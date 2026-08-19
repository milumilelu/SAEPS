"""V3.4 curvature-validation pipeline with separated solver gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.p4_screening import _stationarity
from saeps.p5_confirmation import _runtime_config
from saeps.provenance import environment_provenance, make_run_id
from saeps.scalar import scalar_residual, solve_truth, train_scalar_checkpoint
from saeps.v3.foundation import full_hessian_references
from saeps.v31.local_minimum import optimize_state_local_minimum
from saeps.v31.pipeline import V2_SCALAR_SHA256, _mean_residual_objective
from saeps.v33.pipeline import (
    _augmented_lsqr_reference,
    _direct_augmented_reference,
    _matrix_free_normal_solvers,
    _relative,
)
from saeps.v34.profile import run_resolution_profile


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def _solver_hierarchy(
    explicit: dict[str, Any],
    matrix_free: dict[str, Any],
    lsqr: dict[str, Any],
    specification: dict[str, Any],
) -> dict[str, Any]:
    explicit_value = float(explicit["Fse"][0][0])
    explicit_parameter_residual = float(
        explicit["right_hand_side_relative_normal_residuals"][0]
    )
    explicit_pass = (
        explicit_parameter_residual
        <= float(specification["explicit_parameter_relative_normal_residual"])
        and float(explicit["objective_projection_identity_relative_error"])
        <= float(specification["explicit_objective_identity_tolerance"])
    )
    acceptance = float(specification["parameter_residual_acceptance"])
    curvature_tolerance = float(specification["curvature_relative_acceptance"])

    cg = matrix_free["standard_cg"]
    cg_error = _relative(float(cg["Fse"][0][0]), explicit_value)
    cg_pass = bool(cg["converged"][0]) and float(
        cg["verified_relative_residuals"][0]
    ) <= acceptance and cg_error < curvature_tolerance

    lsqr_error = _relative(float(lsqr["Fse"][0][0]), explicit_value)
    lsqr_pass = bool(lsqr["converged"][0]) and float(
        lsqr["relative_normal_residuals"][0]
    ) <= acceptance and lsqr_error < curvature_tolerance

    pcg = matrix_free["jacobi_pcg"]
    pcg_error = _relative(float(pcg["Fse"][0][0]), explicit_value)
    pcg_parameter_pass = bool(pcg["converged"][0]) and float(
        pcg["verified_relative_residuals"][0]
    ) <= acceptance

    cg_score_pass = bool(cg["converged"][-1]) and float(
        cg["verified_relative_residuals"][-1]
    ) <= acceptance
    lsqr_score_pass = bool(lsqr["converged"][-1]) and float(
        lsqr["relative_normal_residuals"][-1]
    ) <= acceptance
    return {
        "CURVATURE_SOLVER_GATE": {
            "status": "PASS" if explicit_pass and (cg_pass or lsqr_pass) else "SOLVER_FAILURE",
            "explicit_direct_reference": {
                "status": "PASS" if explicit_pass else "NUMERICAL_FAILURE",
                "Fse": explicit_value,
                "parameter_relative_normal_residual": explicit_parameter_residual,
            },
            "scalable_candidates": {
                "standard_CG": {
                    "status": "PASS" if cg_pass else "SOLVER_FAILURE",
                    "Fse": float(cg["Fse"][0][0]),
                    "parameter_relative_residual": float(
                        cg["verified_relative_residuals"][0]
                    ),
                    "curvature_relative_error": cg_error,
                    "iterations": int(cg["iterations"][0]),
                },
                "augmented_LSQR": {
                    "status": "PASS" if lsqr_pass else "SOLVER_FAILURE",
                    "Fse": float(lsqr["Fse"][0][0]),
                    "parameter_relative_normal_residual": float(
                        lsqr["relative_normal_residuals"][0]
                    ),
                    "curvature_relative_error": lsqr_error,
                    "iterations": int(lsqr["iterations"][0]),
                },
            },
            "binding": True,
        },
        "SCORE_SOLVER_GATE": {
            "status": "PASS" if cg_score_pass or lsqr_score_pass else "SOLVER_FAILURE",
            "standard_CG_residual_rhs_relative_residual": float(
                cg["verified_relative_residuals"][-1]
            ),
            "augmented_LSQR_residual_rhs_relative_normal_residual": float(
                lsqr["relative_normal_residuals"][-1]
            ),
            "binding": False,
        },
        "PRECONDITIONER_DIAGNOSTIC": {
            "status": "PASS" if pcg_parameter_pass else "SOLVER_FAILURE",
            "method": "Jacobi-PCG",
            "Fse": float(pcg["Fse"][0][0]),
            "parameter_relative_residual": float(pcg["verified_relative_residuals"][0]),
            "curvature_relative_error": pcg_error,
            "residual_rhs_relative_residual": float(
                pcg["verified_relative_residuals"][-1]
            ),
            "binding": False,
        },
    }


def run_curvature_validation_seed(
    seed: int,
    config_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root)
    specification = load_config(config_path)
    allowed = [int(specification["protocol_seed"])] + [
        int(value) for value in specification["evaluation_seeds"]
    ]
    if seed not in allowed or specification["confirmation_authorized"] is not False:
        raise ValueError("seed is not authorized for v3.4 development")
    locked_path = root / specification["source_scalar_config"]
    if hashlib.sha256(locked_path.read_bytes()).hexdigest() != V2_SCALAR_SHA256:
        raise RuntimeError("v2 scalar lock changed")
    locked = load_config(locked_path)
    runtime = _runtime_config(locked)
    provenance = environment_provenance(root, locked["dtype"], locked["device"])
    digest = config_hash(specification)
    run_id = make_run_id("V3-4-curvature", seed, digest, provenance["timestamp"])
    destination = Path(output_root) / run_id
    destination.mkdir(parents=True, exist_ok=False)

    truth = solve_truth(runtime, "Burgers")
    checkpoint, points = train_scalar_checkpoint(runtime, "Burgers", seed, truth)
    residual_function: ResidualFunction = lambda theta, parameter: scalar_residual(
        theta, parameter, "Burgers", points, truth, runtime
    )
    parameter_center = checkpoint.log_parameter.detach().clone()
    center_objective = _mean_residual_objective(
        residual_function, parameter_center, checkpoint.theta, 0.0, False
    )
    theta_center, center = optimize_state_local_minimum(
        center_objective, checkpoint.theta, specification["local_minimum"]
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "phase": specification["phase"],
        "run_id": run_id,
        "seed": seed,
        "seed_role": "PROTOCOL" if seed == int(specification["protocol_seed"]) else "EVALUATION",
        "config_hash": digest,
        "v2_scalar_lock_sha256": V2_SCALAR_SHA256,
        "provenance": provenance,
        "joint_training": {
            "training_seconds": checkpoint.elapsed_seconds,
            "training_loss_mean": checkpoint.training_loss,
            "learned_parameter": float(torch.exp(parameter_center)[0].item()),
        },
        "common_center": center,
        "center_stationarity": None,
        "gamma": None,
        "solver_hierarchy": None,
        "exact_local_gold_standard": None,
        "local_GN_validation": None,
        "finite_radius_validation": None,
        "readiness_gate": "FAIL",
        "confirmation_authorized": False,
    }
    center_pass = theta_center is not None
    if center_pass:
        linearization = ResidualLinearization(
            residual_function, theta_center, parameter_center
        )
        residual = linearization.residual()
        jacobian_theta, jacobian_parameter = linearization.explicit_jacobians()
        jacobian_parameter_mf = linearization.parameter_columns_matrix_free()
        center_gradient = float(center["final"]["normalized_objective_gradient"])
        s_theta = _stationarity(jacobian_theta, residual)
        s_lambda = _stationarity(jacobian_parameter, residual)
        center_pass = (
            center_gradient
            < float(specification["center"]["required_objective_gradient_tolerance"])
            and s_theta
            < float(specification["center"]["residual_stationarity_tolerance"])
            and center["final"]["hessian_pass"]
        )
        result["center_stationarity"] = {
            "G_theta": center_gradient,
            "S_theta": s_theta,
            "S_lambda": s_lambda,
            "status": "PASS" if center_pass else "NUMERICAL_FAILURE",
        }

    if center_pass:
        gamma = float(specification["gamma"]["alpha"]) * float(
            torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item()
        )
        result["gamma"] = gamma
        explicit = _direct_augmented_reference(
            jacobian_theta,
            jacobian_parameter,
            residual,
            gamma,
            {
                **specification["solvers"],
                "explicit_relative_normal_residual": specification["solvers"][
                    "explicit_parameter_relative_normal_residual"
                ],
            },
        )
        matrix_free = _matrix_free_normal_solvers(
            linearization,
            jacobian_parameter_mf,
            residual,
            gamma,
            {
                **specification["solvers"],
                "acceptance_relative_residual": specification["solvers"][
                    "parameter_residual_acceptance"
                ],
            },
        )
        lsqr = _augmented_lsqr_reference(
            linearization,
            jacobian_parameter_mf,
            residual,
            gamma,
            {
                **specification["solvers"],
                "lsqr_curvature_relative_tolerance": specification["solvers"][
                    "curvature_relative_acceptance"
                ],
            },
            float(explicit["Fse"][0][0]),
        )
        hierarchy = _solver_hierarchy(
            explicit, matrix_free, lsqr, specification["solvers"]
        )
        result["solver_hierarchy"] = hierarchy
        exact = full_hessian_references(
            residual_function,
            theta_center,
            parameter_center,
            gamma,
            specification["full_hessian"],
        )
        exact_gamma = exact["gamma_matched"]
        result["exact_local_gold_standard"] = {
            **exact_gamma,
            "role": "EXACT_LOCAL_GOLD_STANDARD",
        }
        explicit_value = float(explicit["Fse"][0][0])
        exact_value = (
            float(exact_gamma["reduced_hessian"][0][0])
            if exact_gamma["reduced_hessian"] is not None
            else None
        )
        local_error = (
            _relative(explicit_value, exact_value) if exact_value is not None else None
        )
        local_pass = (
            exact_gamma["status"] == "PASS"
            and local_error is not None
            and local_error <= float(specification["local_gn_relative_tolerance"])
        )
        result["local_GN_validation"] = {
            "status": "PASS" if local_pass else "FAIL",
            "Fraw": float((jacobian_parameter.T @ jacobian_parameter)[0, 0].item()),
            "Fse_GN_explicit": explicit_value,
            "Hred_exact_gamma": exact_value,
            "relative_error": local_error,
            "tolerance": float(specification["local_gn_relative_tolerance"]),
        }
        profile = run_resolution_profile(
            residual_function,
            theta_center,
            parameter_center,
            gamma,
            specification["local_minimum"],
            specification["profile"],
            specification["branch_audit"],
            int(runtime["network"]["hidden_width"]),
            float(runtime["domain"]["t"][1]),
        )
        exact_rows = []
        for row in profile["resolution_scales"]:
            error = (
                _relative(float(row["strict_curvature"]), exact_value)
                if row["resolution_status"] == "CERTIFIED"
                and row["strict_curvature"] is not None
                and exact_value is not None
                else None
            )
            exact_rows.append(
                {
                    "h": row["h"],
                    "resolution_status": row["resolution_status"],
                    "relative_error_to_exact": error,
                    "pass": error
                    <= float(
                        specification["profile"]["exact_agreement_relative_tolerance"]
                    )
                    if error is not None
                    else None,
                }
            )
        certified_exact = [row for row in exact_rows if row["pass"] is not None]
        finite_pass = (
            profile["status"] == "PASS"
            and len(certified_exact)
            >= int(specification["profile"]["certified_adjacent_scales_required"])
            and all(row["pass"] for row in certified_exact)
        )
        profile["exact_reference_comparison"] = exact_rows
        profile["status"] = "PASS" if finite_pass else "PROFILE_FAILURE"
        result["finite_radius_validation"] = profile
        readiness = all(
            [
                hierarchy["CURVATURE_SOLVER_GATE"]["status"] == "PASS",
                exact_gamma["status"] == "PASS",
                local_pass,
                finite_pass,
                profile["branch_continuity_audit"]["status"] == "PASS",
            ]
        )
        result["readiness_gate"] = "PASS" if readiness else "FAIL"

    result.update(
        {
            "status": "PASS",
            "engineering_gate": "PASSED",
            "eligible_for_evaluation_seeds_21_24": bool(
                seed == int(specification["protocol_seed"])
                and result["readiness_gate"] == "PASS"
            ),
            "scientific_gate": "NONE_DEVELOPMENT_ONLY",
        }
    )
    result_path = destination / "result.json"
    result_path.write_text(
        json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "records": [
            {
                "path": "result.json",
                "status": result["status"],
                "sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
            }
        ],
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result

