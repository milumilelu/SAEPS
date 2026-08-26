#!/usr/bin/env python3
"""Corrected one-shot v3 exact fixed-state decomposition runner.

V3 captures the immutable base numeric function before runtime dispatch,
preventing the recursive wrapper failure that aborted v2.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import posthoc_exact_fixed_state_v1 as v1  # noqa: E402


CONFIG_PATH = ROOT / "configs/posthoc_exact_fixed_state_v3.yaml"
RUNNER_PATH = Path(__file__).resolve()
TEST_PATH = ROOT / "tests/test_posthoc_exact_fixed_state_v3.py"
OUTPUT_ROOT = ROOT / "outputs/posthoc/exact_fixed_state_v3"
PREFLIGHT_PATH = OUTPUT_ROOT / "preflight.json"
CLAIM_PATH = OUTPUT_ROOT / "execution_claim.json"
ABORT_V2_PATH = ROOT / "outputs/posthoc/exact_fixed_state_v2/ABORTED.json"
CLASSIFICATION = "POSTHOC_NONBINDING_MECHANISM_ANALYSIS"
BASE_NUMERIC_ANALYSIS = v1._numeric_analysis


def corrected_numeric_analysis(
    blocks: dict[str, Any],
    gamma: float,
    original: dict[str, Any],
    selected_fse: float,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Use explicit Schur values for identities; retain LSQR only for reproduction."""
    result = BASE_NUMERIC_ANALYSIS(blocks, gamma, original, selected_fse, config)
    explicit = float(result["rerun"]["F_SAEPS_explicit"])
    hred = float(result["rerun"]["H_red_exact"])
    fraw = float(result["rerun"]["F_raw"])
    delta_gn_fix = float(result["decomposition"]["Delta_GN_fix"])
    delta_relax = float(result["decomposition"]["Delta_relax"])
    floor = float(config["tolerances"]["algebraic_absolute_floor"])
    rtol = float(config["tolerances"]["algebraic_relative"])
    eps = float(config["tolerances"]["denominator_floor"])
    identity_left = explicit - hred
    identity_right = delta_gn_fix - delta_relax
    identity_pass = v1._close(identity_left, identity_right, rtol, floor)
    result["rerun"]["F_SAEPS"] = selected_fse
    result["rerun"]["F_SAEPS_reproduction_LSQR"] = selected_fse
    result["rerun"]["F_SAEPS_mechanistic_explicit"] = explicit
    result["decomposition"]["exact_error_identity_left"] = identity_left
    result["decomposition"]["exact_error_identity_right"] = identity_right
    result["decomposition"]["identity_relative_residual"] = v1._relerr(
        identity_left, identity_right, floor
    )
    result["numerical_checks"]["exact_error_identity"] = identity_pass
    result["metrics"]["E_SAEPS"] = abs(explicit - hred) / (abs(hred) + eps)
    result["metrics"]["R_total_improvement"] = abs(fraw - hred) / (
        abs(explicit - hred) + eps
    )
    bound_check = result["GN_remainder_diagnostics"]["bound_check"]
    result["numerical_status"] = (
        "PASS"
        if all(value is True for value in result["numerical_checks"].values())
        and bound_check is not False
        else "NUMERICAL_FAILURE"
    )
    result["value_roles"] = {
        "mechanistic_identities_and_metrics": "explicit_GN_Schur_solve",
        "historical_reproduction_check": "selected_scaled_LSQR_iterative_refinement",
    }
    return result


def preflight_payload() -> dict[str, Any]:
    base = v1.preflight_payload()
    torch.set_default_dtype(torch.float64)
    theta = torch.tensor([0.25, -0.35], dtype=torch.float64)
    parameter = torch.tensor([math.log(1.1)], dtype=torch.float64)

    def residual(t: torch.Tensor, p: torch.Tensor) -> torch.Tensor:
        physical = torch.exp(p[0])
        return torch.stack(
            [t[0] * physical + t[1] ** 2 - 0.2, torch.sin(t[0]) + physical * t[1]]
        )

    blocks = v1.curvature_blocks(residual, theta, parameter, 0.05)
    explicit = v1._scalar(blocks["F_SAEPS_tensor"])
    simulated_historical_lsqr = explicit * (1.0 + 5.0e-11)
    config = v1.load_config(CONFIG_PATH)
    analysis = corrected_numeric_analysis(
        blocks, 0.05, {}, simulated_historical_lsqr, config
    )
    regression_checks = {
        "study_seeds_used": [],
        "distinct_LSQR_value_retained_for_reproduction": analysis["rerun"]["F_SAEPS"]
        != analysis["rerun"]["F_SAEPS_mechanistic_explicit"],
        "identity_uses_explicit_Schur_value": analysis["numerical_checks"][
            "exact_error_identity"
        ],
        "corrected_numerical_status": analysis["numerical_status"] == "PASS",
    }
    base.update(
        schema_version=3,
        v2_abort_sha256=v1.sha256(ABORT_V2_PATH),
        v3_regression_checks=regression_checks,
        status="PASSED"
        if base["status"] == "PASSED"
        and all(
            regression_checks[key]
            for key in (
                "distinct_LSQR_value_retained_for_reproduction",
                "identity_uses_explicit_Schur_value",
                "corrected_numerical_status",
            )
        )
        else "FAILED",
    )
    return base


def nonstudy_end_to_end_preflight(config: dict[str, Any]) -> dict[str, Any]:
    """Run the real frozen Burgers path on one non-study seed before claiming."""
    seed = int(config["nonstudy_end_to_end_preflight_seed"])
    study_seeds = {
        int(value)
        for cohort in config["cohorts"].values()
        for value in cohort["planned_seeds"]
    }
    if seed in study_seeds:
        raise RuntimeError("end-to-end preflight seed overlaps a study cohort")
    started = datetime.now(UTC)
    theta, parameter, residual_function, center, curvature = v1._center_burgers(seed)
    if theta is None or parameter is None or residual_function is None:
        raise RuntimeError("non-study end-to-end preflight did not reconstruct a center")
    center_pass, stationarity = v1._center_valid(
        "burgers", theta, parameter, residual_function, center, curvature
    )
    if not center_pass:
        raise RuntimeError("non-study end-to-end preflight center gate failed")
    linearization = v1.ResidualLinearization(residual_function, theta, parameter)
    jt, jl = linearization.explicit_jacobians()
    lambda_max = float(torch.linalg.eigvalsh(jt.T @ jt).max().item())
    alpha = float(curvature["gamma"]["alpha"])
    gamma = alpha * lambda_max
    solver_spec = curvature["curvature_solver"]
    candidates = v1.scaled_augmented_lsqr_candidates(
        linearization,
        jl[:, 0],
        gamma,
        float(solver_spec["tolerance"]),
        int(solver_spec["max_iterations_per_pass"]),
        int(solver_spec["refinement_passes"]),
    )
    selected_fse = float(candidates["scaled_LSQR_iterative_refinement"]["Fse"])
    blocks = v1.curvature_blocks(residual_function, theta, parameter, gamma)
    previous = v1._numeric_analysis
    v1._numeric_analysis = corrected_numeric_analysis
    try:
        # Dispatch through the exact symbol used by formal run_sequence. This
        # would recurse under the v2 implementation.
        analysis = v1._numeric_analysis(blocks, gamma, {}, selected_fse, config)
    finally:
        v1._numeric_analysis = previous
    crosscheck = v1._relerr(
        selected_fse,
        float(analysis["rerun"]["F_SAEPS_mechanistic_explicit"]),
        float(config["tolerances"]["algebraic_absolute_floor"]),
    )
    checks = {
        "seed_is_nonstudy": seed not in study_seeds,
        "real_center_gate": center_pass,
        "runtime_dispatch_no_recursion": analysis["numerical_status"] == "PASS",
        "exact_identity": analysis["numerical_checks"]["exact_error_identity"],
        "LSQR_explicit_consistency": crosscheck
        <= float(config["tolerances"]["algebraic_relative"]),
        "full_exact_blocks_finite": all(
            torch.all(torch.isfinite(blocks[key])).item()
            for key in (
                "H_tt_tensor",
                "H_tl_tensor",
                "H_lt_tensor",
                "H_ll_tensor",
            )
        ),
    }
    return {
        "seed": seed,
        "benchmark": "Burgers",
        "role": "NONSTUDY_END_TO_END_PREFLIGHT",
        "study_seed": False,
        "stationarity": stationarity,
        "alpha": alpha,
        "gamma": gamma,
        "lambda_max_G_tt": lambda_max,
        "LSQR_vs_explicit_relative_error": crosscheck,
        "checks": checks,
        "status": "PASSED" if all(checks.values()) else "FAILED",
        "runtime_seconds": (datetime.now(UTC) - started).total_seconds(),
    }


def run_preflight() -> None:
    config = v1.load_config(CONFIG_PATH)
    torch.set_default_dtype(torch.float64)
    env = v1._expected_environment(config)
    manifests = v1._manifest_state(config)
    sources = v1._historical_source_state(config)
    payload = preflight_payload()
    end_to_end = nonstudy_end_to_end_preflight(config)
    validator = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_repository.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        validator_payload = json.loads(validator.stdout)
    except json.JSONDecodeError:
        validator_payload = {
            "status": "FAILED",
            "stdout": validator.stdout,
            "stderr": validator.stderr,
            "returncode": validator.returncode,
        }
    payload.update(
        environment=env,
        frozen_manifests=manifests,
        historical_sources=sources,
        nonstudy_end_to_end=end_to_end,
        pre_run_repository_validator=validator_payload,
    )
    if (
        validator.returncode != 0
        or validator_payload.get("status") != "PASSED"
        or end_to_end["status"] != "PASSED"
    ):
        payload["status"] = "FAILED"
    v1.write_json(PREFLIGHT_PATH, payload)
    if payload["status"] != "PASSED":
        raise RuntimeError("v3 preflight failed")
    print(json.dumps({"status": "PASSED", "path": str(PREFLIGHT_PATH)}, indent=2))


def initialize_claim() -> None:
    config = v1.load_config(CONFIG_PATH)
    if CLAIM_PATH.exists():
        raise RuntimeError("v3 execution claim already exists")
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if preflight["status"] != "PASSED":
        raise RuntimeError("v3 preflight is not PASSED")
    env = v1.environment()
    if env["git_status_porcelain"]:
        raise RuntimeError(f"claim requires clean git status: {env['git_status_porcelain']}")
    manifests = v1._manifest_state(config)
    claim = {
        "schema_version": 3,
        "analysis_name": config["analysis_name"],
        "analysis_classification": CLASSIFICATION,
        "baseline_repo_commit": config["baseline_repo_commit"],
        "current_execution_commit": env["git_commit"],
        "git_status": env["git_status_porcelain"],
        "environment": env,
        "protocol_sha256": v1.sha256(CONFIG_PATH),
        "runner_sha256": v1.sha256(RUNNER_PATH),
        "test_sha256": v1.sha256(TEST_PATH),
        "preflight_sha256": v1.sha256(PREFLIGHT_PATH),
        "v1_runner_dependency_sha256": v1.sha256(v1.RUNNER_PATH),
        "v2_abort_sha256": v1.sha256(ABORT_V2_PATH),
        "source_frozen_evidence": manifests,
        "original_valid_seed_sets": {name: state["valid"] for name, state in manifests.items()},
        "original_invalid_seed_sets": {name: state["invalid"] for name, state in manifests.items()},
        "canary_sequence": config["canary_sequence"],
        "replacement_forbidden": True,
        "rerun_after_scientific_result_forbidden": True,
        "primary_confirmation_claims_changed": False,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    v1.write_json(CLAIM_PATH, claim)
    print(json.dumps({"status": "CLAIMED", "path": str(CLAIM_PATH)}, indent=2))


def _load_and_verify() -> tuple[dict[str, Any], dict[str, Any]]:
    config = v1.load_config(CONFIG_PATH)
    claim = json.loads(CLAIM_PATH.read_text(encoding="utf-8"))
    for path, expected in (
        (CONFIG_PATH, claim["protocol_sha256"]),
        (RUNNER_PATH, claim["runner_sha256"]),
        (TEST_PATH, claim["test_sha256"]),
        (PREFLIGHT_PATH, claim["preflight_sha256"]),
        (v1.RUNNER_PATH, claim["v1_runner_dependency_sha256"]),
        (ABORT_V2_PATH, claim["v2_abort_sha256"]),
    ):
        if v1.sha256(path) != expected:
            raise RuntimeError(f"frozen v3 file changed: {path}")
    v1._manifest_state(config)
    v1._historical_source_state(config)
    return config, claim


def run_sequence(sequence: list[tuple[str, int]]) -> None:
    config, claim = _load_and_verify()
    torch.set_default_dtype(torch.float64)
    v1._numeric_analysis = corrected_numeric_analysis
    for name, seed in sequence:
        path = OUTPUT_ROOT / name / f"seed_{seed}.json"
        if path.exists():
            raise RuntimeError(f"formal v3 seed output already exists; rerun forbidden: {path}")
        record = v1.run_seed(name, seed, config, claim)
        record["schema_version"] = 3
        record["protocol_version"] = "v3"
        v1.write_json(path, record)
        print(
            json.dumps(
                {
                    "cohort": name,
                    "seed": seed,
                    "original_status": record["original_status"],
                    "rerun_center_status": record["rerun_center_status"],
                    "reproduction_status": record["reproduction_status"],
                    "numerical_status": record.get("numerical_status"),
                    "analysis_valid": record["analysis_valid"],
                    "runtime_seconds": record["runtime_seconds"],
                }
            ),
            flush=True,
        )


def canary_sequence() -> list[tuple[str, int]]:
    config = v1.load_config(CONFIG_PATH)
    return [(str(config["canary_sequence"]["cohort"]), int(seed)) for seed in config["canary_sequence"]["seeds"]]


def remaining_sequence() -> list[tuple[str, int]]:
    config = v1.load_config(CONFIG_PATH)
    canary = set(canary_sequence())
    return [
        (name, int(seed))
        for name, cohort in config["cohorts"].items()
        for seed in cohort["planned_seeds"]
        if (name, int(seed)) not in canary
    ]


def verify_canary() -> None:
    failures = []
    rows = []
    for name, seed in canary_sequence():
        path = OUTPUT_ROOT / name / f"seed_{seed}.json"
        if not path.exists():
            failures.append(f"missing {name}/{seed}")
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "seed": seed,
                "original_binding_valid": record["original_binding_valid"],
                "rerun_center_status": record["rerun_center_status"],
                "reproduction_status": record["reproduction_status"],
                "numerical_status": record.get("numerical_status"),
                "analysis_valid": record["analysis_valid"],
                "failure_reason": record["failure_reason"],
            }
        )
        if record["original_binding_valid"]:
            if record["reproduction_status"] != "REPRODUCTION_PASS":
                failures.append(f"seed {seed} reproduction mismatch")
            if record.get("numerical_status") != "PASS":
                failures.append(f"seed {seed} numerical failure")
            if not record["analysis_valid"]:
                failures.append(f"seed {seed} unexpectedly analysis-invalid")
        elif record["analysis_valid"]:
            failures.append(f"original-invalid seed {seed} entered analysis")
    audit = {
        "schema_version": 3,
        "status": "PASSED" if not failures else "FAILED",
        "rows": rows,
        "failures": failures,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    v1.write_json(OUTPUT_ROOT / "canary_audit.json", audit)
    print(json.dumps(audit, indent=2))
    if failures:
        raise RuntimeError("v3 canary failed; remaining seeds must not start")


def aggregate() -> None:
    config, _ = _load_and_verify()
    output: dict[str, Any] = {
        "schema_version": 3,
        "analysis_classification": CLASSIFICATION,
        "baseline_repo_commit": config["baseline_repo_commit"],
        "primary_confirmation_claims_changed": False,
        "cohorts": {},
    }
    csv_rows: list[dict[str, Any]] = []
    metric_names = [
        "E_raw",
        "E_SAEPS",
        "E_fix_exact_to_reduced",
        "E_GN_fix_native",
        "E_GN_fix_reduced_scale",
        "E_relax",
        "rho_relax",
        "R_freezing_to_GN",
        "delta",
    ]
    for name, cohort in config["cohorts"].items():
        records = [
            json.loads((OUTPUT_ROOT / name / f"seed_{int(seed)}.json").read_text(encoding="utf-8"))
            for seed in cohort["planned_seeds"]
        ]
        valid = [record for record in records if record["analysis_valid"]]
        summaries: dict[str, Any] = {}
        for metric in metric_names:
            values = []
            for record in valid:
                value = (
                    record["GN_remainder_diagnostics"]["delta"]
                    if metric == "delta"
                    else record["metrics"][metric]
                )
                if value is not None:
                    values.append(float(value))
            summaries[metric] = (
                {"n": 0}
                if not values
                else {
                    "n": len(values),
                    "median": statistics.median(values),
                    "Q25": float(np.quantile(values, 0.25, method="linear")),
                    "Q75": float(np.quantile(values, 0.75, method="linear")),
                    "min": min(values),
                    "max": max(values),
                }
            )
        output["cohorts"][name] = {
            "planned": len(records),
            "original_binding_valid": sum(record["original_binding_valid"] for record in records),
            "rerun_center_valid_among_original_valid": sum(record["original_binding_valid"] and record["rerun_center_status"] == "PASS" for record in records),
            "reproduction_pass": sum(record["reproduction_status"] == "REPRODUCTION_PASS" for record in records),
            "analysis_valid": len(valid),
            "reproduction_mismatch_seeds": [record["seed"] for record in records if record["reproduction_status"] == "REPRODUCTION_MISMATCH"],
            "algebraic_or_numerical_failure_seeds": [record["seed"] for record in records if record.get("numerical_status") == "NUMERICAL_FAILURE"],
            "metrics": summaries,
            "descriptive_counts": {
                "E_fix_gt_E_GN_fix_reduced_scale": sum(record["metrics"]["E_fix_exact_to_reduced"] > record["metrics"]["E_GN_fix_reduced_scale"] for record in valid),
                "E_relax_lt_0_1": sum(record["metrics"]["E_relax"] is not None and record["metrics"]["E_relax"] < 0.1 for record in valid),
                "E_relax_lt_0_25": sum(record["metrics"]["E_relax"] is not None and record["metrics"]["E_relax"] < 0.25 for record in valid),
                "rho_relax_0_75_to_1_25": sum(record["metrics"]["rho_relax"] is not None and 0.75 <= record["metrics"]["rho_relax"] <= 1.25 for record in valid),
                "GN_bound_applicable": sum(record["GN_remainder_diagnostics"]["bound_applicable"] for record in valid),
            },
        }
        for record in records:
            row = {
                "cohort": name,
                "seed": record["seed"],
                "original_status": record["original_status"],
                "original_binding_valid": record["original_binding_valid"],
                "rerun_center_status": record["rerun_center_status"],
                "reproduction_status": record["reproduction_status"],
                "analysis_valid": record["analysis_valid"],
                "failure_reason": record["failure_reason"],
            }
            for metric in metric_names:
                row[metric] = (
                    (record.get("GN_remainder_diagnostics") or {}).get("delta")
                    if metric == "delta"
                    else (record.get("metrics") or {}).get(metric)
                )
            csv_rows.append(row)
    json_path = ROOT / "docs/evidence/posthoc_exact_fixed_state_v3.json"
    csv_path = ROOT / "docs/evidence/posthoc_exact_fixed_state_v3.csv"
    v1.write_json(json_path, output)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(json.dumps({"json": str(json_path), "csv": str(csv_path)}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("preflight", "initialize-claim", "run-canary", "verify-canary", "run-remaining", "aggregate"),
    )
    args = parser.parse_args()
    if args.command == "preflight":
        run_preflight()
    elif args.command == "initialize-claim":
        initialize_claim()
    elif args.command == "run-canary":
        run_sequence(canary_sequence())
    elif args.command == "verify-canary":
        verify_canary()
    elif args.command == "run-remaining":
        run_sequence(remaining_sequence())
    else:
        aggregate()


if __name__ == "__main__":
    main()
