"""v3 foundation: common base, matched profiles, exact Hessian, and h convergence."""

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
from saeps.profile import ProfilePoint, _reoptimize_point
from saeps.provenance import environment_provenance, make_run_id
from saeps.scalar import scalar_residual, solve_truth, train_scalar_checkpoint


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def _mean_loss(
    residual_function: ResidualFunction,
    theta: torch.Tensor,
    parameter: torch.Tensor,
) -> torch.Tensor:
    residual = residual_function(theta, parameter)
    return 0.5 * torch.mean(residual.square())


def _normalized_state_gradient(
    residual_function: ResidualFunction,
    theta: torch.Tensor,
    parameter: torch.Tensor,
) -> float:
    current = theta.detach().clone().requires_grad_(True)
    loss = _mean_loss(residual_function, current, parameter)
    gradient = torch.autograd.grad(loss, current)[0]
    scale = max(float(torch.linalg.vector_norm(current).item()), 1.0)
    return float(torch.linalg.vector_norm(gradient).item()) / scale


def _point_record(point: ProfilePoint) -> dict[str, Any]:
    return {
        "offset": point.offset,
        "loss": point.loss,
        "status": point.status,
        "failure_reason": point.failure_reason,
        "outer_steps": point.outer_steps,
        "closure_calls": point.closure_calls,
        "normalized_gradient": point.normalized_gradient,
        "relative_loss_change": point.relative_loss_change,
        "optimizer_terminated": point.optimizer_terminated,
        "plateau_pass": point.loss_plateau,
        "gradient_pass": point.gradient_converged,
    }


def refine_common_base(
    residual_function: ResidualFunction,
    theta0: torch.Tensor,
    parameter0: torch.Tensor,
    specification: dict[str, Any],
) -> tuple[torch.Tensor | None, dict[str, Any]]:
    initial_loss = float(_mean_loss(residual_function, theta0, parameter0).item())
    initial_gradient = _normalized_state_gradient(
        residual_function, theta0, parameter0
    )
    point = _reoptimize_point(
        lambda state, coordinate: _mean_loss(
            residual_function, state, coordinate
        ),
        theta0,
        parameter0,
        0.0,
        specification["optimizer"],
        specification["stopping"],
    )
    record = _point_record(point)
    record.update(
        {
            "initial_loss_mean": initial_loss,
            "initial_normalized_state_gradient": initial_gradient,
            "delta_theta_relative": None,
            "delta_loss_relative": None,
            "refined_normalized_state_gradient": None,
        }
    )
    if point.status != "PASS" or point.theta is None or point.loss is None:
        return None, record
    refined = point.theta.detach().clone()
    denominator = max(
        float(torch.linalg.vector_norm(theta0).item()), 1.0e-30
    )
    record.update(
        {
            "delta_theta_relative": float(
                torch.linalg.vector_norm(refined - theta0).item()
            )
            / denominator,
            "delta_loss_relative": (initial_loss - float(point.loss))
            / max(abs(initial_loss), 1.0e-30),
            "refined_normalized_state_gradient": _normalized_state_gradient(
                residual_function, refined, parameter0
            ),
        }
    )
    return refined, record


def _profile_objective(
    residual_function: ResidualFunction,
    theta_base: torch.Tensor,
    gamma: float,
    residual_count: int,
    matched: bool,
) -> Callable[[torch.Tensor, torch.Tensor], torch.Tensor]:
    def objective(theta: torch.Tensor, parameter: torch.Tensor) -> torch.Tensor:
        value = _mean_loss(residual_function, theta, parameter)
        if matched:
            value = value + (gamma / (2.0 * residual_count)) * torch.sum(
                (theta - theta_base).square()
            )
        return value

    return objective


def run_multiscale_profile(
    residual_function: ResidualFunction,
    theta_base: torch.Tensor,
    parameter_base: torch.Tensor,
    gamma: float,
    specification: dict[str, Any],
    *,
    matched: bool,
) -> dict[str, Any]:
    residual_count = int(residual_function(theta_base, parameter_base).numel())
    objective = _profile_objective(
        residual_function, theta_base, gamma, residual_count, matched
    )
    center_loss = float(objective(theta_base, parameter_base).item())
    h_values = [float(value) for value in specification["h_values"]]
    if h_values != sorted(h_values, reverse=True) or any(value <= 0 for value in h_values):
        raise ValueError("h_values must be positive and strictly coarse-to-fine")

    point_records: list[dict[str, Any]] = []
    estimates: list[dict[str, Any]] = []
    for h in h_values:
        pair: dict[float, ProfilePoint] = {}
        for offset in (-h, h):
            point = _reoptimize_point(
                objective,
                theta_base,
                parameter_base + offset * torch.ones_like(parameter_base),
                offset,
                specification["optimizer"],
                specification["stopping"],
            )
            pair[offset] = point
            point_records.append(_point_record(point))
        valid_pair = all(
            point.status == "PASS" and point.loss is not None
            for point in pair.values()
        )
        curvature = (
            residual_count
            * (
                float(pair[h].loss)
                - 2.0 * center_loss
                + float(pair[-h].loss)
            )
            / (h * h)
            if valid_pair
            else None
        )
        estimates.append(
            {
                "h": h,
                "curvature": curvature,
                "pair_status": "PASS" if valid_pair else "PROFILE_FAILURE",
            }
        )

    convergence = []
    convergence_specification = specification["convergence"]
    floor = float(convergence_specification["denominator_absolute_floor"])
    tolerance = float(convergence_specification["relative_tolerance"])
    for coarse, fine in zip(estimates, estimates[1:]):
        if coarse["curvature"] is None or fine["curvature"] is None:
            change = None
            passed = False
        else:
            change = abs(float(fine["curvature"]) - float(coarse["curvature"])) / max(
                abs(float(fine["curvature"])), floor
            )
            passed = math.isfinite(change) and change <= tolerance
        convergence.append(
            {
                "coarse_h": coarse["h"],
                "fine_h": fine["h"],
                "relative_change": change,
                "pass": passed,
            }
        )
    required = int(convergence_specification["adjacent_pairs_required"])
    selected = convergence[-required:]
    all_points_final = len(point_records) == 2 * len(h_values) and all(
        point["status"] in {"PASS", "PROFILE_FAILURE"} for point in point_records
    )
    converged = (
        all_points_final
        and all(point["status"] == "PASS" for point in point_records)
        and len(selected) == required
        and all(item["pass"] for item in selected)
    )
    return {
        "objective": "gamma_matched" if matched else "unregularized",
        "objective_scaling": (
            "0.5*mean(r^2) + gamma/(2*m)*||theta-theta_base||^2"
            if matched
            else "0.5*mean(r^2)"
        ),
        "gamma": gamma if matched else 0.0,
        "residual_count": residual_count,
        "center_loss_mean": center_loss,
        "points": point_records,
        "curvature_estimates_unnormalized": estimates,
        "adjacent_convergence": convergence,
        "finest_curvature": estimates[-1]["curvature"],
        "all_points_have_final_status": all_points_final,
        "status": "PASS" if converged else "PROFILE_FAILURE",
        "failure_reason": None
        if converged
        else "planned points or two-finest multiscale convergence gate failed",
    }


def _reduce_hessian(
    state_block: torch.Tensor,
    cross_state_parameter: torch.Tensor,
    cross_parameter_state: torch.Tensor,
    parameter_block: torch.Tensor,
    specification: dict[str, Any],
) -> dict[str, Any]:
    symmetric = 0.5 * (state_block + state_block.T)
    eigenvalues = torch.linalg.eigvalsh(symmetric)
    maximum_scale = max(float(torch.max(torch.abs(eigenvalues)).item()), 1.0)
    positive_tolerance = (
        float(specification["positive_eigenvalue_relative_tolerance"])
        * maximum_scale
    )
    minimum = float(eigenvalues[0].item())
    maximum = float(eigenvalues[-1].item())
    positive = minimum > positive_tolerance
    result: dict[str, Any] = {
        "minimum_state_eigenvalue": minimum,
        "maximum_state_eigenvalue": maximum,
        "positive_eigenvalue_tolerance": positive_tolerance,
        "nonpositive_eigenvalue_count": int(
            torch.count_nonzero(eigenvalues <= positive_tolerance).item()
        ),
        "condition_number": maximum / minimum if positive else None,
        "reduced_hessian": None,
        "solve_relative_residual": None,
    }
    if not positive:
        result.update(
            {
                "status": "NUMERICAL_FAILURE",
                "failure_reason": "state Hessian block is not positive definite",
            }
        )
        return result
    solution = torch.linalg.solve(symmetric, cross_state_parameter)
    solve_residual = symmetric @ solution - cross_state_parameter
    relative_residual = float(torch.linalg.vector_norm(solve_residual).item()) / max(
        float(torch.linalg.vector_norm(cross_state_parameter).item()), 1.0e-30
    )
    reduced = parameter_block - cross_parameter_state @ solution
    solve_pass = relative_residual <= float(
        specification["solve_relative_tolerance"]
    )
    result.update(
        {
            "status": "PASS" if solve_pass else "NUMERICAL_FAILURE",
            "failure_reason": None
            if solve_pass
            else "state-block solve residual exceeds tolerance",
            "reduced_hessian": reduced.tolist() if solve_pass else None,
            "solve_relative_residual": relative_residual,
        }
    )
    return result


def full_hessian_references(
    residual_function: ResidualFunction,
    theta_base: torch.Tensor,
    parameter_base: torch.Tensor,
    gamma: float,
    specification: dict[str, Any],
) -> dict[str, Any]:
    theta_size = theta_base.numel()
    joint = torch.cat([theta_base, parameter_base]).detach()

    def unnormalized_loss(current: torch.Tensor) -> torch.Tensor:
        theta = current[:theta_size]
        parameter = current[theta_size:]
        residual = residual_function(theta, parameter)
        return 0.5 * torch.sum(residual.square())

    hessian = torch.func.hessian(unnormalized_loss)(joint)
    symmetry = float(torch.linalg.matrix_norm(hessian - hessian.T).item()) / max(
        float(torch.linalg.matrix_norm(hessian).item()), 1.0e-30
    )
    if not torch.all(torch.isfinite(hessian)):
        raise ValueError("full Hessian contains non-finite values")
    state = hessian[:theta_size, :theta_size]
    state_parameter = hessian[:theta_size, theta_size:]
    parameter_state = hessian[theta_size:, :theta_size]
    parameter = hessian[theta_size:, theta_size:]
    identity = torch.eye(
        theta_size, dtype=theta_base.dtype, device=theta_base.device
    )
    unregularized = _reduce_hessian(
        state,
        state_parameter,
        parameter_state,
        parameter,
        specification,
    )
    matched = _reduce_hessian(
        state + gamma * identity,
        state_parameter,
        parameter_state,
        parameter,
        specification,
    )
    symmetry_pass = symmetry <= float(
        specification["symmetry_relative_tolerance"]
    )
    reductions_pass = all(
        item["status"] == "PASS" for item in [unregularized, matched]
    )
    overall_pass = symmetry_pass and reductions_pass
    if not symmetry_pass:
        failure_reason = "full Hessian symmetry tolerance failed"
    elif not reductions_pass:
        failure_reason = "one or more state Hessian blocks are not valid for reduction"
    else:
        failure_reason = None
    return {
        "status": "PASS" if overall_pass else "NUMERICAL_FAILURE",
        "failure_reason": failure_reason,
        "dimension": int(hessian.shape[0]),
        "symmetry_relative_error": symmetry,
        "exact_parameter_block": parameter.tolist(),
        "unregularized": unregularized,
        "gamma_matched": matched,
    }


def gauss_newton_references(
    linearization: ResidualLinearization,
    gamma: float,
    cg_tolerance: float,
    cg_max_iterations: int,
) -> dict[str, Any]:
    jacobian_theta, jacobian_parameter = linearization.explicit_jacobians()
    raw = jacobian_parameter.T @ jacobian_parameter
    operator = explicit_tikhonov_operator(jacobian_theta, gamma)
    explicit = jacobian_parameter.T @ operator @ jacobian_parameter
    result: dict[str, Any] = {
        "status": "PASS",
        "failure_reason": None,
        "Fraw": raw.tolist(),
        "Fse_explicit": explicit.tolist(),
        "Fse_matrix_free": None,
        "explicit_matrix_free_relative_error": None,
        "CG_iterations": None,
        "CG_relative_residual": None,
    }
    try:
        matrix_free = compute_matrix_free_saeps(
            linearization, gamma, cg_tolerance, cg_max_iterations
        )
        relative_error = float(
            torch.linalg.matrix_norm(matrix_free.eliminated_curvature - explicit).item()
        ) / max(float(torch.linalg.matrix_norm(explicit).item()), 1.0e-30)
        result.update(
            {
                "Fse_matrix_free": matrix_free.eliminated_curvature.tolist(),
                "explicit_matrix_free_relative_error": relative_error,
                "CG_iterations": [solve.iterations for solve in matrix_free.solves],
                "CG_relative_residual": [
                    solve.relative_residual for solve in matrix_free.solves
                ],
                "JVP_count": matrix_free.operation_counts.get("jvp_theta", 0)
                + matrix_free.operation_counts.get("jvp_parameter", 0),
                "VJP_count": matrix_free.operation_counts.get("vjp_theta", 0),
            }
        )
    except Exception as error:
        result.update(
            {
                "status": "SOLVER_FAILURE",
                "failure_reason": f"{type(error).__name__}: {error}",
            }
        )
    return result


def run_foundation_development(
    config_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root)
    specification = load_config(config_path)
    if specification["confirmation_authorized"] is not False:
        raise ValueError("v3 foundation must not authorize confirmation")
    seed = int(specification["foundation_validation_seed"])
    if seed != 20 or seed in range(10, 20):
        raise ValueError("v3 foundation seed isolation failed")
    locked_path = root / specification["source_scalar_config"]
    locked = load_config(locked_path)
    locked_sha256 = hashlib.sha256(locked_path.read_bytes()).hexdigest()
    expected_v2_hash = "cb5c2e9e3eee2d5462dd92ac0b9cd3b2b607ea487367d9c83b18a3a8af9c5cf8"
    if locked_sha256 != expected_v2_hash:
        raise RuntimeError("v2 scalar lock changed before v3 development")

    runtime = _runtime_config(locked)
    truth = solve_truth(runtime, "Burgers")
    provenance = environment_provenance(
        root, locked["dtype"], locked["device"]
    )
    digest = config_hash(specification)
    run_id = make_run_id("V3-foundation", seed, digest, provenance["timestamp"])
    destination = Path(output_root) / run_id
    destination.mkdir(parents=True, exist_ok=False)

    checkpoint, points = train_scalar_checkpoint(
        runtime, "Burgers", seed, truth
    )
    residual_function: ResidualFunction = lambda theta, parameter: scalar_residual(
        theta, parameter, "Burgers", points, truth, runtime
    )
    theta_base, base = refine_common_base(
        residual_function,
        checkpoint.theta,
        checkpoint.log_parameter,
        specification["base_refinement"],
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "phase": "V3_FOUNDATION_DEVELOPMENT",
        "run_id": run_id,
        "seed": seed,
        "split": specification["split"],
        "benchmark": "Burgers",
        "config_path": str(Path(config_path).relative_to(root)).replace("\\", "/"),
        "config_hash": digest,
        "v2_scalar_lock_sha256": locked_sha256,
        "provenance": provenance,
        "joint_training": {
            "training_seconds": checkpoint.elapsed_seconds,
            "training_loss_mean": checkpoint.training_loss,
            "learned_log_parameter": float(checkpoint.log_parameter[0].item()),
            "learned_parameter": float(torch.exp(checkpoint.log_parameter)[0].item()),
            "state_rmse_validation_only": checkpoint.state_rmse,
        },
        "common_base_refinement": base,
        "gauss_newton": None,
        "full_hessian": None,
        "profiles": None,
    }
    if theta_base is None:
        result.update(
            {
                "status": "PROFILE_FAILURE",
                "engineering_gate": "FAILED",
                "failure_reason": "common base refinement failed",
                "scientific_gate": "NONE_DEVELOPMENT_ONLY",
            }
        )
    else:
        linearization = ResidualLinearization(
            residual_function, theta_base, checkpoint.log_parameter
        )
        residual = linearization.residual()
        jacobian_theta, jacobian_parameter = linearization.explicit_jacobians()
        gamma = float(specification["gamma"]["alpha"]) * float(
            torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item()
        )
        base.update(
            {
                "theta_stationarity_residual_normalized": _stationarity(
                    jacobian_theta, residual
                ),
                "parameter_stationarity_residual_normalized": _stationarity(
                    jacobian_parameter, residual
                ),
            }
        )
        gauss_newton = gauss_newton_references(
            linearization,
            gamma,
            float(specification["gamma"]["cg_tolerance"]),
            int(specification["gamma"]["cg_max_iterations"]),
        )
        full_hessian = full_hessian_references(
            residual_function,
            theta_base,
            checkpoint.log_parameter,
            gamma,
            specification["full_hessian"],
        )
        unregularized = run_multiscale_profile(
            residual_function,
            theta_base,
            checkpoint.log_parameter,
            gamma,
            specification["profile"],
            matched=False,
        )
        matched = run_multiscale_profile(
            residual_function,
            theta_base,
            checkpoint.log_parameter,
            gamma,
            specification["profile"],
            matched=True,
        )
        all_points_final = all(
            profile["all_points_have_final_status"]
            for profile in [unregularized, matched]
        )
        full_diagnostics = all(
            key in full_hessian
            for key in ["symmetry_relative_error", "unregularized", "gamma_matched"]
        )
        engineering_pass = (
            base["status"] == "PASS"
            and all_points_final
            and full_diagnostics
        )
        result.update(
            {
                "status": "PASS" if engineering_pass else "NUMERICAL_FAILURE",
                "engineering_gate": "PASSED" if engineering_pass else "FAILED",
                "failure_reason": None
                if engineering_pass
                else "v3 foundation engineering requirement failed",
                "scientific_gate": "NONE_DEVELOPMENT_ONLY",
                "gamma": gamma,
                "residual_count": int(residual.numel()),
                "gauss_newton": gauss_newton,
                "full_hessian": full_hessian,
                "profiles": {
                    "unregularized": unregularized,
                    "gamma_matched": matched,
                },
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
