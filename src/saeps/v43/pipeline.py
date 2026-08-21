"""Fail-soft Allen--Cahn external-replication development pipeline."""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any, Callable

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.p4_screening import _stationarity
from saeps.provenance import environment_provenance
from saeps.scalar import scalar_residual, solve_truth, train_scalar_checkpoint
from saeps.v3.foundation import full_hessian_references
from saeps.v31.pipeline import _mean_residual_objective
from saeps.v34.profile import run_resolution_profile
from saeps.v35.engineering import center_with_registered_rescue, scaled_augmented_lsqr_candidates
from saeps.v35.second_order import second_order_reduced_decomposition
from saeps.v36.pipeline import _center_specs, _relative
from saeps.v41.numerics import binding_curvature_gate, explicit_curvature_reference, explicit_score_diagnostic
from saeps.v43.indicator import directional_first_order_correction


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _protected_config(root: Path, source: dict[str, str]) -> dict[str, Any]:
    path = root / source["path"]
    if _sha256(path) != source["sha256"]:
        raise RuntimeError(f"protected source changed: {source['path']}")
    return load_config(path)


def _initial_record(seed: int, digest: str, provenance: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "phase": "V4_3_ALLEN_CAHN_EXTERNAL_DEVELOPMENT",
        "role": "ENGINEERING_DEVELOPMENT_ONLY",
        "benchmark": "Allen-Cahn",
        "seed": seed,
        "config_hash": digest,
        "git_commit": provenance["git_commit"],
        "status": "NUMERICAL_FAILURE",
        "failure_reason": None,
        "binding_valid": False,
        "statuses": {
            "center_status": "NOT_COMPUTED",
            "parameter_reference_status": "NOT_COMPUTED",
            "curvature_solver_status": "NOT_COMPUTED",
            "score_solver_status": "NOT_COMPUTED",
            "exact_reference_status": "NOT_COMPUTED",
            "finite_primary_status": "NOT_COMPUTED",
            "profile_status": "NOT_COMPUTED",
            "directional_indicator_status": "NOT_COMPUTED",
        },
        "training": None,
        "center": None,
        "center_stationarity": None,
        "gamma": None,
        "F_raw": None,
        "F_se_explicit": None,
        "F_se_GN": None,
        "H_red_exact_gamma": None,
        "E_raw": None,
        "E_SAEPS": None,
        "D": None,
        "I_GN": None,
        "parameter_reference": None,
        "curvature_solver": None,
        "score_diagnostic": None,
        "exact_hessian": None,
        "directional_indicator": None,
        "gamma_matched_profile": None,
        "gate_graph": None,
        "computation_errors": {},
        "elapsed_seconds": None,
    }


def run_allen_development_seed(
    seed: int,
    config_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    specification = load_config(config_path)
    if specification["confirmation_authorized"] is not False:
        raise RuntimeError("Allen-Cahn development cannot authorize confirmation")
    if seed not in [int(value) for value in specification["development_seeds"]]:
        raise ValueError("seed is not authorized for Allen-Cahn development")
    sources = specification["protected_sources"]
    runtime = _protected_config(root, sources["scalar_runtime"])
    curvature = _protected_config(root, sources["curvature_protocol"])
    profile_protocol = _protected_config(root, sources["profile_protocol"])
    benchmark = str(specification["benchmark"])
    provenance = environment_provenance(root, runtime["dtype"], "cpu")
    if provenance["git_dirty"]:
        raise RuntimeError("formal development seed requires clean provenance")

    destination = Path(output_root) / f"seed_{seed}"
    destination.mkdir(parents=True, exist_ok=False)
    digest = config_hash(specification)
    record = _initial_record(seed, digest, provenance)
    started = time.perf_counter()
    try:
        truth = solve_truth(runtime, benchmark)
        checkpoint, points = train_scalar_checkpoint(runtime, benchmark, seed, truth)
        residual_function: ResidualFunction = lambda theta, parameter: scalar_residual(
            theta, parameter, benchmark, points, truth, runtime
        )
        parameter = checkpoint.log_parameter.detach().clone()
        objective = _mean_residual_objective(residual_function, parameter, checkpoint.theta, 0.0, False)
        local, enhanced = _center_specs(curvature)
        theta, center = center_with_registered_rescue(objective, checkpoint.theta, local, enhanced)
        record["training"] = {
            "seconds": checkpoint.elapsed_seconds,
            "stop_reason": checkpoint.stop_reason,
            "loss_mean": checkpoint.training_loss,
            "state_rmse_validation_only": checkpoint.state_rmse,
            "parameter_relative_error_validation_only": checkpoint.parameter_relative_error,
        }
        record["center"] = center
        if theta is None:
            record["statuses"]["center_status"] = "CHECKPOINT_INVALID"
            record["status"] = "CHECKPOINT_INVALID"
            record["failure_reason"] = "frozen center policy failed"
            return record

        linearization = ResidualLinearization(residual_function, theta, parameter)
        residual = linearization.residual()
        jacobian_theta, jacobian_parameter = linearization.explicit_jacobians()
        selected = center["baseline"] if center["selected_method"] == "baseline_v3_4_exact_trust" else center["enhanced"]
        g_theta = float(selected["final"]["normalized_objective_gradient"])
        s_theta = _stationarity(jacobian_theta, residual)
        s_lambda = _stationarity(jacobian_parameter, residual)
        center_pass = (
            g_theta < float(curvature["center"]["required_objective_gradient_tolerance"])
            and s_theta < float(curvature["center"]["residual_stationarity_tolerance"])
        )
        record["center_stationarity"] = {"G_theta": g_theta, "S_theta": s_theta, "S_lambda": s_lambda}
        record["statuses"]["center_status"] = "PASS" if center_pass else "CHECKPOINT_INVALID"
        if not center_pass:
            record["status"] = "CHECKPOINT_INVALID"
            record["failure_reason"] = "frozen center stationarity gate failed"
            return record

        gamma = float(curvature["gamma"]["alpha"]) * float(
            torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item()
        )
        record["gamma"] = gamma
        record["F_raw"] = float(torch.dot(jacobian_parameter[:, 0], jacobian_parameter[:, 0]).item())

        try:
            reference = explicit_curvature_reference(jacobian_theta, jacobian_parameter, gamma)
            record["parameter_reference"] = reference
            record["F_se_explicit"] = reference["Fse_explicit"]
            record["statuses"]["parameter_reference_status"] = reference["parameter_reference_status"]
        except Exception as error:
            record["statuses"]["parameter_reference_status"] = "NUMERICAL_FAILURE"
            record["computation_errors"]["parameter_reference"] = f"{type(error).__name__}: {error}"

        try:
            score = explicit_score_diagnostic(jacobian_theta, residual, gamma)
            record["score_diagnostic"] = score
            record["statuses"]["score_solver_status"] = score["score_solver_status"]
        except Exception as error:
            record["statuses"]["score_solver_status"] = "SOLVER_FAILURE"
            record["computation_errors"]["score_diagnostic"] = f"{type(error).__name__}: {error}"

        try:
            solver_spec = curvature["curvature_solver"]
            candidates = scaled_augmented_lsqr_candidates(
                linearization,
                jacobian_parameter[:, 0],
                gamma,
                float(solver_spec["tolerance"]),
                int(solver_spec["max_iterations_per_pass"]),
                int(solver_spec["refinement_passes"]),
            )
            solved = candidates["scaled_LSQR_iterative_refinement"]
            record["F_se_GN"] = float(solved["Fse"])
            comparison = (
                _relative(record["F_se_GN"], float(record["F_se_explicit"]))
                if record["F_se_explicit"] is not None
                else None
            )
            solver_pass = (
                solved["verified_original_relative_normal_residual"]
                <= float(solver_spec["verified_normal_residual_acceptance"])
                and comparison is not None
                and comparison <= float(solver_spec["explicit_reference_relative_acceptance"])
                and solved["total_iterations"] <= int(solver_spec["maximum_total_iterations"])
            )
            record["statuses"]["curvature_solver_status"] = "PASS" if solver_pass else "SOLVER_FAILURE"
            record["curvature_solver"] = {
                "verified_original_relative_normal_residual": solved["verified_original_relative_normal_residual"],
                "selected_vs_explicit_relative_error": comparison,
                "iterations": solved["total_iterations"],
                "setup_jvp_count": candidates["setup_jvp_count"],
                "passes": solved["passes"],
            }
        except Exception as error:
            record["statuses"]["curvature_solver_status"] = "SOLVER_FAILURE"
            record["computation_errors"]["curvature_solver"] = f"{type(error).__name__}: {error}"

        decomposition = None
        try:
            full = full_hessian_references(
                residual_function, theta, parameter, gamma, curvature["gold_standard"]
            )
            decomposition = second_order_reduced_decomposition(
                residual_function, theta, parameter, gamma, float(curvature["errors"]["denominator_floor"])
            )
            gamma_gold = full["gamma_matched"]
            exact = float(gamma_gold["reduced_hessian"][0][0]) if gamma_gold["reduced_hessian"] is not None else None
            cross_error = _relative(float(decomposition["Hred_exact_gamma"]), exact) if exact is not None else None
            exact_pass = (
                full["symmetry_relative_error"] <= float(curvature["gold_standard"]["symmetry_relative_tolerance"])
                and gamma_gold["status"] == "PASS"
                and cross_error is not None
                and cross_error <= float(curvature["gold_standard"]["solve_relative_tolerance"])
            )
            record["statuses"]["exact_reference_status"] = "PASS" if exact_pass else "NUMERICAL_FAILURE"
            record["H_red_exact_gamma"] = exact
            record["I_GN"] = float(decomposition["block_ratios_and_indicators"]["first_order_correction_relative_to_GN"])
            record["exact_hessian"] = {
                "symmetry_relative_error": full["symmetry_relative_error"],
                "gamma_matched": gamma_gold,
                "decomposition_crosscheck_relative_error": cross_error,
                "first_order_reduced_correction": decomposition["first_order_reduced_correction"],
            }
        except Exception as error:
            record["statuses"]["exact_reference_status"] = "NUMERICAL_FAILURE"
            record["computation_errors"]["exact_reference"] = f"{type(error).__name__}: {error}"

        try:
            directional = directional_first_order_correction(residual_function, theta, parameter, gamma)
            explicit_value = float(decomposition["first_order_reduced_correction"]) if decomposition is not None else None
            agreement = _relative(directional["first_order_reduced_correction"], explicit_value) if explicit_value is not None else None
            directional["explicit_relative_error"] = agreement
            indicator_pass = agreement is not None and agreement <= float(
                specification["directional_indicator"]["explicit_relative_tolerance"]
            )
            record["directional_indicator"] = directional
            record["statuses"]["directional_indicator_status"] = "PASS" if indicator_pass else "NUMERICAL_FAILURE"
        except Exception as error:
            record["statuses"]["directional_indicator_status"] = "NUMERICAL_FAILURE"
            record["computation_errors"]["directional_indicator"] = f"{type(error).__name__}: {error}"

        try:
            matched_profile = run_resolution_profile(
                residual_function,
                theta,
                parameter,
                gamma,
                curvature["center"]["local_minimum"],
                profile_protocol["profile"],
                profile_protocol["branch_audit"],
                int(runtime["network"]["hidden_width"]),
                float(runtime["domain"]["t"][1]),
            )
            record["gamma_matched_profile"] = matched_profile
            record["statuses"]["profile_status"] = matched_profile["status"]
        except Exception as error:
            record["statuses"]["profile_status"] = "PROFILE_FAILURE"
            record["computation_errors"]["gamma_matched_profile"] = f"{type(error).__name__}: {error}"

        primary_values = [record[key] for key in ["F_raw", "F_se_GN", "H_red_exact_gamma", "I_GN"]]
        finite = all(value is not None and math.isfinite(float(value)) for value in primary_values)
        record["statuses"]["finite_primary_status"] = "PASS" if finite else "NUMERICAL_FAILURE"
        gate = binding_curvature_gate(
            record["statuses"]["parameter_reference_status"],
            record["statuses"]["curvature_solver_status"],
            record["statuses"]["score_solver_status"],
        )
        record["gate_graph"] = gate
        record["binding_valid"] = (
            record["statuses"]["center_status"] == "PASS"
            and gate["CURVATURE_GATE"] == "PASS"
            and record["statuses"]["exact_reference_status"] == "PASS"
            and record["statuses"]["finite_primary_status"] == "PASS"
        )
        if finite:
            denominator = abs(float(record["H_red_exact_gamma"])) + float(curvature["errors"]["denominator_floor"])
            record["E_raw"] = abs(float(record["F_raw"]) - float(record["H_red_exact_gamma"])) / denominator
            record["E_SAEPS"] = abs(float(record["F_se_GN"]) - float(record["H_red_exact_gamma"])) / denominator
            record["D"] = record["E_raw"] - record["E_SAEPS"]
        if record["binding_valid"]:
            record["status"] = "PASS"
            record["failure_reason"] = None
        elif gate["CURVATURE_GATE"] != "PASS":
            record["status"] = "SOLVER_FAILURE"
            record["failure_reason"] = "binding curvature gate failed"
        else:
            record["status"] = "NUMERICAL_FAILURE"
            record["failure_reason"] = "binding exact or finite-primary node failed"
        return record
    except Exception as error:
        record["status"] = "NUMERICAL_FAILURE"
        record["failure_reason"] = f"unhandled seed-level failure: {type(error).__name__}: {error}"
        record["computation_errors"]["seed_level"] = record["failure_reason"]
        return record
    finally:
        record["elapsed_seconds"] = time.perf_counter() - started
        record_path = destination / "result.json"
        _write(record_path, record)
        _write(
            destination / "manifest.json",
            {
                "schema_version": 1,
                "phase": specification["phase"],
                "seed": seed,
                "status": record["status"],
                "binding_valid": record["binding_valid"],
                "result_path": "result.json",
                "result_sha256": _sha256(record_path),
                "scientific_gate": "NONE_DEVELOPMENT_ONLY",
            },
        )

