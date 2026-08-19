"""Four-node numerical decomposition for v3.3 seed-20 development."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.p4_screening import _stationarity
from saeps.p5_confirmation import _runtime_config
from saeps.provenance import environment_provenance, make_run_id
from saeps.scalar import scalar_residual, solve_truth, train_scalar_checkpoint
from saeps.solvers import (
    conjugate_gradient,
    least_squares_qr,
    preconditioned_conjugate_gradient,
)
from saeps.v3.foundation import full_hessian_references
from saeps.v31.local_minimum import optimize_state_local_minimum
from saeps.v31.pipeline import V2_SCALAR_SHA256, _mean_residual_objective
from saeps.v32.pipeline import run_accuracy_profile


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def _relative(left: float, right: float, floor: float = 1.0e-8) -> float:
    return abs(left - right) / max(abs(right), floor)


def _direct_augmented_reference(
    jacobian_theta: torch.Tensor,
    jacobian_parameter: torch.Tensor,
    residual: torch.Tensor,
    gamma: float,
    specification: dict[str, Any],
) -> dict[str, Any]:
    state_size = jacobian_theta.shape[1]
    parameter_size = jacobian_parameter.shape[1]
    square_root_gamma = math.sqrt(gamma)
    augmented = torch.cat(
        [
            jacobian_theta,
            square_root_gamma
            * torch.eye(
                state_size,
                dtype=jacobian_theta.dtype,
                device=jacobian_theta.device,
            ),
        ],
        dim=0,
    )
    right_hand_sides = torch.cat(
        [jacobian_parameter, residual.reshape(-1, 1)], dim=1
    )
    augmented_rhs = torch.cat(
        [
            right_hand_sides,
            torch.zeros(
                state_size,
                right_hand_sides.shape[1],
                dtype=right_hand_sides.dtype,
                device=right_hand_sides.device,
            ),
        ],
        dim=0,
    )
    solution = torch.linalg.lstsq(augmented, augmented_rhs, driver="gelsd").solution
    augmented_residual = augmented @ solution - augmented_rhs
    normal_residual = augmented.T @ augmented_residual
    normal_rhs = augmented.T @ augmented_rhs
    relative_normal = torch.linalg.vector_norm(normal_residual, dim=0) / torch.clamp(
        torch.linalg.vector_norm(normal_rhs, dim=0), min=1.0e-30
    )
    parameter_augmented_residual = augmented_residual[:, :parameter_size]
    objective_curvature = parameter_augmented_residual.T @ parameter_augmented_residual
    state_solution = solution[:, :parameter_size]
    projection_curvature = jacobian_parameter.T @ (
        jacobian_parameter - jacobian_theta @ state_solution
    )
    identity_error = float(
        torch.linalg.matrix_norm(objective_curvature - projection_curvature).item()
    ) / max(float(torch.linalg.matrix_norm(objective_curvature).item()), 1.0e-30)
    singular_values = torch.linalg.svdvals(augmented)
    max_normal = float(torch.max(relative_normal).item())
    passed = (
        max_normal <= float(specification["explicit_relative_normal_residual"])
        and identity_error <= float(specification["explicit_objective_identity_tolerance"])
    )
    return {
        "node": "Fse_GN_explicit_direct",
        "status": "PASS" if passed else "NUMERICAL_FAILURE",
        "method": "explicit augmented SVD least-squares (torch gelsd)",
        "Fse": objective_curvature.tolist(),
        "projection_identity_Fse": projection_curvature.tolist(),
        "maximum_relative_normal_residual": max_normal,
        "objective_projection_identity_relative_error": identity_error,
        "augmented_singular_value_minimum": float(singular_values.min().item()),
        "augmented_singular_value_maximum": float(singular_values.max().item()),
        "augmented_condition_number": float(
            (singular_values.max() / singular_values.min()).item()
        ),
        "right_hand_side_relative_normal_residuals": relative_normal.tolist(),
    }


def _matrix_free_normal_solvers(
    linearization: ResidualLinearization,
    jacobian_parameter_matrix_free: torch.Tensor,
    residual: torch.Tensor,
    gamma: float,
    specification: dict[str, Any],
) -> dict[str, Any]:
    parameter_size = jacobian_parameter_matrix_free.shape[1]
    right_hand_sides = [
        jacobian_parameter_matrix_free[:, index] for index in range(parameter_size)
    ] + [residual]
    normal_diagonal = torch.zeros_like(linearization.theta)
    basis = torch.eye(
        linearization.theta.numel(),
        dtype=linearization.theta.dtype,
        device=linearization.theta.device,
    )
    for column in basis:
        normal_diagonal = normal_diagonal + linearization.jvp_theta(column).square().sum() * column
    normal_diagonal = normal_diagonal + gamma

    def operator(vector: torch.Tensor) -> torch.Tensor:
        return linearization.vjp_theta(linearization.jvp_theta(vector)) + gamma * vector

    normal_rhs = [linearization.vjp_theta(value) for value in right_hand_sides]
    tolerance = float(specification["normal_equation_tolerance"])
    maximum = int(specification["max_iterations"])
    acceptance = float(specification["acceptance_relative_residual"])
    cg_solves = [
        conjugate_gradient(operator, value, tolerance, maximum) for value in normal_rhs
    ]
    pcg_solves = [
        preconditioned_conjugate_gradient(
            operator,
            value,
            lambda vector: vector / normal_diagonal,
            tolerance,
            maximum,
        )
        for value in normal_rhs
    ]

    def record(name: str, solves: list[Any]) -> dict[str, Any]:
        states = torch.stack(
            [solves[index].solution for index in range(parameter_size)], dim=1
        )
        eliminated = jacobian_parameter_matrix_free - torch.stack(
            [
                linearization.jvp_theta(states[:, index])
                for index in range(parameter_size)
            ],
            dim=1,
        )
        curvature = jacobian_parameter_matrix_free.T @ eliminated
        passed = all(
            solve.converged and solve.relative_residual <= acceptance for solve in solves
        )
        return {
            "node": name,
            "status": "PASS" if passed else "SOLVER_FAILURE",
            "Fse": curvature.tolist(),
            "iterations": [solve.iterations for solve in solves],
            "converged": [solve.converged for solve in solves],
            "verified_relative_residuals": [
                solve.relative_residual for solve in solves
            ],
            "right_hand_side_order": [
                *[f"Jlambda_column_{index}" for index in range(parameter_size)],
                "residual",
            ],
        }

    return {
        "standard_cg": record("Fse_GN_matrix_free_CG", cg_solves),
        "jacobi_pcg": record("Fse_GN_matrix_free_Jacobi_PCG", pcg_solves),
    }


def _augmented_lsqr_reference(
    linearization: ResidualLinearization,
    jacobian_parameter_matrix_free: torch.Tensor,
    residual: torch.Tensor,
    gamma: float,
    specification: dict[str, Any],
    explicit_value: float,
) -> dict[str, Any]:
    state_size = linearization.theta.numel()
    residual_size = residual.numel()
    parameter_size = jacobian_parameter_matrix_free.shape[1]
    square_root_gamma = math.sqrt(gamma)

    def forward(vector: torch.Tensor) -> torch.Tensor:
        return torch.cat(
            [linearization.jvp_theta(vector), square_root_gamma * vector]
        )

    def adjoint(vector: torch.Tensor) -> torch.Tensor:
        return (
            linearization.vjp_theta(vector[:residual_size])
            + square_root_gamma * vector[residual_size:]
        )

    right_hand_sides = [
        jacobian_parameter_matrix_free[:, index] for index in range(parameter_size)
    ] + [residual]
    augmented_right_hand_sides = [
        torch.cat([value, torch.zeros_like(linearization.theta)])
        for value in right_hand_sides
    ]
    solves = [
        least_squares_qr(
            forward,
            adjoint,
            value,
            state_size,
            float(specification["lsqr_relative_normal_residual"]),
            int(specification["max_iterations"]),
        )
        for value in augmented_right_hand_sides
    ]
    augmented_residuals = torch.stack(
        [
            forward(solves[index].solution) - augmented_right_hand_sides[index]
            for index in range(parameter_size)
        ],
        dim=1,
    )
    curvature = augmented_residuals.T @ augmented_residuals
    curvature_value = float(curvature[0, 0].item())
    curvature_error = _relative(curvature_value, explicit_value)
    residual_pass = all(
        solve.converged
        and solve.relative_normal_residual
        <= float(specification["lsqr_relative_normal_residual"])
        for solve in solves
    )
    passed = residual_pass and curvature_error <= float(
        specification["lsqr_curvature_relative_tolerance"]
    )
    return {
        "node": "Fse_GN_augmented_LSQR",
        "status": "PASS" if passed else "SOLVER_FAILURE",
        "method": "matrix-free Golub-Kahan LSQR on [Jtheta; sqrt(gamma) I]",
        "Fse": curvature.tolist(),
        "iterations": [solve.iterations for solve in solves],
        "converged": [solve.converged for solve in solves],
        "objective_residual_norms": [
            solve.objective_residual_norm for solve in solves
        ],
        "relative_normal_residuals": [
            solve.relative_normal_residual for solve in solves
        ],
        "relative_error_to_explicit_direct": curvature_error,
        "right_hand_side_order": [
            *[f"Jlambda_column_{index}" for index in range(parameter_size)],
            "residual",
        ],
    }


def _diagnostic_decomposition(
    explicit: dict[str, Any],
    matrix_free: dict[str, Any],
    lsqr: dict[str, Any],
    exact: dict[str, Any],
    profile: dict[str, Any],
    raw: float,
) -> dict[str, Any]:
    explicit_value = float(explicit["Fse"][0][0])
    cg_value = float(matrix_free["standard_cg"]["Fse"][0][0])
    pcg_value = float(matrix_free["jacobi_pcg"]["Fse"][0][0])
    lsqr_value = float(lsqr["Fse"][0][0])
    exact_value = (
        float(exact["gamma_matched"]["reduced_hessian"][0][0])
        if exact["gamma_matched"]["reduced_hessian"] is not None
        else None
    )
    profile_value = profile["accuracy_levels"]["strict"]["finest_curvature"]
    nodes = {
        "Fraw": raw,
        "Fse_GN_matrix_free_CG": cg_value,
        "Fse_GN_matrix_free_Jacobi_PCG": pcg_value,
        "Fse_GN_augmented_LSQR": lsqr_value,
        "Fse_GN_explicit_direct": explicit_value,
        "Hred_exact_gamma": exact_value,
        "Hprofile_gamma": profile_value,
    }
    segments: dict[str, Any] = {
        "solver_error_CG_to_explicit": _relative(cg_value, explicit_value),
        "solver_error_Jacobi_PCG_to_explicit": _relative(pcg_value, explicit_value),
        "solver_error_augmented_LSQR_to_explicit": _relative(
            lsqr_value, explicit_value
        ),
    }
    if exact_value is not None:
        segments["GN_approximation_error_explicit_to_exact"] = _relative(
            explicit_value, exact_value
        )
    else:
        segments["GN_approximation_error_explicit_to_exact"] = None
    if exact_value is not None and profile_value is not None:
        segments["nonlinear_profile_error_exact_to_profile"] = _relative(
            exact_value, float(profile_value)
        )
    else:
        segments["nonlinear_profile_error_exact_to_profile"] = None
    segments["total_GN_to_profile_discrepancy"] = (
        _relative(explicit_value, float(profile_value))
        if profile_value is not None
        else None
    )
    return {
        "reporting_scope": "NONBINDING_DIAGNOSTIC_ONLY",
        "paper_facing": False,
        "nodes": nodes,
        "segment_relative_errors": segments,
        "status_by_node": {
            "Fse_GN_matrix_free_CG": matrix_free["standard_cg"]["status"],
            "Fse_GN_matrix_free_Jacobi_PCG": matrix_free["jacobi_pcg"]["status"],
            "Fse_GN_augmented_LSQR": lsqr["status"],
            "Fse_GN_explicit_direct": explicit["status"],
            "Hred_exact_gamma": exact["gamma_matched"]["status"],
            "Hprofile_gamma": profile["status"],
        },
    }


def run_seed20_numerical_decomposition(
    config_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root)
    specification = load_config(config_path)
    if specification["confirmation_authorized"] is not False:
        raise ValueError("v3.3 confirmation must remain unauthorized")
    if int(specification["active_seed"]) != 20:
        raise ValueError("only seed 20 is authorized")
    if specification["diagnostic_reporting_scope"] != "NONBINDING_DIAGNOSTIC_ONLY":
        raise ValueError("v3.3 decomposition must remain nonbinding")
    locked_path = root / specification["source_scalar_config"]
    if hashlib.sha256(locked_path.read_bytes()).hexdigest() != V2_SCALAR_SHA256:
        raise RuntimeError("v2 scalar lock changed")
    locked = load_config(locked_path)
    runtime = _runtime_config(locked)
    provenance = environment_provenance(root, locked["dtype"], locked["device"])
    digest = config_hash(specification)
    run_id = make_run_id("V3-3-num-decomp", 20, digest, provenance["timestamp"])
    destination = Path(output_root) / run_id
    destination.mkdir(parents=True, exist_ok=False)

    truth = solve_truth(runtime, "Burgers")
    checkpoint, points = train_scalar_checkpoint(runtime, "Burgers", 20, truth)
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
        "seed": 20,
        "split": specification["split"],
        "config_hash": digest,
        "v2_scalar_lock_sha256": V2_SCALAR_SHA256,
        "provenance": provenance,
        "joint_training": {
            "training_seconds": checkpoint.elapsed_seconds,
            "training_loss_mean": checkpoint.training_loss,
            "learned_log_parameter": float(parameter_center[0].item()),
            "learned_parameter": float(torch.exp(parameter_center)[0].item()),
        },
        "common_center": center,
        "center_stationarity": None,
        "gamma": None,
        "gamma_matched_profile": None,
        "explicit_direct_reference": None,
        "matrix_free_normal_equations": None,
        "augmented_lsqr_reference": None,
        "full_hessian": None,
        "development_decomposition": None,
        "paper_facing_comparison": None,
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
        s_theta = _stationarity(jacobian_theta, residual)
        s_lambda = _stationarity(jacobian_parameter, residual)
        center_gradient = float(center["final"]["normalized_objective_gradient"])
        jacobian_parameter_error = float(
            torch.linalg.matrix_norm(jacobian_parameter - jacobian_parameter_mf).item()
        ) / max(float(torch.linalg.matrix_norm(jacobian_parameter).item()), 1.0e-30)
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
            "Jlambda_explicit_matrix_free_relative_error": jacobian_parameter_error,
            "status": "PASS" if center_pass else "NUMERICAL_FAILURE",
        }

    all_registered_pass = False
    if center_pass:
        gamma = float(specification["gamma"]["alpha"]) * float(
            torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item()
        )
        result["gamma"] = gamma
        profile = run_accuracy_profile(
            residual_function,
            theta_center,
            parameter_center,
            gamma,
            specification["local_minimum"],
            specification["profile"],
            matched=True,
        )
        result["gamma_matched_profile"] = profile
        explicit = _direct_augmented_reference(
            jacobian_theta,
            jacobian_parameter,
            residual,
            gamma,
            specification["solvers"],
        )
        result["explicit_direct_reference"] = explicit
        matrix_free = _matrix_free_normal_solvers(
            linearization,
            jacobian_parameter_mf,
            residual,
            gamma,
            specification["solvers"],
        )
        result["matrix_free_normal_equations"] = matrix_free
        explicit_value = float(explicit["Fse"][0][0])
        lsqr = _augmented_lsqr_reference(
            linearization,
            jacobian_parameter_mf,
            residual,
            gamma,
            specification["solvers"],
            explicit_value,
        )
        result["augmented_lsqr_reference"] = lsqr
        exact = full_hessian_references(
            residual_function,
            theta_center,
            parameter_center,
            gamma,
            specification["full_hessian"],
        )
        result["full_hessian"] = exact
        raw = float((jacobian_parameter.T @ jacobian_parameter)[0, 0].item())
        decomposition = _diagnostic_decomposition(
            explicit, matrix_free, lsqr, exact, profile, raw
        )
        result["development_decomposition"] = decomposition
        all_registered_pass = all(
            status == "PASS"
            for status in [
                profile["status"],
                explicit["status"],
                matrix_free["standard_cg"]["status"],
                matrix_free["jacobi_pcg"]["status"],
                lsqr["status"],
                exact["gamma_matched"]["status"],
            ]
        )
        if all_registered_pass:
            result["paper_facing_comparison"] = {
                **decomposition["nodes"],
                "segment_relative_errors": decomposition["segment_relative_errors"],
            }

    result.update(
        {
            "status": "PASS",
            "engineering_gate": "PASSED",
            "registered_chain_gate": "PASS"
            if center_pass and all_registered_pass
            else "FAIL",
            "diagnostic_reporting_scope": "NONBINDING_DIAGNOSTIC_ONLY",
            "eligible_to_request_activation_of_seeds_21_24": False,
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

