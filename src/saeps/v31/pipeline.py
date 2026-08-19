"""Strict serial seed-20 v3.1 development pipeline."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.core import compute_matrix_free_saeps, explicit_tikhonov_operator
from saeps.p4_screening import _stationarity
from saeps.p5_confirmation import _runtime_config
from saeps.provenance import environment_provenance, make_run_id
from saeps.scalar import scalar_residual, solve_truth, train_scalar_checkpoint
from saeps.solvers import preconditioned_conjugate_gradient
from saeps.v3.foundation import full_hessian_references
from saeps.v31.local_minimum import optimize_state_local_minimum


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]
V2_SCALAR_SHA256 = "cb5c2e9e3eee2d5462dd92ac0b9cd3b2b607ea487367d9c83b18a3a8af9c5cf8"


def _mean_residual_objective(
    residual_function: ResidualFunction,
    parameter: torch.Tensor,
    theta_reference: torch.Tensor,
    gamma: float,
    matched: bool,
) -> Callable[[torch.Tensor], torch.Tensor]:
    residual_count = int(residual_function(theta_reference, parameter).numel())

    def objective(theta: torch.Tensor) -> torch.Tensor:
        residual = residual_function(theta, parameter)
        value = 0.5 * torch.mean(residual.square())
        if matched:
            value = value + gamma / (2.0 * residual_count) * torch.sum(
                (theta - theta_reference).square()
            )
        return value

    return objective


def _run_profile(
    residual_function: ResidualFunction,
    theta_base: torch.Tensor,
    parameter_base: torch.Tensor,
    gamma: float,
    local_specification: dict[str, Any],
    profile_specification: dict[str, Any],
    *,
    matched: bool,
) -> dict[str, Any]:
    residual_count = int(residual_function(theta_base, parameter_base).numel())
    center_objective = _mean_residual_objective(
        residual_function, parameter_base, theta_base, gamma, matched
    )
    center_loss = float(center_objective(theta_base).item())
    h_values = [float(value) for value in profile_specification["h_values"]]
    points: list[dict[str, Any]] = []
    estimates: list[dict[str, Any]] = []
    for h in h_values:
        pair: dict[float, dict[str, Any]] = {}
        for offset in (-h, h):
            parameter = parameter_base + offset * torch.ones_like(parameter_base)
            objective = _mean_residual_objective(
                residual_function, parameter, theta_base, gamma, matched
            )
            optimized, optimization = optimize_state_local_minimum(
                objective, theta_base, local_specification
            )
            record = {
                "offset": offset,
                "parameter_coordinate": parameter.tolist(),
                "status": optimization["status"],
                "failure_reason": optimization["failure_reason"],
                "optimization": optimization,
                "loss_mean": float(objective(optimized).item())
                if optimized is not None
                else None,
            }
            points.append(record)
            pair[offset] = record
        valid = all(pair[offset]["status"] == "PASS" for offset in (-h, h))
        curvature = (
            residual_count
            * (
                float(pair[h]["loss_mean"])
                - 2.0 * center_loss
                + float(pair[-h]["loss_mean"])
            )
            / (h * h)
            if valid
            else None
        )
        estimates.append(
            {
                "h": h,
                "curvature": curvature,
                "pair_status": "PASS" if valid else "NUMERICAL_FAILURE",
            }
        )

    convergence = []
    convergence_specification = profile_specification["convergence"]
    floor = float(convergence_specification["denominator_absolute_floor"])
    tolerance = float(convergence_specification["relative_tolerance"])
    for coarse, fine in zip(estimates, estimates[1:]):
        if coarse["curvature"] is None or fine["curvature"] is None:
            relative_change = None
            passed = False
        else:
            relative_change = abs(float(fine["curvature"]) - float(coarse["curvature"])) / max(
                abs(float(fine["curvature"])), floor
            )
            passed = math.isfinite(relative_change) and relative_change <= tolerance
        convergence.append(
            {
                "coarse_h": coarse["h"],
                "fine_h": fine["h"],
                "relative_change": relative_change,
                "pass": passed,
            }
        )
    required = int(convergence_specification["adjacent_pairs_required"])
    all_points_pass = len(points) == 8 and all(point["status"] == "PASS" for point in points)
    convergence_pass = len(convergence[-required:]) == required and all(
        item["pass"] for item in convergence[-required:]
    )
    status = "PASS" if all_points_pass and convergence_pass else "PROFILE_FAILURE"
    return {
        "objective": "gamma_matched" if matched else "unregularized",
        "objective_scaling": (
            "0.5*mean(r^2) + gamma/(2*m)*||theta-theta_base||^2"
            if matched
            else "0.5*mean(r^2)"
        ),
        "gamma": gamma if matched else 0.0,
        "center_loss_mean": center_loss,
        "points": points,
        "passed_points": sum(point["status"] == "PASS" for point in points),
        "curvature_estimates_unnormalized": estimates,
        "adjacent_convergence": convergence,
        "finest_curvature": estimates[-1]["curvature"],
        "status": status,
        "failure_reason": None
        if status == "PASS"
        else "8/8 local-minimum points or two-finest curvature convergence failed",
    }


def _krylov_gate(
    linearization: ResidualLinearization,
    gamma: float,
    specification: dict[str, Any],
) -> dict[str, Any]:
    jacobian_theta, jacobian_parameter = linearization.explicit_jacobians()
    residual = linearization.residual()
    normal_diagonal = torch.sum(jacobian_theta.square(), dim=0) + gamma
    if torch.any(normal_diagonal <= 0.0):
        raise ValueError("Jacobi preconditioner has a nonpositive diagonal")

    standard: dict[str, Any]
    try:
        result = compute_matrix_free_saeps(
            linearization,
            gamma,
            float(specification["cg_tolerance"]),
            int(specification["cg_max_iterations"]),
        )
        standard = {
            "status": "PASS",
            "iterations": [solve.iterations for solve in result.solves],
            "verified_relative_residuals": [solve.relative_residual for solve in result.solves],
            "Fse": result.eliminated_curvature.tolist(),
        }
    except Exception as error:
        standard = {
            "status": "SOLVER_FAILURE",
            "failure_reason": f"{type(error).__name__}: {error}",
        }

    def operator(vector: torch.Tensor) -> torch.Tensor:
        return linearization.vjp_theta(linearization.jvp_theta(vector)) + gamma * vector

    right_hand_sides = [
        linearization.vjp_theta(jacobian_parameter[:, index])
        for index in range(jacobian_parameter.shape[1])
    ] + [linearization.vjp_theta(residual)]
    solves = [
        preconditioned_conjugate_gradient(
            operator,
            right_hand_side,
            lambda vector: vector / normal_diagonal,
            float(specification["cg_tolerance"]),
            int(specification["cg_max_iterations"]),
        )
        for right_hand_side in right_hand_sides
    ]
    acceptance = float(specification["cg_acceptance"])
    pcg_pass = all(
        solve.converged and solve.relative_residual <= acceptance for solve in solves
    )
    eliminated_columns = torch.stack(
        [
            jacobian_parameter[:, index]
            - linearization.jvp_theta(solves[index].solution)
            for index in range(jacobian_parameter.shape[1])
        ],
        dim=1,
    )
    pcg_curvature = jacobian_parameter.T @ eliminated_columns
    pcg = {
        "status": "PASS" if pcg_pass else "SOLVER_FAILURE",
        "preconditioner": "exact_development_Jacobi_diag(Jtheta^T Jtheta + gamma I)",
        "iterations": [solve.iterations for solve in solves],
        "verified_relative_residuals": [solve.relative_residual for solve in solves],
        "Fse": pcg_curvature.tolist(),
    }
    overall = standard.get("status") == "PASS" and pcg_pass
    return {
        "status": "PASS" if overall else "SOLVER_FAILURE",
        "standard_cg": standard,
        "jacobi_pcg": pcg,
        "solver_failure_count": int(standard.get("status") != "PASS")
        + sum(not solve.converged or solve.relative_residual > acceptance for solve in solves),
    }


def _comparison(
    jacobian_theta: torch.Tensor,
    jacobian_parameter: torch.Tensor,
    gamma: float,
    exact: dict[str, Any],
    matched_profile: dict[str, Any],
) -> dict[str, Any]:
    raw = float((jacobian_parameter.T @ jacobian_parameter)[0, 0].item())
    gn = float(
        (jacobian_parameter.T @ explicit_tikhonov_operator(jacobian_theta, gamma) @ jacobian_parameter)[0, 0].item()
    )
    exact_value = float(exact["gamma_matched"]["reduced_hessian"][0][0])
    profile = float(matched_profile["finest_curvature"])

    def relative(left: float, right: float) -> float:
        return abs(left - right) / max(abs(right), 1.0e-8)

    return {
        "Fraw": raw,
        "Fse_GN": gn,
        "Hred_exact_gamma": exact_value,
        "Hprofile_gamma": profile,
        "relative_error_GN_to_exact": relative(gn, exact_value),
        "relative_error_GN_to_profile": relative(gn, profile),
        "relative_error_exact_to_profile": relative(exact_value, profile),
        "relative_error_raw_to_profile": relative(raw, profile),
        "binding_scientific_threshold": None,
    }


def run_seed20_development(
    config_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root)
    specification = load_config(config_path)
    if specification["confirmation_authorized"] is not False:
        raise ValueError("v3.1 confirmation must remain unauthorized")
    if int(specification["active_seed"]) != 20:
        raise ValueError("only seed 20 is authorized")
    if set(specification["inactive_development_seeds"]) != {21, 22, 23, 24}:
        raise ValueError("development seed isolation changed")
    locked_path = root / specification["source_scalar_config"]
    if hashlib.sha256(locked_path.read_bytes()).hexdigest() != V2_SCALAR_SHA256:
        raise RuntimeError("v2 scalar lock changed")
    locked = load_config(locked_path)
    runtime = _runtime_config(locked)
    provenance = environment_provenance(root, locked["dtype"], locked["device"])
    digest = config_hash(specification)
    run_id = make_run_id("V3-1-state-min", 20, digest, provenance["timestamp"])
    destination = Path(output_root) / run_id
    destination.mkdir(parents=True, exist_ok=False)

    truth = solve_truth(runtime, "Burgers")
    checkpoint, points = train_scalar_checkpoint(runtime, "Burgers", 20, truth)
    residual_function: ResidualFunction = lambda theta, parameter: scalar_residual(
        theta, parameter, "Burgers", points, truth, runtime
    )
    parameter_base = checkpoint.log_parameter.detach().clone()
    center_objective = _mean_residual_objective(
        residual_function, parameter_base, checkpoint.theta, 0.0, False
    )
    theta_base, center = optimize_state_local_minimum(
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
            "learned_log_parameter": float(parameter_base[0].item()),
            "learned_parameter": float(torch.exp(parameter_base)[0].item()),
        },
        "center_local_minimum": center,
        "center_residual_stationarity": None,
        "unregularized_profile": None,
        "gamma_matched_profile": None,
        "krylov_gate": None,
        "full_hessian": None,
        "curvature_comparison": None,
        "serial_stop_stage": None,
        "confirmation_authorized": False,
    }

    full_chain = True
    if theta_base is None:
        full_chain = False
        result["serial_stop_stage"] = "CENTER_LOCAL_MINIMUM"
    else:
        linearization = ResidualLinearization(residual_function, theta_base, parameter_base)
        residual = linearization.residual()
        jacobian_theta, jacobian_parameter = linearization.explicit_jacobians()
        center_stationarity = _stationarity(jacobian_theta, residual)
        stationarity_pass = center_stationarity <= float(
            specification["local_minimum"]["center_residual_stationarity_tolerance"]
        )
        result["center_residual_stationarity"] = {
            "S_theta": center_stationarity,
            "tolerance": float(
                specification["local_minimum"]["center_residual_stationarity_tolerance"]
            ),
            "status": "PASS" if stationarity_pass else "NUMERICAL_FAILURE",
        }
        if not stationarity_pass:
            full_chain = False
            result["serial_stop_stage"] = "CENTER_RESIDUAL_STATIONARITY"

    if full_chain:
        gamma = float(specification["gamma"]["alpha"]) * float(
            torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item()
        )
        result["gamma"] = gamma
        unregularized = _run_profile(
            residual_function,
            theta_base,
            parameter_base,
            gamma,
            specification["local_minimum"],
            specification["profile"],
            matched=False,
        )
        result["unregularized_profile"] = unregularized
        if unregularized["status"] != "PASS":
            full_chain = False
            result["serial_stop_stage"] = "UNREGULARIZED_PROFILE"

    if full_chain:
        matched = _run_profile(
            residual_function,
            theta_base,
            parameter_base,
            gamma,
            specification["local_minimum"],
            specification["profile"],
            matched=True,
        )
        result["gamma_matched_profile"] = matched
        if matched["status"] != "PASS":
            full_chain = False
            result["serial_stop_stage"] = "GAMMA_MATCHED_PROFILE"

    if full_chain:
        krylov = _krylov_gate(linearization, gamma, specification["gamma"])
        result["krylov_gate"] = krylov
        if krylov["status"] != "PASS" or krylov["solver_failure_count"] != 0:
            full_chain = False
            result["serial_stop_stage"] = "KRYLOV_GATE"

    if full_chain:
        exact = full_hessian_references(
            residual_function,
            theta_base,
            parameter_base,
            gamma,
            specification["full_hessian"],
        )
        result["full_hessian"] = exact
        if exact["status"] != "PASS":
            full_chain = False
            result["serial_stop_stage"] = "EXACT_REDUCED_HESSIAN"

    if full_chain:
        result["curvature_comparison"] = _comparison(
            jacobian_theta,
            jacobian_parameter,
            gamma,
            exact,
            matched,
        )

    result.update(
        {
            "status": "PASS",
            "engineering_gate": "PASSED",
            "full_chain_gate": "PASS" if full_chain else "FAIL",
            "eligible_to_request_activation_of_seeds_21_24": full_chain,
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
