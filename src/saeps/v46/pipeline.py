"""Independent controlled-confirmation seed executable preserving v4.5 freeze."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.controlled import _stationarity, base_residual, fourier_library, make_diagnostic_points, train_checkpoint
from saeps.core import MatrixFreeEliminator, explicit_tikhonov_operator
from saeps.v31.local_minimum import exact_state_diagnostics
from saeps.v35.engineering import scaled_augmented_lsqr_candidates
from saeps.v43.center import allen_center_candidates
from saeps.v45.pipeline import _sha256, _write


def run_controlled_confirmation_seed(
    root: Path, seed: int, provenance: dict[str, Any]
) -> dict[str, Any]:
    development = load_config(root / "configs/v4_5/controlled_mechanism_development.yaml")
    if seed not in development["inactive_confirmation_seeds"]:
        raise ValueError("seed is not in the locked confirmation cohort")
    destination = root / f"outputs/runs/v4_5_controlled_mechanism/confirmation/seed_{seed}"
    if destination.exists():
        raise RuntimeError("seed output already exists; rerun forbidden")
    controlled = load_config(root / "configs/locked/controlled_geometry.yaml")
    local = load_config(root / "configs/v3_4/curvature_validation.yaml")["local_minimum"]
    started = time.perf_counter()
    checkpoint = train_checkpoint(controlled, seed)
    points = make_diagnostic_points(controlled)

    def residual_at_state(state: torch.Tensor) -> torch.Tensor:
        return base_residual(state, points, controlled)

    def objective(state: torch.Tensor) -> torch.Tensor:
        return 0.5 * torch.mean(residual_at_state(state).square())

    baseline, _, _, _ = exact_state_diagnostics(objective, checkpoint.theta, local)
    selected = checkpoint.theta
    method = "inherited_baseline"
    enhanced = None
    if baseline["local_minimum_gate"] != "PASS":
        candidate, enhanced = allen_center_candidates(
            residual_at_state, objective, checkpoint.theta, seed, local, development["center_engineering"]
        )
        if candidate is not None:
            selected = candidate
            method = "deterministic_enhanced"
    final_center, _, _, _ = exact_state_diagnostics(objective, selected, local)
    residual = residual_at_state(selected)
    jacobian_theta = torch.func.jacrev(residual_at_state)(selected)
    theta_stationarity = _stationarity(jacobian_theta, residual)
    center_valid = (
        final_center["local_minimum_gate"] == "PASS"
        and theta_stationarity <= float(controlled["confirmation_rules"]["checkpoint_theta_stationarity_max"])
        and float(objective(selected).item()) <= float(controlled["confirmation_rules"]["checkpoint_training_loss_max"])
    )
    library = fourier_library(controlled, points)
    parallel = library[controlled["selected_sources"]["q_parallel"]]
    perpendicular = library[controlled["selected_sources"]["q_perpendicular"]]
    lambda_max = float(torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item())
    gamma = float(controlled["gamma"]["nominal_alpha"]) * lambda_max
    log_lambda = torch.tensor([math.log(float(controlled["pde"]["lambda_star"]))], dtype=selected.dtype)
    solver_spec = development["curvature_solver_engineering"]
    alpha_rows = []
    for alpha_value in controlled["alpha_values"]:
        alpha = float(alpha_value)
        source = math.sqrt(1.0 - alpha) * parallel + math.sqrt(alpha) * perpendicular
        pde_count = points.pde_x.numel()
        scale = math.sqrt(float(controlled["training"]["loss_weights"]["pde"]))

        def parameterized(state: torch.Tensor, parameter: torch.Tensor) -> torch.Tensor:
            value = base_residual(state, points, controlled).clone()
            value[:pde_count] -= scale * (torch.exp(parameter[0]) - float(controlled["pde"]["lambda_star"])) * source
            return value

        row: dict[str, Any] = {"alpha": alpha, "status": "CHECKPOINT_INVALID", "eta": None}
        if center_valid:
            linearization = ResidualLinearization(parameterized, selected, log_lambda)
            _, jacobian_parameter = linearization.explicit_jacobians()
            explicit = explicit_tikhonov_operator(jacobian_theta, gamma)
            explicit_value = float((jacobian_parameter.T @ explicit @ jacobian_parameter)[0, 0].item())
            solver_name = "standard_CG"
            audit: dict[str, Any]
            try:
                eliminator = MatrixFreeEliminator(
                    linearization, gamma, float(solver_spec["standard_CG"]["tolerance"]), int(solver_spec["standard_CG"]["max_iterations"])
                )
                applied = eliminator.apply(jacobian_parameter[:, 0])
                fse = float(torch.dot(jacobian_parameter[:, 0], applied.value).item())
                verified = float(applied.solves[0].relative_residual)
                iterations = int(applied.solves[0].iterations)
                audit = {"standard_CG": {"status": "PASS", "verified_relative_residual": verified, "iterations": iterations}}
            except Exception as error:
                candidates = scaled_augmented_lsqr_candidates(
                    linearization, jacobian_parameter[:, 0], gamma,
                    float(solver_spec["scaled_LSQR_iterative_refinement"]["tolerance"]),
                    int(solver_spec["scaled_LSQR_iterative_refinement"]["max_iterations_per_pass"]),
                    int(solver_spec["scaled_LSQR_iterative_refinement"]["refinement_passes"]),
                )
                solved = candidates["scaled_LSQR_iterative_refinement"]
                solver_name = "scaled_LSQR_iterative_refinement"
                fse = float(solved["Fse"])
                verified = float(solved["verified_original_relative_normal_residual"])
                iterations = int(solved["total_iterations"])
                audit = {"standard_CG": {"status": "SOLVER_FAILURE", "error": f"{type(error).__name__}: {error}"}, "scaled_LSQR_iterative_refinement": candidates}
            relative_error = abs(fse - explicit_value) / max(abs(explicit_value), 1.0e-30)
            passed = verified <= float(solver_spec["verified_normal_residual_acceptance"]) and relative_error < float(solver_spec["explicit_reference_relative_acceptance"]) and iterations <= int(solver_spec["scaled_LSQR_iterative_refinement"]["maximum_total_iterations"])
            fraw = float(torch.dot(jacobian_parameter[:, 0], jacobian_parameter[:, 0]).item())
            row = {"alpha": alpha, "status": "PASS" if passed else "SOLVER_FAILURE", "eta": fse / fraw, "Fraw": fraw, "Fse": fse, "selected_solver": solver_name, "solver_verified_relative_residual": verified, "solver_iterations": iterations, "solver_audit": audit, "explicit_mf_relative_error": relative_error}
        alpha_rows.append(row)
    binding = center_valid and all(row["status"] == "PASS" for row in alpha_rows)
    record = {
        "schema_version": 1, "phase": "V4_5_CONTROLLED_MECHANISM_CONFIRMATION", "role": "confirmation",
        "seed": seed, "status": "PASS" if binding else ("CHECKPOINT_INVALID" if not center_valid else "SOLVER_FAILURE"),
        "binding_valid": binding, "failure_reason": None if binding else ("center gate failed" if not center_valid else "alpha solver gate failed"),
        "config_hash": config_hash(development), "git_commit": provenance["git_commit"], "provenance": provenance,
        "training": checkpoint.__dict__ | {"theta": None}, "center_method": method,
        "center": {"baseline": baseline, "enhanced": enhanced, "final": final_center, "theta_stationarity": theta_stationarity},
        "gamma": gamma, "lambda_max": lambda_max, "alpha_evaluations": alpha_rows,
        "elapsed_seconds": time.perf_counter() - started,
    }
    result_path = destination / "result.json"
    _write(result_path, record)
    _write(destination / "manifest.json", {"schema_version": 1, "seed": seed, "status": record["status"], "binding_valid": binding, "result_path": "result.json", "result_sha256": _sha256(result_path)})
    return record
