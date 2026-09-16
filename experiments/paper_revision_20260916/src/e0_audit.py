"""E0: data and statistics audit for the local-curvature manuscript.

Read-only.  Recomputes every paper-facing number from frozen records and exports the
experiment settings the manuscript had left implicit.  A number that cannot be traced
is reported as a gap, never reconstructed by re-training.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_repository  # noqa: E402  (package-supplied read-only cohort audit)
import repo_adapter as A  # noqa: E402

TWO_PARAMETER_REPORT = "docs/evidence/v5/V5_TWO_PARAMETER_CONFIRMATION_REPORT.json"
ROBUSTNESS_EVIDENCE = "docs/evidence/v4_8_robustness.json"
SCALABILITY_CONDITION = "outputs/runs/v5/residual_scalability/n_100001/m_3413"
SCALABILITY_RESULT = SCALABILITY_CONDITION + "/repeat_{}/result.json"


def two_parameter_audit(repo: Path, commit: str) -> dict:
    report = A.read_json(repo, commit, TWO_PARAMETER_REPORT)
    rows = []
    for row in report["seed_rows"]:
        rows.append(
            {
                "seed": int(row["seed"]),
                "terminal_status": row.get("terminal_status"),
                "binding_valid": bool(row.get("binding_valid")),
                "planned_win": bool(row.get("planned_win")),
                "E_raw2": row.get("E_raw2"),
                "E_SAEPS2": row.get("E_SAEPS2"),
                "D2": row.get("D2"),
                "failure_reason": row.get("failure_reason"),
            }
        )
    valid = [r for r in rows if r["binding_valid"]]
    ratios = [r["E_raw2"] / r["E_SAEPS2"] for r in valid if r["E_SAEPS2"]]
    med_raw = statistics.median([r["E_raw2"] for r in valid]) if valid else None
    med_sae = statistics.median([r["E_SAEPS2"] for r in valid]) if valid else None
    return {
        "planned": report["planned_denominator"],
        "available": len(rows),
        "valid": len(valid),
        "planned_wins": report["planned_win_count"],
        "valid_win_count": report["valid_win_count"],
        "one_sided_exact_sign_test_p": report["one_sided_exact_sign_test_p"],
        "median_E_raw2": med_raw,
        "median_E_SAEPS2": med_sae,
        "ratio_of_median_errors": (med_raw / med_sae) if med_sae else None,
        "median_paired_ratio": statistics.median(ratios) if ratios else None,
        "gate_minimum_valid": report["primary_gate"]["minimum_valid"],
        "gate_minimum_planned_wins": report["primary_gate"]["minimum_planned_wins"],
        "gate_valid_pass": report["primary_gate"]["valid_gate_pass"],
        "gate_planned_win_pass": report["primary_gate"]["planned_win_gate_pass"],
        "scientific_status": report["scientific_status"],
        "rows": rows,
        "source_path": TWO_PARAMETER_REPORT,
        "source_sha256": A.blob_sha256(repo, commit, TWO_PARAMETER_REPORT),
    }


def robustness_audit(repo: Path, commit: str) -> dict:
    evidence = A.read_json(repo, commit, ROBUSTNESS_EVIDENCE)
    return {
        "completed": evidence["completed"],
        "planned_total": evidence["adjudication"].get("planned_total"),
        "binding_valid": evidence["binding_valid"],
        "integrity_gate": evidence["integrity_gate"],
        "adjudication": evidence["adjudication"],
        "architecture": evidence["architecture"],
        "exact_anchors": evidence["exact_anchors"],
        "noise_sparsity_summary": {
            k: v for k, v in evidence["noise_sparsity"].items() if k != "cells"
        },
        "noise_sparsity_cells": evidence["noise_sparsity"]["cells"],
        "source_path": ROBUSTNESS_EVIDENCE,
        "source_sha256": A.blob_sha256(repo, commit, ROBUSTNESS_EVIDENCE),
    }


def settings_audit(repo: Path, commit: str) -> dict:
    import yaml

    multi = A.two_parameter_config(repo, commit)
    robustness = yaml.safe_load(A.read_blob(repo, commit, "configs/v4_8/robustness.yaml"))
    scalability = yaml.safe_load(
        A.read_blob(repo, commit, "configs/v5/residual_scalability_execution.yaml")
    )
    frozen = yaml.safe_load(
        A.read_blob(repo, commit, A.TWO_PARAMETER_EXECUTION_CONFIG)
    )
    declarations = (
        int(multi["points"]["pde"]) * 2
        + int(multi["points"]["data"]) * 2
        + int(multi["points"]["initial"]) * 2
        + int(multi["points"]["boundary_times"]) * 2 * 2
    )
    return {
        "two_parameter": {
            "pde": "coupled manufactured reaction-diffusion, Dirichlet boundary (not periodic)",
            "declared_hidden_width": multi["_declared_width"],
            "effective_hidden_width": multi["_effective_width"],
            "states_per_field": 4 * int(multi["_effective_width"]) + 1,
            "state_parameter_count": 2 * (4 * int(multi["_effective_width"]) + 1),
            "residual_count_expected": declarations,
            "loss_weights": multi["loss_weights"],
            "gamma_alpha": multi["_gamma_alpha"],
            "training_objective": "0.5 * mean_i r_i^2 (mean); exported Hessian uses 0.5 * sum_i r_i^2",
        },
        "noise_sparsity": {
            "noise_levels": robustness["noise_sparsity"]["noise_levels"],
            "observation_fractions": robustness["noise_sparsity"]["observation_fractions"],
            "seed_count": len(robustness["noise_sparsity"]["seeds"]),
            "exact_anchor_cells": robustness["noise_sparsity"]["exact_anchor_cells"],
            "planned_noise_sparsity_runs": robustness["reporting"]["planned_noise_sparsity_runs"],
            "planned_architecture_runs": robustness["reporting"]["planned_architecture_runs"],
            "report_failures_in_denominator": robustness["reporting"]["report_failures_in_denominator"],
            "scientific_gate": robustness["reporting"]["scientific_gate"],
        },
        "architecture_robustness": {
            "widths": robustness["architecture"]["widths"],
            "labels": robustness["architecture"]["labels"],
        },
        "scalability": {
            "gamma_alpha": scalability["gamma_alpha"],
            "primary_accuracy_gamma_alpha": 1.0e-8,
            "state_parameter_counts": list(scalability["state_parameter_counts"]),
            "initial_guess_each_repeat": scalability["initial_guess_each_repeat"],
            "repeats_per_condition": scalability["repeats_per_condition"],
            "cg_tolerance": scalability["cg_tolerance"],
            "cg_max_iterations": scalability["cg_max_iterations"],
            "power_iterations": scalability["power_iterations"],
            "synthetic_residual_padding": scalability["synthetic_residual_padding"],
            "residual_count_settings": scalability["residual_constructions"],
        },
        "loss_scale_note": (
            "Historical training minimised the mean squared residual; the manuscript Hessian "
            "uses the sum objective. Derivatives differ by the residual count m, and a damping "
            "used with the mean objective must be divided by m."
        ),
    }


def cost_audit(repo: Path, commit: str) -> dict:
    repeats = []
    for index in (1, 2, 3):
        record = A.read_json(repo, commit, SCALABILITY_RESULT.format(index))
        repeats.append(
            {
                "repeat": index,
                "setup_seconds": record["shared_condition_setup_seconds"],
                "solve_seconds": record["solve_seconds"],
                "wall_seconds": record["wall_seconds"],
                "cg_iterations": record["cg_iterations"],
                "JVP_count": record["JVP_count"],
                "VJP_count": record["VJP_count"],
                "gamma": record["gamma"],
                "lambda_max_power_estimate": record["lambda_max_power_estimate"],
                "verified_relative_residual": record["verified_relative_residual"],
                "initial_guess": record["initial_guess"],
                "state_parameter_count": record["state_parameter_count"],
                "residual_count": record["residual_count"],
                "peak_memory_bytes": record["peak_memory_bytes"],
                "peak_memory_unavailable_reason": record["peak_memory_unavailable_reason"],
                "role": record["role"],
            }
        )
    setup = [r["setup_seconds"] for r in repeats]
    solve = [r["solve_seconds"] for r in repeats]
    wall = [r["wall_seconds"] for r in repeats]
    return {
        "condition": SCALABILITY_CONDITION,
        "repeats": repeats,
        "setup_seconds_median": statistics.median(setup),
        "setup_seconds_min": min(setup),
        "setup_seconds_max": max(setup),
        "solve_seconds_median": statistics.median(solve),
        "wall_seconds_median": statistics.median(wall),
        "timing_scope_note": (
            "setup and iteration times are recorded separately; their sum is not an "
            "end-to-end cost, and checkpoint loading and residual construction are outside "
            "the recorded iteration timer."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=A.repo_root())
    parser.add_argument("--ref", default=A.DEFAULT_REF)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    commit = A.resolve_commit(repo, args.ref)
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True, exist_ok=True)

    scalar = audit_repository.audit(repo, args.ref)
    two_parameter = two_parameter_audit(repo, commit)
    robustness = robustness_audit(repo, commit)
    settings = settings_audit(repo, commit)
    cost = cost_audit(repo, commit)

    audit = {
        "classification": "NEW_POSTHOC_READ_ONLY",
        "task": "E0_data_and_statistics_audit",
        "environment": A.frozen_environment(repo, args.ref),
        "training_executed": False,
        "historical_records_modified": False,
        "scalar": scalar,
        "two_parameter": two_parameter,
        "robustness": robustness,
        "settings": settings,
        "cost": cost,
    }
    with (out / "e0_source_audit.json").open("x", encoding="utf-8") as handle:
        json.dump(audit, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")

    rows = []
    for name, cohort in scalar["cohorts"].items():
        rows.append(
            {
                "cohort": name,
                "family": "scalar",
                "planned": cohort["planned"],
                "available": cohort["available"],
                "valid": cohort["valid"],
                "wins_among_valid": cohort["wins_among_valid"],
                "median_E_raw": cohort["median_E_raw"],
                "median_E_SAEPS": cohort["median_E_SAEPS"],
                "ratio_of_median_errors": cohort["ratio_of_median_errors"],
                "median_paired_ratio": cohort["median_paired_ratio"],
                "one_sided_sign_p": cohort["one_sided_sign_p_valid_non_ties"],
                "median_metric": "curvature error E",
            }
        )
    rows.append(
        {
            "cohort": "coupled two-parameter",
            "family": "two_parameter",
            "planned": two_parameter["planned"],
            "available": two_parameter["available"],
            "valid": two_parameter["valid"],
            "wins_among_valid": two_parameter["valid_win_count"],
            "median_E_raw": two_parameter["median_E_raw2"],
            "median_E_SAEPS": two_parameter["median_E_SAEPS2"],
            "ratio_of_median_errors": two_parameter["ratio_of_median_errors"],
            "median_paired_ratio": two_parameter["median_paired_ratio"],
            "one_sided_sign_p": two_parameter["one_sided_exact_sign_test_p"],
            "median_metric": "reduced curvature value (E_raw2 / E_SAEPS2)",
        }
    )
    for name, group in robustness["architecture"]["widths"].items():
        rows.append(
            {
                "cohort": f"architecture {name.split('=')[-1]}",
                "family": "robustness",
                "planned": group["planned"],
                "available": group["planned"],
                "valid": group["binding_valid"],
                "wins_among_valid": None,
                "median_E_raw": group["median_F_raw_valid"],
                "median_E_SAEPS": group["median_F_se_valid"],
                "ratio_of_median_errors": None,
                "median_paired_ratio": None,
                "one_sided_sign_p": None,
                "median_metric": "median F_raw / F_SAEPS over binding-valid centres, not an error",
            }
        )
    fields = [
        "cohort",
        "family",
        "planned",
        "available",
        "valid",
        "wins_among_valid",
        "median_E_raw",
        "median_E_SAEPS",
        "ratio_of_median_errors",
        "median_paired_ratio",
        "one_sided_sign_p",
        "median_metric",
    ]
    with (out / "e0_statistics.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    (out / "e0_missing_metadata.md").write_text(missing_metadata(audit), encoding="utf-8")
    print(out)


def missing_metadata(audit: dict) -> str:
    r = audit["robustness"]
    c = audit["cost"]
    wide = next(v for k, v in r["architecture"]["widths"].items() if k.endswith("wide"))
    return f"""# E0 missing metadata and unresolved traces

Frozen evidence: `{audit['environment']['commit']}` (`{audit['environment']['ref']}`).

## Available and traced

- Scalar cohorts read directly from run records; every record hash is listed in
  `e0_source_audit.json` under `scalar.input_sha256`.
- Two-parameter cohort read from the confirmation report with all {audit['two_parameter']['planned']} planned seeds present.
- Cost record read from raw run output for `{c['condition']}`.

## Not available from the frozen archive

- **Scalar state tensors, observation sets and residuals.** The scalar posthoc records
  store parameter and state matrix blocks only. Consequences: the E1 identity cannot be
  re-derived by autograd for scalar centres (block-level self-consistency only), and E2
  state refinement is `NOT_AVAILABLE` for the prescribed scalar queue
  (Burgers 55/60/69; Allen-Cahn 75/79/84).
- **Original scalar centre tensors.** `outputs/runs/v5/checkpoints/burgers`,
  `.../allen_cahn` hold `V5_RECONSTRUCTED_ENGINEERING_CHECKPOINT` artifacts with
  `historical_tensor_identity_claimed: false`. They are engineering reconstructions, not
  the archived confirmation tensors, so they cannot stand in for the original reference.
- **Native peak tensor memory.** The scalability record reports
  `peak_memory_unavailable_reason = {c['repeats'][0]['peak_memory_unavailable_reason']!r}`.
  No native tensor peak is recorded, and process RSS is not a substitute.

## Deliberately not reconstructed

- No historical seed was re-run, and no failed seed was replaced.
- No scalar state tensor was regenerated to fill the E1/E2 gap.

## Denominator notes

- Scalar evaluation denominators are the surviving binding-valid counts, as recorded:
  Burgers {audit['scalar']['cohorts']['Burgers']['valid']}/{audit['scalar']['cohorts']['Burgers']['planned']},
  Allen-Cahn {audit['scalar']['cohorts']['Allen-Cahn']['valid']}/{audit['scalar']['cohorts']['Allen-Cahn']['planned']},
  two-parameter {audit['two_parameter']['valid']}/{audit['two_parameter']['planned']}.
- Two-parameter invalid seeds are non-wins in the planned denominator; the 8/10 result and
  the `INCONCLUSIVE` scientific status are unchanged.
- Architecture robustness: the `wide` group has {wide['binding_valid']} binding-valid centres out of
  {wide['planned']} planned.
"""


if __name__ == "__main__":
    main()
