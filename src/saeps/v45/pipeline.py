"""Fresh-seed controlled-mechanism engineering pipeline."""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.controlled import (
    _stationarity,
    base_residual,
    fourier_library,
    make_diagnostic_points,
    train_checkpoint,
)
from saeps.core import compute_matrix_free_saeps, explicit_tikhonov_operator
from saeps.provenance import environment_provenance
from saeps.v31.local_minimum import exact_state_diagnostics
from saeps.v43.center import allen_center_candidates


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run_v45_engineering_seed(root: Path, seed: int) -> dict[str, Any]:
    development_path = root / "configs/v4_5/controlled_mechanism_development.yaml"
    development = load_config(development_path)
    if seed not in development["engineering_seeds"]:
        raise ValueError("only registered v4.5 engineering seeds are authorized")
    destination = root / f"outputs/runs/v4_5_controlled_mechanism/engineering/seed_{seed}"
    if destination.exists():
        raise RuntimeError("seed output already exists; rerun forbidden")
    for item in development["protected_sources"].values():
        if _sha256(root / item["path"]) != item["sha256"]:
            raise RuntimeError(f"protected source hash mismatch: {item['path']}")
    controlled = load_config(root / "configs/locked/controlled_geometry.yaml")
    local = load_config(root / "configs/v3_4/curvature_validation.yaml")["local_minimum"]
    provenance = environment_provenance(root, controlled["dtype"], controlled["device"])
    started = time.perf_counter()
    checkpoint = train_checkpoint(controlled, seed)
    points = make_diagnostic_points(controlled)

    def residual_at_state(state: torch.Tensor) -> torch.Tensor:
        return base_residual(state, points, controlled)

    def objective(state: torch.Tensor) -> torch.Tensor:
        return 0.5 * torch.mean(residual_at_state(state).square())

    baseline, _, _, _ = exact_state_diagnostics(objective, checkpoint.theta, local)
    selected = checkpoint.theta
    center_method = "inherited_baseline"
    center_audit: dict[str, Any] = {"baseline": baseline, "enhanced": None}
    if baseline["local_minimum_gate"] != "PASS":
        candidate, enhanced = allen_center_candidates(
            residual_at_state,
            objective,
            checkpoint.theta,
            seed,
            local,
            development["center_engineering"],
        )
        center_audit["enhanced"] = enhanced
        if candidate is not None:
            selected = candidate
            center_method = "deterministic_enhanced"
    final_center, _, _, _ = exact_state_diagnostics(objective, selected, local)
    residual = residual_at_state(selected)
    jacobian_theta = torch.func.jacrev(residual_at_state)(selected)
    theta_stationarity = _stationarity(jacobian_theta, residual)
    center_valid = (
        final_center["local_minimum_gate"] == "PASS"
        and theta_stationarity
        <= float(controlled["confirmation_rules"]["checkpoint_theta_stationarity_max"])
        and float(objective(selected).item())
        <= float(controlled["confirmation_rules"]["checkpoint_training_loss_max"])
    )
    library = fourier_library(controlled, points)
    parallel = library[controlled["selected_sources"]["q_parallel"]]
    perpendicular = library[controlled["selected_sources"]["q_perpendicular"]]
    lambda_max = float(torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item())
    gamma = float(controlled["gamma"]["nominal_alpha"]) * lambda_max
    log_lambda = torch.tensor(
        [math.log(float(controlled["pde"]["lambda_star"]))], dtype=selected.dtype
    )
    alpha_rows: list[dict[str, Any]] = []
    for alpha_value in controlled["alpha_values"]:
        alpha = float(alpha_value)
        source = math.sqrt(1.0 - alpha) * parallel + math.sqrt(alpha) * perpendicular
        pde_count = points.pde_x.numel()
        scale = math.sqrt(float(controlled["training"]["loss_weights"]["pde"]))

        def parameterized(state: torch.Tensor, parameter: torch.Tensor) -> torch.Tensor:
            value = base_residual(state, points, controlled).clone()
            value[:pde_count] -= scale * (
                torch.exp(parameter[0]) - float(controlled["pde"]["lambda_star"])
            ) * source
            return value

        row: dict[str, Any] = {"alpha": alpha, "status": "CHECKPOINT_INVALID"}
        if center_valid:
            linearization = ResidualLinearization(parameterized, selected, log_lambda)
            matrix_free = compute_matrix_free_saeps(
                linearization,
                gamma,
                float(controlled["gamma"]["cg_tolerance"]),
                int(controlled["gamma"]["cg_max_iterations"]),
            )
            explicit = explicit_tikhonov_operator(jacobian_theta, gamma)
            explicit_curvature = (
                matrix_free.jacobian_parameter.T @ explicit @ matrix_free.jacobian_parameter
            )
            relative_error = float(
                (
                    torch.linalg.matrix_norm(matrix_free.eliminated_curvature - explicit_curvature)
                    / (torch.linalg.matrix_norm(explicit_curvature) + torch.finfo(selected.dtype).eps)
                ).item()
            )
            maximum_residual = max(solve.relative_residual for solve in matrix_free.solves)
            passed = (
                maximum_residual <= float(controlled["gamma"]["cg_acceptance"])
                and relative_error < float(controlled["gamma"]["explicit_mf_relative_tolerance"])
            )
            row = {
                "alpha": alpha,
                "status": "PASS" if passed else "SOLVER_FAILURE",
                "eta": float(matrix_free.eta[0].item()),
                "Fraw": matrix_free.raw_curvature.tolist(),
                "Fse": matrix_free.eliminated_curvature.tolist(),
                "CG_iterations": [solve.iterations for solve in matrix_free.solves],
                "CG_relative_residual": [solve.relative_residual for solve in matrix_free.solves],
                "explicit_mf_relative_error": relative_error,
                "JVP_count": dict(linearization.operation_counts),
            }
        alpha_rows.append(row)
    binding_valid = center_valid and all(row["status"] == "PASS" for row in alpha_rows)
    record = {
        "schema_version": 1,
        "phase": development["phase"],
        "role": "engineering",
        "seed": seed,
        "status": "PASS" if binding_valid else ("CHECKPOINT_INVALID" if not center_valid else "SOLVER_FAILURE"),
        "binding_valid": binding_valid,
        "failure_reason": None if binding_valid else ("center gate failed" if not center_valid else "alpha solver gate failed"),
        "config_hash": config_hash(development),
        "git_commit": provenance["git_commit"],
        "provenance": provenance,
        "training": checkpoint.__dict__ | {"theta": None},
        "center_method": center_method,
        "center": center_audit | {"final": final_center, "theta_stationarity": theta_stationarity},
        "gamma": gamma,
        "lambda_max": lambda_max,
        "alpha_evaluations": alpha_rows,
        "elapsed_seconds": time.perf_counter() - started,
        "selection_forbidden_metrics_not_used": ["eta", "monotonicity", "spearman", "figure_appearance"],
    }
    result_path = destination / "result.json"
    _write(result_path, record)
    _write(
        destination / "manifest.json",
        {
            "schema_version": 1,
            "seed": seed,
            "status": record["status"],
            "binding_valid": binding_valid,
            "result_path": "result.json",
            "result_sha256": _sha256(result_path),
        },
    )
    return record
