"""End-to-end numerical validation of the SAEPS core on a tiny neural residual."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import torch

from saeps.autodiff import ResidualLinearization, finite_difference_jacobian
from saeps.config import config_hash, load_config
from saeps.coordinates import LogCoordinate
from saeps.core import (
    MatrixFreeEliminator,
    compute_matrix_free_saeps,
    exact_svd_complement_projector,
    explicit_tikhonov_operator,
    raw_curvature,
    retained_sensitivity,
    state_eliminated_curvature,
    state_eliminated_score,
)
from saeps.provenance import environment_provenance, make_run_id
from saeps.residual import stack_weighted_residuals
from saeps.seed import set_deterministic_seed


def _relative_error(actual: torch.Tensor, reference: torch.Tensor) -> float:
    numerator = torch.linalg.vector_norm(actual - reference)
    denominator = torch.linalg.vector_norm(reference) + torch.finfo(reference.dtype).eps
    return float((numerator / denominator).item())


def _tiny_problem(config: dict[str, Any]) -> tuple[Any, torch.Tensor, torch.Tensor]:
    problem = config["tiny_problem"]
    width = int(problem["hidden_width"])
    points = int(problem["grid_points"])
    parameter_count = int(problem["target_parameters"])
    if width < 1 or points < 3 or parameter_count != 2:
        raise ValueError("P1 tiny problem requires width >= 1, points >= 3, and two parameters")

    dtype = getattr(torch, str(config["dtype"]))
    generator = torch.Generator(device="cpu").manual_seed(int(config["seed"]))
    theta = 0.35 * torch.randn(3 * width + 1, dtype=dtype, generator=generator)
    log_parameter = torch.log(torch.tensor([0.8, 1.25], dtype=dtype))
    grid = torch.linspace(0.0, 1.0, points, dtype=dtype)
    observed = torch.sin(torch.pi * grid) + 0.15 * torch.cos(2.0 * torch.pi * grid)
    true_physical = torch.tensor([0.8, 1.25], dtype=dtype)
    log_coordinate = LogCoordinate()

    def residual_function(state: torch.Tensor, coordinate: torch.Tensor) -> torch.Tensor:
        first_weight = state[:width]
        first_bias = state[width : 2 * width]
        second_weight = state[2 * width : 3 * width]
        output_bias = state[-1]
        activation = torch.tanh(grid[:, None] * first_weight[None, :] + first_bias[None, :])
        prediction = activation @ second_weight + output_bias
        derivative = (
            (1.0 - activation.square())
            * first_weight[None, :]
            * second_weight[None, :]
        ).sum(dim=1)
        physical = log_coordinate.to_physical(coordinate)
        pde = derivative + physical[0] * prediction + physical[1] * torch.sin(torch.pi * grid)
        target_pde = (
            torch.pi * torch.cos(torch.pi * grid)
            - 0.3 * torch.pi * torch.sin(2.0 * torch.pi * grid)
            + true_physical[0] * observed
            + true_physical[1] * torch.sin(torch.pi * grid)
        )
        return stack_weighted_residuals(
            {"pde": pde - target_pde, "data": prediction - observed},
            {"pde": float(problem["pde_weight"]), "data": float(problem["data_weight"])},
        )

    return residual_function, theta, log_parameter


def _assert_config(config: dict[str, Any]) -> None:
    required = {"phase", "seed", "dtype", "tiny_problem", "saeps", "acceptance"}
    missing = required - config.keys()
    if missing:
        raise ValueError(f"P1 config missing keys: {sorted(missing)}")
    if config["phase"] != "P1" or config["dtype"] != "float64":
        raise ValueError("P1 validation is locked to phase P1 and float64")


def run_core_validation(
    config_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
    *,
    write_output: bool = True,
) -> dict[str, Any]:
    """Run all P1 gates and optionally persist a machine-readable record."""
    started = time.perf_counter()
    config = load_config(config_path)
    _assert_config(config)
    set_deterministic_seed(int(config["seed"]))
    residual_function, theta, parameter = _tiny_problem(config)
    acceptance = config["acceptance"]
    settings = config["saeps"]

    explicit_linearization = ResidualLinearization(residual_function, theta, parameter)
    residual = explicit_linearization.residual()
    jacobian_theta, jacobian_parameter = explicit_linearization.explicit_jacobians()
    normal = jacobian_theta.T @ jacobian_theta
    lambda_max = float(torch.linalg.eigvalsh(normal).max().item())
    gamma = float(settings["gamma_alpha"]) * lambda_max
    if not gamma > 0.0:
        raise RuntimeError("regularization gamma is not positive")

    explicit_operator = explicit_tikhonov_operator(jacobian_theta, gamma)
    fixed_curvature = raw_curvature(jacobian_parameter)
    explicit_curvature = state_eliminated_curvature(jacobian_parameter, explicit_operator)
    explicit_score = state_eliminated_score(jacobian_parameter, explicit_operator, residual)
    exact_projector, svd_rank = exact_svd_complement_projector(
        jacobian_theta, float(settings["svd_relative_tolerance"])
    )
    exact_curvature = state_eliminated_curvature(jacobian_parameter, exact_projector)

    matrix_free_linearization = ResidualLinearization(residual_function, theta, parameter)
    matrix_free = compute_matrix_free_saeps(
        matrix_free_linearization,
        gamma,
        float(settings["cg_tolerance"]),
        int(settings["cg_max_iterations"]),
    )
    eliminator = MatrixFreeEliminator(
        matrix_free_linearization,
        gamma,
        float(settings["cg_tolerance"]),
        int(settings["cg_max_iterations"]),
    )
    generator = torch.Generator(device="cpu").manual_seed(int(config["seed"]) + 1)
    operator_errors: list[float] = []
    random_solve_residuals: list[float] = []
    for _ in range(int(acceptance["random_operator_vectors"])):
        vector = torch.randn(residual.numel(), dtype=theta.dtype, generator=generator)
        application = eliminator.apply(vector)
        operator_errors.append(_relative_error(application.value, explicit_operator @ vector))
        random_solve_residuals.append(application.solve.relative_residual)

    theta_fd = finite_difference_jacobian(
        lambda current: residual_function(current, parameter), theta, float(acceptance["finite_difference_step"])
    )
    parameter_fd = finite_difference_jacobian(
        lambda current: residual_function(theta, current), parameter, float(acceptance["finite_difference_step"])
    )
    fd_theta_error = _relative_error(theta_fd, jacobian_theta)
    fd_parameter_error = _relative_error(parameter_fd, jacobian_parameter)
    curvature_error = _relative_error(matrix_free.eliminated_curvature, explicit_curvature)
    score_error = _relative_error(matrix_free.eliminated_score, explicit_score)
    symmetry_error = _relative_error(matrix_free.eliminated_curvature, matrix_free.eliminated_curvature.T)
    symmetric_curvature = 0.5 * (matrix_free.eliminated_curvature + matrix_free.eliminated_curvature.T)
    difference = fixed_curvature - matrix_free.eliminated_curvature
    minimum_eigenvalue = float(torch.linalg.eigvalsh(symmetric_curvature).min().item())
    loewner_minimum = float(torch.linalg.eigvalsh(0.5 * (difference + difference.T)).min().item())
    psd_scale = max(float(torch.linalg.eigvalsh(symmetric_curvature).max().item()), 1.0e-30)
    loewner_scale = max(float(torch.linalg.matrix_norm(fixed_curvature).item()), 1.0)
    formal_solve_residuals = [item.relative_residual for item in matrix_free.solves]

    repeat = compute_matrix_free_saeps(
        ResidualLinearization(residual_function, theta, parameter),
        gamma,
        float(settings["cg_tolerance"]),
        int(settings["cg_max_iterations"]),
    )
    reproducibility_error = max(
        float(torch.max(torch.abs(matrix_free.eliminated_curvature - repeat.eliminated_curvature)).item()),
        float(torch.max(torch.abs(matrix_free.eliminated_score - repeat.eliminated_score)).item()),
        float(torch.max(torch.abs(matrix_free.eta - repeat.eta)).item()),
    )

    checks = {
        "operator_relative_error": max(operator_errors) < float(acceptance["operator_relative_error"]),
        "curvature_relative_error": curvature_error < float(acceptance["curvature_relative_error"]),
        "score_relative_error": score_error < float(acceptance["curvature_relative_error"]),
        "symmetry": symmetry_error < float(acceptance["symmetry_relative_error"]),
        "positive_semidefinite": minimum_eigenvalue
        >= -float(acceptance["psd_relative_tolerance"]) * psd_scale,
        "loewner_relation": loewner_minimum
        >= -float(acceptance["psd_relative_tolerance"]) * loewner_scale,
        "scalar_eta_bounds": bool(
            torch.all(matrix_free.eta >= -float(acceptance["scalar_eta_tolerance"]))
            and torch.all(matrix_free.eta <= 1.0 + float(acceptance["scalar_eta_tolerance"]))
        ),
        "formal_cg_residuals": max(formal_solve_residuals) <= float(acceptance["cg_relative_residual"]),
        "random_cg_residuals": max(random_solve_residuals) <= float(acceptance["cg_relative_residual"]),
        "finite_difference_theta": fd_theta_error < float(acceptance["finite_difference_relative_error"]),
        "finite_difference_parameter": fd_parameter_error < float(acceptance["finite_difference_relative_error"]),
        "reproducibility": reproducibility_error <= float(acceptance["reproducibility_absolute_tolerance"]),
        "matrix_free_no_explicit_jacobian": matrix_free_linearization.operation_counts.get("explicit_jacobians", 0) == 0,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    provenance = environment_provenance(repo_root, config["dtype"], "cpu")
    digest = config_hash(config)
    run_id = make_run_id("P1-core", int(config["seed"]), digest, provenance["timestamp"])
    result: dict[str, Any] = {
        "schema_version": 1,
        "phase": "P1",
        "run_id": run_id,
        "status": status,
        "config_hash": digest,
        "regularization": {
            "rule": "gamma = gamma_alpha * lambda_max(J_theta^T J_theta)",
            "gamma_alpha": float(settings["gamma_alpha"]),
            "lambda_max": lambda_max,
            "gamma": gamma,
        },
        "dimensions": {"residual": residual.numel(), "theta": theta.numel(), "parameter": parameter.numel(), "svd_rank": svd_rank},
        "metrics": {
            "operator_relative_errors": operator_errors,
            "operator_relative_error_max": max(operator_errors),
            "curvature_relative_error": curvature_error,
            "score_relative_error": score_error,
            "symmetry_relative_error": symmetry_error,
            "minimum_eigenvalue": minimum_eigenvalue,
            "loewner_minimum_eigenvalue": loewner_minimum,
            "eta": matrix_free.eta.tolist(),
            "finite_difference_theta_relative_error": fd_theta_error,
            "finite_difference_parameter_relative_error": fd_parameter_error,
            "formal_cg_relative_residuals": formal_solve_residuals,
            "random_cg_relative_residuals": random_solve_residuals,
            "reproducibility_max_abs_error": reproducibility_error,
            "exact_svd_curvature": exact_curvature.tolist(),
            "tikhonov_curvature": explicit_curvature.tolist(),
        },
        "checks": checks,
        "operation_counts": dict(matrix_free_linearization.operation_counts),
        "elapsed_seconds": time.perf_counter() - started,
        "provenance": provenance,
    }
    if write_output:
        destination = Path(output_root) / run_id
        destination.mkdir(parents=True, exist_ok=False)
        with (destination / "result.json").open("w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
            stream.write("\n")
    if status != "PASS":
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(f"P1 validation failed: {failed}")
    return result
