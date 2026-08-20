"""V4.1 fail-soft post-confirmation development pipeline."""

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
from saeps.p5_confirmation import _runtime_config
from saeps.provenance import environment_provenance
from saeps.scalar import scalar_residual, solve_truth, train_scalar_checkpoint
from saeps.v3.foundation import full_hessian_references
from saeps.v31.pipeline import _mean_residual_objective
from saeps.v35.engineering import center_with_registered_rescue, scaled_augmented_lsqr_candidates
from saeps.v35.second_order import second_order_reduced_decomposition
from saeps.v36.pipeline import _center_specs, _relative
from saeps.v41.numerics import (
    binding_curvature_gate,
    explicit_curvature_reference,
    explicit_score_diagnostic,
)


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _protected_v36(root: Path, specification: dict[str, Any]) -> dict[str, Any]:
    source = specification["source_v3_6_protocol"]
    path = root / source["path"]
    if _sha256(path) != source["sha256"]:
        raise RuntimeError("protected v3.6 protocol changed")
    result_record = json.loads(
        (root / "configs/v3_6/CONFIRMATION_RESULT_RECORD.json").read_text(encoding="utf-8")
    )
    if result_record["rerun_permitted"] is not False:
        raise RuntimeError("v3.6 permanent closure is not protected")
    return load_config(path)


def _initial_record(seed: int, role: str, config_digest: str, provenance: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "phase": "V4_1_POST_CONFIRMATION_DEVELOPMENT",
        "role": role,
        "seed": seed,
        "config_hash": config_digest,
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
        },
        "gate_graph": None,
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
        "computation_errors": {},
        "elapsed_seconds": None,
    }


def _run_seed(
    seed: int,
    role: str,
    specification: dict[str, Any],
    v36: dict[str, Any],
    runtime: dict[str, Any],
    truth: Any,
    provenance: dict[str, Any],
    config_digest: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    record = _initial_record(seed, role, config_digest, provenance)
    try:
        checkpoint, points = train_scalar_checkpoint(runtime, "Burgers", seed, truth)
        residual_function: ResidualFunction = lambda theta, parameter: scalar_residual(
            theta, parameter, "Burgers", points, truth, runtime
        )
        parameter = checkpoint.log_parameter.detach().clone()
        objective = _mean_residual_objective(
            residual_function, parameter, checkpoint.theta, 0.0, False
        )
        local, enhanced = _center_specs(v36)
        theta, center = center_with_registered_rescue(objective, checkpoint.theta, local, enhanced)
        record["training"] = {
            "seconds": checkpoint.elapsed_seconds,
            "stop_reason": checkpoint.stop_reason,
            "state_rmse_validation_only": checkpoint.state_rmse,
        }
        record["center"] = center
        if theta is None:
            record["statuses"]["center_status"] = "CHECKPOINT_INVALID"
            record["status"] = "CHECKPOINT_INVALID"
            record["failure_reason"] = "frozen center policy failed"
            return record

        linearization = ResidualLinearization(residual_function, theta, parameter)
        residual = linearization.residual()
        jt, jl = linearization.explicit_jacobians()
        selected_center = center["baseline"] if center["selected_method"] == "baseline_v3_4_exact_trust" else center["enhanced"]
        g_theta = float(selected_center["final"]["normalized_objective_gradient"])
        s_theta = _stationarity(jt, residual)
        s_lambda = _stationarity(jl, residual)
        center_pass = (
            g_theta < float(v36["center"]["required_objective_gradient_tolerance"])
            and s_theta < float(v36["center"]["residual_stationarity_tolerance"])
        )
        record["center_stationarity"] = {"G_theta": g_theta, "S_theta": s_theta, "S_lambda": s_lambda}
        record["statuses"]["center_status"] = "PASS" if center_pass else "CHECKPOINT_INVALID"
        if not center_pass:
            record["status"] = "CHECKPOINT_INVALID"
            record["failure_reason"] = "frozen center stationarity gate failed"
            return record

        gamma = float(v36["gamma"]["alpha"]) * float(torch.linalg.eigvalsh(jt.T @ jt).max().item())
        record["gamma"] = gamma
        record["F_raw"] = float(torch.dot(jl[:, 0], jl[:, 0]).item())

        try:
            parameter_reference = explicit_curvature_reference(jt, jl, gamma)
            record["parameter_reference"] = parameter_reference
            record["F_se_explicit"] = parameter_reference["Fse_explicit"]
            record["statuses"]["parameter_reference_status"] = parameter_reference[
                "parameter_reference_status"
            ]
        except Exception as error:
            record["statuses"]["parameter_reference_status"] = "NUMERICAL_FAILURE"
            record["computation_errors"]["parameter_reference"] = f"{type(error).__name__}: {error}"

        try:
            score = explicit_score_diagnostic(jt, residual, gamma)
            record["score_diagnostic"] = score
            record["statuses"]["score_solver_status"] = score["score_solver_status"]
        except Exception as error:
            record["statuses"]["score_solver_status"] = "SOLVER_FAILURE"
            record["computation_errors"]["score_diagnostic"] = f"{type(error).__name__}: {error}"

        try:
            solver_spec = v36["curvature_solver"]
            scaled = scaled_augmented_lsqr_candidates(
                linearization,
                jl[:, 0],
                gamma,
                float(solver_spec["tolerance"]),
                int(solver_spec["max_iterations_per_pass"]),
                int(solver_spec["refinement_passes"]),
            )
            selected = scaled["scaled_LSQR_iterative_refinement"]
            fse = float(selected["Fse"])
            record["F_se_GN"] = fse
            comparison = (
                _relative(fse, float(record["F_se_explicit"]))
                if record["F_se_explicit"] is not None
                else None
            )
            solver_pass = (
                float(selected["verified_original_relative_normal_residual"])
                <= float(solver_spec["verified_normal_residual_acceptance"])
                and comparison is not None
                and comparison <= float(solver_spec["explicit_reference_relative_acceptance"])
                and int(selected["total_iterations"]) <= int(solver_spec["maximum_total_iterations"])
            )
            record["statuses"]["curvature_solver_status"] = "PASS" if solver_pass else "SOLVER_FAILURE"
            record["curvature_solver"] = {
                "curvature_solver_status": record["statuses"]["curvature_solver_status"],
                "binding": True,
                "verified_original_relative_normal_residual": selected[
                    "verified_original_relative_normal_residual"
                ],
                "selected_vs_explicit_relative_error": comparison,
                "iterations": selected["total_iterations"],
                "setup_jvp_count": scaled["setup_jvp_count"],
                "passes": selected["passes"],
            }
        except Exception as error:
            record["statuses"]["curvature_solver_status"] = "SOLVER_FAILURE"
            record["computation_errors"]["curvature_solver"] = f"{type(error).__name__}: {error}"

        try:
            full = full_hessian_references(
                residual_function, theta, parameter, gamma, v36["gold_standard"]
            )
            decomposition = second_order_reduced_decomposition(
                residual_function,
                theta,
                parameter,
                gamma,
                float(v36["errors"]["denominator_floor"]),
            )
            gamma_gold = full["gamma_matched"]
            h_exact = float(gamma_gold["reduced_hessian"][0][0]) if gamma_gold["reduced_hessian"] is not None else None
            cross_error = _relative(float(decomposition["Hred_exact_gamma"]), h_exact) if h_exact is not None else None
            exact_pass = (
                full["symmetry_relative_error"] <= float(v36["gold_standard"]["symmetry_relative_tolerance"])
                and gamma_gold["status"] == "PASS"
                and cross_error is not None
                and cross_error <= float(v36["gold_standard"]["solve_relative_tolerance"])
            )
            record["statuses"]["exact_reference_status"] = "PASS" if exact_pass else "NUMERICAL_FAILURE"
            record["H_red_exact_gamma"] = h_exact
            record["I_GN"] = float(
                decomposition["block_ratios_and_indicators"]["first_order_correction_relative_to_GN"]
            )
            record["exact_hessian"] = {
                "exact_reference_status": record["statuses"]["exact_reference_status"],
                "binding": True,
                "symmetry_relative_error": full["symmetry_relative_error"],
                "gamma_matched": gamma_gold,
                "decomposition_crosscheck_relative_error": cross_error,
                "first_order_reduced_correction": decomposition["first_order_reduced_correction"],
            }
        except Exception as error:
            record["statuses"]["exact_reference_status"] = "NUMERICAL_FAILURE"
            record["computation_errors"]["exact_reference"] = f"{type(error).__name__}: {error}"

        computable = [record[key] for key in ["F_raw", "F_se_GN", "H_red_exact_gamma", "I_GN"]]
        finite = all(value is not None and math.isfinite(float(value)) for value in computable)
        record["statuses"]["finite_primary_status"] = "PASS" if finite else "NUMERICAL_FAILURE"
        gate = binding_curvature_gate(
            record["statuses"]["parameter_reference_status"],
            record["statuses"]["curvature_solver_status"],
            record["statuses"]["score_solver_status"],
        )
        record["gate_graph"] = gate
        binding_valid = (
            record["statuses"]["center_status"] == "PASS"
            and gate["CURVATURE_GATE"] == "PASS"
            and record["statuses"]["exact_reference_status"] == "PASS"
            and record["statuses"]["finite_primary_status"] == "PASS"
        )
        record["binding_valid"] = binding_valid

        if finite:
            denominator = abs(float(record["H_red_exact_gamma"])) + float(v36["errors"]["denominator_floor"])
            record["E_raw"] = abs(float(record["F_raw"]) - float(record["H_red_exact_gamma"])) / denominator
            record["E_SAEPS"] = abs(float(record["F_se_GN"]) - float(record["H_red_exact_gamma"])) / denominator
            record["D"] = float(record["E_raw"]) - float(record["E_SAEPS"])
        if binding_valid:
            record["status"] = "PASS"
            record["failure_reason"] = None
        elif record["statuses"]["exact_reference_status"] != "PASS":
            record["status"] = "NUMERICAL_FAILURE"
            record["failure_reason"] = "binding exact-reference node failed"
        elif gate["CURVATURE_GATE"] != "PASS":
            record["status"] = "SOLVER_FAILURE"
            record["failure_reason"] = "binding curvature gate failed"
        else:
            record["status"] = "NUMERICAL_FAILURE"
            record["failure_reason"] = "binding finite-primary node failed"
        return record
    except Exception as error:
        record["status"] = "NUMERICAL_FAILURE"
        record["failure_reason"] = f"unhandled seed-level failure: {type(error).__name__}: {error}"
        record["computation_errors"]["seed_level"] = record["failure_reason"]
        return record
    finally:
        record["elapsed_seconds"] = time.perf_counter() - started


def run_v41_cohort(
    role: str,
    config_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    specification = load_config(config_path)
    roles = {
        "ENGINEERING_INTEGRATION": specification["engineering_integration_seeds"],
        "HELDOUT_DEVELOPMENT": specification["heldout_development_seeds"],
    }
    if role not in roles or specification["confirmation_authorized"] is not False:
        raise ValueError("invalid v4.1 development role")
    if role == "HELDOUT_DEVELOPMENT":
        freeze_path = root / "configs/v4_1/EXECUTABLE_FREEZE.json"
        if not freeze_path.is_file():
            raise RuntimeError("held-out development requires executable freeze")
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        for path_name, expected in freeze["file_sha256"].items():
            if _sha256(root / path_name) != expected:
                raise RuntimeError(f"held-out executable freeze mismatch: {path_name}")
    v36 = _protected_v36(root, specification)
    scalar_path = root / v36["source_files"]["scalar_config"]["path"]
    scalar = load_config(scalar_path)
    runtime = _runtime_config(scalar)
    provenance = environment_provenance(root, scalar["dtype"], scalar["device"])
    if provenance["git_dirty"]:
        raise RuntimeError("formal development cohort requires clean provenance")
    destination = Path(output_root) / role.lower()
    destination.mkdir(parents=True, exist_ok=False)
    records_dir = destination / "records"
    records_dir.mkdir()
    truth = solve_truth(runtime, "Burgers")
    digest = config_hash(specification)
    records = []
    manifest_rows = []
    for seed in roles[role]:
        record = _run_seed(int(seed), role, specification, v36, runtime, truth, provenance, digest)
        path = records_dir / f"seed_{seed}.json"
        _write(path, record)
        manifest_rows.append(
            {
                "seed": seed,
                "status": record["status"],
                "binding_valid": record["binding_valid"],
                "path": str(path.relative_to(destination)).replace("\\", "/"),
                "sha256": _sha256(path),
            }
        )
        records.append(record)
    summary = {
        "schema_version": 1,
        "phase": specification["phase"],
        "role": role,
        "seeds": roles[role],
        "config_hash": digest,
        "provenance": provenance,
        "binding_valid_count": sum(record["binding_valid"] for record in records),
        "score_computed_count": sum(
            record["statuses"]["score_solver_status"] != "NOT_COMPUTED" for record in records
        ),
        "score_failure_count": sum(
            record["statuses"]["score_solver_status"] == "SOLVER_FAILURE" for record in records
        ),
        "record_all_computable_count": sum(
            all(record[key] is not None for key in ["F_raw", "F_se_explicit", "F_se_GN", "H_red_exact_gamma"])
            for record in records
        ),
        "records": [
            {
                "seed": record["seed"],
                "status": record["status"],
                "binding_valid": record["binding_valid"],
                "statuses": record["statuses"],
                "D": record["D"],
            }
            for record in records
        ],
        "scientific_gate": "NONE_DEVELOPMENT_ONLY",
    }
    _write(destination / "summary.json", summary)
    _write(
        destination / "manifest.json",
        {"schema_version": 1, "planned": 5, "records": manifest_rows},
    )
    return summary
