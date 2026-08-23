"""Frozen optimizer validation on V5.2A development seeds 73--74."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Callable

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.io_utils import write_json_atomic
from saeps.provenance import environment_provenance
from saeps.scalar import scalar_residual, solve_truth
from saeps.v3.foundation import _reduce_hessian
from saeps.v31.local_minimum import exact_state_diagnostics, optimize_state_local_minimum
from saeps.v31.pipeline import _mean_residual_objective
from saeps.v5.finite_gamma import _full_hessian_blocks, _load_checkpoint, _runtime
from saeps.v5.governance import sha256_file
from saeps.v5.profile_engineering import _local_specification


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]
VALIDATION_SEEDS = [73, 74]


def _verify(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    lock = json.loads((root / "configs/v5/PROFILE_OPTIMIZER_LOCK.json").read_text(encoding="utf-8"))
    if lock["selected_candidate"] != "independent_exact_trust_lbfgs":
        raise RuntimeError("unexpected V5.2A selected optimizer")
    freeze = json.loads(
        (root / "configs/v5/PROFILE_VALIDATION_EXECUTABLE_FREEZE.json").read_text(encoding="utf-8")
    )
    if freeze.get("execution_authorized") is not True:
        raise RuntimeError("V5.2A validation is not authorized")
    for relative, expected in freeze["file_sha256"].items():
        if sha256_file(root / relative) != expected:
            raise RuntimeError(f"V5.2A validation frozen file mismatch: {relative}")
    return lock, load_config(root / "configs/v5/profile_engineering_execution.yaml")


def _run_seed(
    root: Path,
    seed: int,
    provenance: dict[str, Any],
    lock: dict[str, Any],
    execution: dict[str, Any],
) -> dict[str, Any]:
    destination = root / execution["output_root"] / "validation" / f"seed_{seed}"
    if destination.exists():
        raise RuntimeError("V5.2A validation record already exists; rerun forbidden")
    destination.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    theta0, parameter0, points, manifest, _ = _load_checkpoint(root, "allen_cahn", seed)
    runtime, runtime_hashes, benchmark = _runtime(root, "allen_cahn")
    truth = solve_truth(runtime, benchmark)
    residual_function: ResidualFunction = lambda state, coordinate: scalar_residual(
        state, coordinate, benchmark, points, truth, runtime
    )
    linearization = ResidualLinearization(residual_function, theta0, parameter0)
    jacobian_theta, _ = linearization.explicit_jacobians()
    lambda_max = float(torch.linalg.svdvals(jacobian_theta)[0].square().item())
    gamma = float(execution["gamma_alpha"]) * lambda_max
    h_tt, h_tl, h_ll, symmetry = _full_hessian_blocks(residual_function, theta0, parameter0)
    numerical = load_config(root / "configs/v3_6/locked_scalar_confirmation.yaml")
    exact = _reduce_hessian(
        h_tt + gamma * torch.eye(theta0.numel(), dtype=theta0.dtype),
        h_tl,
        h_tl.T,
        h_ll,
        numerical["gold_standard"],
    )
    exact_value = float(exact["reduced_hessian"][0][0]) if exact["reduced_hessian"] else None
    exact_pass = (
        exact["status"] == "PASS"
        and symmetry <= float(numerical["gold_standard"]["symmetry_relative_tolerance"])
    )
    local = _local_specification(
        root, float(lock["selected_settings"]["normalized_gradient_tolerance"])
    )
    m = int(linearization.residual().numel())
    center_objective = _mean_residual_objective(
        residual_function, parameter0, theta0, gamma, True
    )
    center_loss = float(center_objective(theta0).item())
    points_rows = []
    losses: dict[float, float] = {}
    for h in [float(value) for value in lock["selected_settings"]["h_values"]]:
        for sign in [-1.0, 1.0]:
            offset = sign * h
            coordinate = parameter0 + offset * torch.ones_like(parameter0)
            objective = _mean_residual_objective(
                residual_function, coordinate, theta0, gamma, True
            )
            point_started = time.perf_counter()
            optimized, optimization = optimize_state_local_minimum(objective, theta0, local)
            diagnostics = None
            loss = None
            status = "PROFILE_FAILURE"
            if optimized is not None:
                diagnostics, _, _, _ = exact_state_diagnostics(objective, optimized, local)
                loss = float(objective(optimized).item())
                if diagnostics["local_minimum_gate"] == "PASS":
                    status = "PASS"
                    losses[offset] = loss
            points_rows.append(
                {
                    "h": h,
                    "sign": int(sign),
                    "offset": offset,
                    "start": "independent_common_theta0",
                    "status": status,
                    "loss_mean": loss,
                    "exact_diagnostics": diagnostics,
                    "optimization": optimization,
                    "elapsed_seconds": time.perf_counter() - point_started,
                }
            )
    curvatures = []
    for h in [float(value) for value in lock["selected_settings"]["h_values"]]:
        curvature = (
            m * (losses[h] - 2.0 * center_loss + losses[-h]) / (h * h)
            if h in losses and -h in losses
            else None
        )
        curvatures.append({"h": h, "curvature": curvature})
    values = {row["h"]: row["curvature"] for row in curvatures}
    finest, previous = values[0.005], values[0.01]
    exact_error = (
        abs(finest - exact_value) / max(abs(exact_value), 1.0e-8)
        if finest is not None and exact_value is not None
        else None
    )
    change = (
        abs(finest - previous) / max(abs(finest), 1.0e-8)
        if finest is not None and previous is not None
        else None
    )
    all_points = len(points_rows) == 8 and all(row["status"] == "PASS" for row in points_rows)
    passed = exact_pass and all_points
    record = {
        "schema_version": 1,
        "phase": "V5_2A_PROFILE_VALIDATION",
        "role": "frozen_optimizer_development_validation",
        "benchmark": benchmark,
        "seed": seed,
        "selected_candidate": lock["selected_candidate"],
        "status": "PASS" if passed else "PROFILE_FAILURE",
        "binding_valid": passed,
        "failure_stage": None if passed else "profile_or_exact",
        "failure_reason": None if passed else "frozen optimizer validation chain failed",
        "config_hash": config_hash(execution),
        "source_hashes": {
            "profile_optimizer_lock": sha256_file(root / "configs/v5/PROFILE_OPTIMIZER_LOCK.json"),
            "checkpoint_manifest": sha256_file(
                root / "outputs/runs/v5/checkpoints/allen_cahn" / f"seed_{seed}/checkpoint_manifest.json"
            ),
            "model_state": manifest["model_state_hash"],
            **runtime_hashes,
        },
        "provenance": provenance,
        "gamma_alpha": float(execution["gamma_alpha"]),
        "gamma": gamma,
        "diagnostic_set_hash": manifest["diagnostic_set_hash"],
        "m": m,
        "n_theta": int(theta0.numel()),
        "independent_start_from_common_theta0": True,
        "continuation_used": False,
        "exact_reference": {**exact, "full_hessian_symmetry_relative_error": symmetry},
        "H_red_exact_gamma": exact_value,
        "profile_points": points_rows,
        "curvatures": curvatures,
        "all_8_profile_points_pass": all_points,
        "finest_profile_exact_relative_error": exact_error,
        "last_two_curvature_relative_change": change,
        "accuracy_thresholds_binding_for_validation_gate": False,
        "selection_forbidden_metrics_computed": False,
        "elapsed_seconds": time.perf_counter() - started,
    }
    write_json_atomic(destination / "result.json", record)
    return record


def run_profile_validation(repo_root: str | Path) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    lock, execution = _verify(root)
    provenance = environment_provenance(root, "float64", "cpu")
    if provenance["git_dirty"]:
        raise RuntimeError("V5.2A validation requires a clean committed executable")
    for seed in VALIDATION_SEEDS:
        if (root / execution["output_root"] / "validation" / f"seed_{seed}").exists():
            raise RuntimeError("V5.2A validation cohort has prior output; rerun forbidden")
    return [_run_seed(root, seed, provenance, lock, execution) for seed in VALIDATION_SEEDS]
