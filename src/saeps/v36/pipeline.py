"""Immutable one-shot v3.6 scalar-curvature confirmation pipeline."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import load_config
from saeps.p4_screening import _stationarity
from saeps.p5_confirmation import _runtime_config
from saeps.provenance import environment_provenance
from saeps.scalar import scalar_residual, solve_truth, train_scalar_checkpoint
from saeps.v3.foundation import full_hessian_references
from saeps.v31.pipeline import _mean_residual_objective
from saeps.v33.pipeline import _direct_augmented_reference
from saeps.v35.engineering import center_with_registered_rescue, scaled_augmented_lsqr_candidates
from saeps.v35.pipeline import _spearman
from saeps.v35.second_order import second_order_reduced_decomposition


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _relative(left: float, right: float, floor: float = 1.0e-30) -> float:
    return abs(left - right) / max(abs(right), floor)


def _center_specs(specification: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    local = dict(specification["center"]["local_minimum"])
    baseline = {
        key: local[key]
        for key in [
            "normalized_gradient_tolerance",
            "hessian_absolute_tolerance",
            "hessian_relative_tolerance",
            "maximum_escape_cycles",
            "negative_probe_relative_radii",
            "trust_initial_relative_radius",
            "trust_minimum_relative_radius",
            "trust_maximum_relative_radius",
            "trust_backtracking_factors",
            "minimum_actual_decrease",
            "optimizer",
            "polish_optimizer",
            "stopping",
        ]
    }
    enhanced = {
        "maximum_rescue_steps": local["maximum_rescue_steps"],
        "initial_relative_radius": local["rescue_initial_relative_radius"],
        "minimum_relative_radius": local["rescue_minimum_relative_radius"],
        "maximum_relative_radius": local["rescue_maximum_relative_radius"],
        "eigenvalue_clip_relative": local["rescue_eigenvalue_clip_relative"],
        "armijo_constant": local["rescue_armijo_constant"],
        "backtracking_factors": local["rescue_backtracking_factors"],
    }
    return baseline, enhanced


def _exact_sign_tail(wins: int, non_tied: int) -> float | None:
    if non_tied == 0:
        return None
    return sum(math.comb(non_tied, value) for value in range(wins, non_tied + 1)) / 2**non_tied


def _base_record(seed: int, specification: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "phase": "V3_6_SCALAR_CONFIRMATION",
        "seed": seed,
        "split": "untouched_confirmation",
        "config_path": "configs/v3_6/locked_scalar_confirmation.yaml",
        "config_sha256": _sha256(Path(provenance["repo_root"]) / "configs/v3_6/locked_scalar_confirmation.yaml"),
        "git_commit": provenance["git_commit"],
        "benchmark": specification["benchmark"],
        "status": "NUMERICAL_FAILURE",
        "failure_reason": None,
        "failure_stage": None,
        "center": None,
        "center_stationarity": None,
        "gamma": None,
        "solver": None,
        "exact_hessian": None,
        "F_raw": None,
        "F_se_GN": None,
        "H_red_exact_gamma": None,
        "E_raw": None,
        "E_SAEPS": None,
        "D": None,
        "I_GN": None,
        "elapsed_seconds": None,
    }


def _run_seed(
    seed: int,
    specification: dict[str, Any],
    scalar_locked: dict[str, Any],
    runtime: dict[str, Any],
    truth: Any,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    record = _base_record(seed, specification, provenance)
    stage = "center"
    try:
        checkpoint, points = train_scalar_checkpoint(runtime, "Burgers", seed, truth)
        residual_function: ResidualFunction = lambda theta, parameter: scalar_residual(
            theta, parameter, "Burgers", points, truth, runtime
        )
        parameter = checkpoint.log_parameter.detach().clone()
        objective = _mean_residual_objective(
            residual_function, parameter, checkpoint.theta, 0.0, False
        )
        local, enhanced = _center_specs(specification)
        theta, center = center_with_registered_rescue(
            objective, checkpoint.theta, local, enhanced
        )
        record["training"] = {
            "seconds": checkpoint.elapsed_seconds,
            "stop_reason": checkpoint.stop_reason,
            "adam_epochs": checkpoint.adam_epochs,
            "state_rmse_validation_only": checkpoint.state_rmse,
            "learned_parameter_validation_only": float(torch.exp(parameter)[0].item()),
        }
        record["center"] = center
        if theta is None:
            record.update(
                status="CHECKPOINT_INVALID",
                failure_reason="frozen baseline and enhanced-rescue center failed",
                failure_stage="center",
            )
            return record

        linearization = ResidualLinearization(residual_function, theta, parameter)
        residual = linearization.residual()
        jt, jl = linearization.explicit_jacobians()
        selected = center["baseline"] if center["selected_method"] == "baseline_v3_4_exact_trust" else center["enhanced"]
        g_theta = float(selected["final"]["normalized_objective_gradient"])
        s_theta = _stationarity(jt, residual)
        s_lambda = _stationarity(jl, residual)
        center_pass = (
            g_theta < float(specification["center"]["required_objective_gradient_tolerance"])
            and s_theta < float(specification["center"]["residual_stationarity_tolerance"])
        )
        record["center_stationarity"] = {
            "G_theta": g_theta,
            "S_theta": s_theta,
            "S_lambda": s_lambda,
            "status": "PASS" if center_pass else "CHECKPOINT_INVALID",
        }
        if not center_pass:
            record.update(
                status="CHECKPOINT_INVALID",
                failure_reason="frozen common-center first-order gate failed",
                failure_stage="center",
            )
            return record

        gamma = float(specification["gamma"]["alpha"]) * float(
            torch.linalg.eigvalsh(jt.T @ jt).max().item()
        )
        record["gamma"] = gamma

        stage = "exact_reference"
        full = full_hessian_references(
            residual_function,
            theta,
            parameter,
            gamma,
            specification["gold_standard"],
        )
        decomposition = second_order_reduced_decomposition(
            residual_function,
            theta,
            parameter,
            gamma,
            float(specification["errors"]["denominator_floor"]),
        )
        gamma_gold = full["gamma_matched"]
        h_exact = (
            float(gamma_gold["reduced_hessian"][0][0])
            if gamma_gold["reduced_hessian"] is not None
            else None
        )
        decomposition_exact = float(decomposition["Hred_exact_gamma"])
        exact_cross_error = (
            _relative(decomposition_exact, h_exact)
            if h_exact is not None
            else None
        )
        exact_pass = (
            full["symmetry_relative_error"]
            <= float(specification["gold_standard"]["symmetry_relative_tolerance"])
            and gamma_gold["status"] == "PASS"
            and exact_cross_error is not None
            and exact_cross_error <= float(specification["gold_standard"]["solve_relative_tolerance"])
        )
        record["exact_hessian"] = {
            "status": "PASS" if exact_pass else "NUMERICAL_FAILURE",
            "symmetry_relative_error": full["symmetry_relative_error"],
            "gamma_matched": gamma_gold,
            "decomposition_crosscheck_relative_error": exact_cross_error,
            "first_order_reduced_correction": decomposition["first_order_reduced_correction"],
        }
        if not exact_pass:
            record.update(
                status="NUMERICAL_FAILURE",
                failure_reason="exact finite-gamma reduced-Hessian gate failed",
                failure_stage="exact_reference",
            )
            return record

        stage = "solver"
        explicit = _direct_augmented_reference(
            jt,
            jl,
            residual,
            gamma,
            {
                "explicit_relative_normal_residual": 1.0e-10,
                "explicit_objective_identity_tolerance": 1.0e-10,
            },
        )
        solver_spec = specification["curvature_solver"]
        scaled = scaled_augmented_lsqr_candidates(
            linearization,
            jl[:, 0],
            gamma,
            float(solver_spec["tolerance"]),
            int(solver_spec["max_iterations_per_pass"]),
            int(solver_spec["refinement_passes"]),
        )
        selected_solver = scaled["scaled_LSQR_iterative_refinement"]
        fse = float(selected_solver["Fse"])
        explicit_fse = float(explicit["Fse"][0][0])
        solver_error = _relative(fse, explicit_fse)
        solver_pass = (
            explicit["status"] == "PASS"
            and float(selected_solver["verified_original_relative_normal_residual"])
            <= float(solver_spec["verified_normal_residual_acceptance"])
            and solver_error <= float(solver_spec["explicit_reference_relative_acceptance"])
            and int(selected_solver["total_iterations"]) <= int(solver_spec["maximum_total_iterations"])
        )
        record["solver"] = {
            "status": "PASS" if solver_pass else "SOLVER_FAILURE",
            "method": solver_spec["selected"],
            "Fse_explicit": explicit_fse,
            "Fse_selected": fse,
            "selected_vs_explicit_relative_error": solver_error,
            "verified_original_relative_normal_residual": selected_solver[
                "verified_original_relative_normal_residual"
            ],
            "iterations": selected_solver["total_iterations"],
            "refinement_passes": selected_solver["passes"],
            "setup": scaled["scaling"],
            "setup_jvp_count": scaled["setup_jvp_count"],
            "explicit_reference": explicit,
        }
        if not solver_pass:
            record.update(
                status="SOLVER_FAILURE",
                failure_reason="frozen two-pass scaled-LSQR gate failed",
                failure_stage="solver",
            )
            return record

        stage = "comparative"
        fraw = float(decomposition["Fraw"])
        floor = float(specification["errors"]["denominator_floor"])
        denominator = abs(h_exact) + floor
        e_raw = abs(fraw - h_exact) / denominator
        e_saeps = abs(fse - h_exact) / denominator
        d_value = e_raw - e_saeps
        indicator = float(
            decomposition["block_ratios_and_indicators"][
                "first_order_correction_relative_to_GN"
            ]
        )
        primary = [fraw, fse, h_exact, e_raw, e_saeps, d_value, indicator, gamma]
        if not all(math.isfinite(value) for value in primary):
            raise FloatingPointError("one or more primary quantities are non-finite")
        record.update(
            status="PASS",
            failure_reason=None,
            failure_stage=None,
            F_raw=fraw,
            F_se_GN=fse,
            H_red_exact_gamma=h_exact,
            E_raw=e_raw,
            E_SAEPS=e_saeps,
            D=d_value,
            I_GN=indicator,
        )
        return record
    except Exception as error:
        terminal = "SOLVER_FAILURE" if stage == "solver" else "NUMERICAL_FAILURE"
        record.update(
            status=terminal,
            failure_reason=f"{type(error).__name__}: {error}",
            failure_stage=stage,
        )
        return record
    finally:
        record["elapsed_seconds"] = time.perf_counter() - started


def _aggregate(records: list[dict[str, Any]], specification: dict[str, Any]) -> dict[str, Any]:
    valid = [record for record in records if record["status"] == "PASS"]
    tie_tolerance = float(specification["primary"]["tie_tolerance"])
    strict_wins = sum(float(record["D"]) > tie_tolerance for record in valid)
    strict_losses = sum(float(record["D"]) < -tie_tolerance for record in valid)
    ties = len(valid) - strict_wins - strict_losses
    non_tied = strict_wins + strict_losses
    sign_p = _exact_sign_tail(strict_wins, non_tied)
    differences = [float(record["D"]) for record in valid]
    median_d = statistics.median(differences) if differences else None
    conditions = {
        "minimum_valid_pairs": len(valid) >= int(specification["primary"]["minimum_valid_pairs"]),
        "planned_seed_wins": strict_wins >= int(specification["primary"]["planned_seed_wins_required"]),
        "positive_median_D": median_d is not None and median_d > 0.0,
        "exact_sign_test": sign_p is not None and sign_p <= float(specification["primary"]["alpha"]),
    }
    scientific = "SUPPORTED" if all(conditions.values()) else "NOT_SUPPORTED"
    e_saeps = [float(record["E_SAEPS"]) for record in valid]
    e_raw = [float(record["E_raw"]) for record in valid]
    indicators = [float(record["I_GN"]) for record in valid]
    threshold = float(specification["gn_indicator"]["threshold"])
    predicted = [value <= threshold for value in indicators]
    observed = [value <= threshold for value in e_saeps]
    confusion = {
        "true_positive": sum(left and right for left, right in zip(predicted, observed)),
        "false_positive": sum(left and not right for left, right in zip(predicted, observed)),
        "true_negative": sum(not left and not right for left, right in zip(predicted, observed)),
        "false_negative": sum(not left and right for left, right in zip(predicted, observed)),
    }
    return {
        "schema_version": 1,
        "phase": "V3_6_SCALAR_CONFIRMATION",
        "scientific_status": scientific,
        "primary_conditions": conditions,
        "planned": 15,
        "valid": len(valid),
        "invalid": 15 - len(valid),
        "strict_wins_out_of_planned_15": strict_wins,
        "strict_losses": strict_losses,
        "ties": ties,
        "sign_test_non_tied_denominator": non_tied,
        "exact_one_sided_sign_p": sign_p,
        "median_D": median_d,
        "status_counts": {
            status: sum(record["status"] == status for record in records)
            for status in ["PASS", "CHECKPOINT_INVALID", "PROFILE_FAILURE", "SOLVER_FAILURE", "NUMERICAL_FAILURE"]
        },
        "secondary": {
            "E_SAEPS_all_valid": e_saeps,
            "E_SAEPS_median": statistics.median(e_saeps) if e_saeps else None,
            "E_SAEPS_q25": float(np.quantile(e_saeps, 0.25, method="linear")) if e_saeps else None,
            "E_SAEPS_q75": float(np.quantile(e_saeps, 0.75, method="linear")) if e_saeps else None,
            "E_SAEPS_IQR": float(np.quantile(e_saeps, 0.75, method="linear") - np.quantile(e_saeps, 0.25, method="linear")) if e_saeps else None,
            "E_SAEPS_range": [min(e_saeps), max(e_saeps)] if e_saeps else None,
            "E_SAEPS_within_5_percent_count": sum(value <= 0.05 for value in e_saeps),
            "E_raw_all_valid": e_raw,
        },
        "gn_indicator": {
            "threshold": threshold,
            "values": indicators,
            "confusion_matrix": confusion,
            "accuracy": sum(left == right for left, right in zip(predicted, observed)) / len(valid) if valid else None,
            "spearman_with_E_SAEPS": _spearman(indicators, e_saeps),
            "median_absolute_calibration_error": statistics.median(abs(left - right) for left, right in zip(indicators, e_saeps)) if valid else None,
        },
        "per_seed": [
            {
                "seed": record["seed"],
                "status": record["status"],
                "failure_stage": record["failure_stage"],
                "E_raw": record["E_raw"],
                "E_SAEPS": record["E_SAEPS"],
                "D": record["D"],
                "I_GN": record["I_GN"],
            }
            for record in records
        ],
    }


def run_v36_confirmation(
    config_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
    authorization_path: str | Path,
    preflight_path: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    destination = Path(output_root).resolve()
    if destination.exists():
        raise RuntimeError("v3.6 one-shot output root already exists; rerun is forbidden")
    specification = load_config(config_path)
    lock_record = json.loads((root / "configs/v3_6/LOCK_RECORD.json").read_text(encoding="utf-8"))
    if _sha256(Path(config_path)) != lock_record["locked_config_sha256"]:
        raise RuntimeError("locked v3.6 config hash mismatch")
    if specification["planned_seeds"] != list(range(30, 45)):
        raise RuntimeError("planned seeds changed")
    authorization = json.loads(Path(authorization_path).read_text(encoding="utf-8"))
    if authorization.get("execution_authorized") is not True:
        raise RuntimeError("separate v3.6 execution authorization is absent")
    preflight = json.loads(Path(preflight_path).read_text(encoding="utf-8"))
    if preflight.get("status") != "PASSED" or preflight.get("confirmation_runs_observed") != 0:
        raise RuntimeError("pre-confirmation audit is not a clean PASS")
    provenance = environment_provenance(root, "float64", "cpu")
    if provenance["git_dirty"]:
        raise RuntimeError("formal confirmation must start from a clean commit")
    provenance["repo_root"] = str(root)
    destination.mkdir(parents=True, exist_ok=False)
    records_dir = destination / "records"
    records_dir.mkdir()
    claim = {
        "schema_version": 1,
        "state": "EXECUTION_CLAIMED_ONE_SHOT",
        "planned_seeds": specification["planned_seeds"],
        "config_sha256": lock_record["locked_config_sha256"],
        "git_commit": provenance["git_commit"],
        "timestamp": provenance["timestamp"],
        "rerun_forbidden": True,
    }
    _write_json(destination / "execution_claim.json", claim)

    scalar_path = root / specification["source_files"]["scalar_config"]["path"]
    scalar_locked = load_config(scalar_path)
    runtime = _runtime_config(scalar_locked)
    truth = solve_truth(runtime, "Burgers")
    records: list[dict[str, Any]] = []
    manifest_rows = []
    for seed in specification["planned_seeds"]:
        record = _run_seed(int(seed), specification, scalar_locked, runtime, truth, provenance)
        record_path = records_dir / f"seed_{seed}.json"
        _write_json(record_path, record)
        manifest_rows.append(
            {
                "seed": seed,
                "status": record["status"],
                "path": str(record_path.relative_to(destination)).replace("\\", "/"),
                "sha256": _sha256(record_path),
            }
        )
        records.append(record)
    aggregate = _aggregate(records, specification)
    aggregate.update(
        config_sha256=lock_record["locked_config_sha256"],
        lock_commit=lock_record["lock_commit"],
        provenance={key: value for key, value in provenance.items() if key != "repo_root"},
        execution_claim=claim,
    )
    _write_json(destination / "summary.json", aggregate)
    failed = [
        {
            "seed": record["seed"],
            "status": record["status"],
            "failure_stage": record["failure_stage"],
            "failure_reason": record["failure_reason"],
        }
        for record in records
        if record["status"] != "PASS"
    ]
    _write_json(destination / "failed_seeds.json", {"schema_version": 1, "failed": failed})
    manifest = {
        "schema_version": 1,
        "planned": 15,
        "records": manifest_rows,
        "raw_records_sha256": hashlib.sha256(
            json.dumps(manifest_rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }
    _write_json(destination / "manifest.json", manifest)
    return aggregate

