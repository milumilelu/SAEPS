"""Bounded S2 profile development for the paper-strengthening namespace.

This module reuses immutable historical Allen--Cahn checkpoints as inputs and
writes only to ``outputs/runs/paper_strengthening_v1``.  It is a development
diagnostic: no confirmation seed, manuscript number, or historical output is
modified.
"""

from __future__ import annotations

import copy
import json
import math
import statistics
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


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def _local_specification(root: Path, tolerance: float) -> dict[str, Any]:
    numerical = load_config(root / "configs/v3_6/locked_scalar_confirmation.yaml")
    local = copy.deepcopy(numerical["center"]["local_minimum"])
    local["normalized_gradient_tolerance"] = float(tolerance)
    local["stopping"]["normalized_gradient"] = float(tolerance)
    return local


def _finite_or_none(value: float | None) -> float | None:
    if value is None or not math.isfinite(float(value)):
        return None
    return float(value)


def _run_seed(
    root: Path,
    config: dict[str, Any],
    arm: dict[str, Any],
    seed: int,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    destination = root / config["output_root"] / f"arm_{arm['id']}" / f"seed_{seed}"
    if destination.exists():
        raise RuntimeError(f"S2 output already exists: {destination}")
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
    gamma = float(config["gamma_alpha"]) * lambda_max
    h_tt, h_tl, h_ll, symmetry = _full_hessian_blocks(residual_function, theta0, parameter0)
    numerical = load_config(root / "configs/v3_6/locked_scalar_confirmation.yaml")
    exact = _reduce_hessian(
        h_tt + gamma * torch.eye(theta0.numel(), dtype=theta0.dtype),
        h_tl,
        h_tl.T,
        h_ll,
        numerical["gold_standard"],
    )
    exact_value = (
        float(exact["reduced_hessian"][0][0])
        if exact["reduced_hessian"]
        else None
    )
    exact_pass = bool(
        exact["status"] == "PASS"
        and symmetry <= float(numerical["gold_standard"]["symmetry_relative_tolerance"])
    )
    local = _local_specification(root, float(arm["normalized_gradient_tolerance"]))
    residual_count = int(linearization.residual().numel())
    center_objective = _mean_residual_objective(
        residual_function, parameter0, theta0, gamma, True
    )
    center_loss = float(center_objective(theta0).item())
    losses: dict[float, float] = {}
    point_rows: list[dict[str, Any]] = []
    for h in [float(value) for value in arm["h_values"]]:
        for sign in (-1.0, 1.0):
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
            failure_reason = optimization.get("failure_reason")
            if optimized is not None:
                diagnostics, _, _, _ = exact_state_diagnostics(objective, optimized, local)
                loss = float(objective(optimized).item())
                if diagnostics["local_minimum_gate"] == "PASS":
                    status = "PASS"
                    losses[offset] = loss
                else:
                    failure_reason = "exact local-minimum gate failed"
            point_rows.append(
                {
                    "h": h,
                    "sign": int(sign),
                    "offset": offset,
                    "start": "independent_common_theta0",
                    "status": status,
                    "loss_mean": _finite_or_none(loss),
                    "failure_reason": failure_reason,
                    "exact_diagnostics": diagnostics,
                    "optimization": optimization,
                    "elapsed_seconds": time.perf_counter() - point_started,
                }
            )

    curvatures: list[dict[str, Any]] = []
    for h in [float(value) for value in arm["h_values"]]:
        curvature = (
            residual_count * (losses[h] - 2.0 * center_loss + losses[-h]) / (h * h)
            if h in losses and -h in losses
            else None
        )
        curvatures.append({"h": h, "curvature": _finite_or_none(curvature)})
    by_h = {row["h"]: row["curvature"] for row in curvatures}
    ordered_h = sorted(float(value) for value in arm["h_values"])
    finest = by_h[ordered_h[-1]]
    previous = by_h[ordered_h[-2]]
    exact_error = (
        abs(finest - exact_value) / max(abs(exact_value), 1.0e-8)
        if finest is not None and exact_value is not None
        else None
    )
    resolution_change = (
        abs(finest - previous) / max(abs(finest), 1.0e-8)
        if finest is not None and previous is not None
        else None
    )
    all_points_pass = len(point_rows) == 2 * len(arm["h_values"]) and all(
        row["status"] == "PASS" for row in point_rows
    )
    record = {
        "schema_version": 1,
        "protocol_id": config["protocol_id"],
        "phase": config["phase"],
        "role": "development_only_profile_resolution_diagnostic",
        "namespace": config["namespace"],
        "benchmark": benchmark,
        "seed": int(seed),
        "arm_id": arm["id"],
        "status": "PASS" if all_points_pass and exact_pass else "PROFILE_FAILURE",
        "failure_reason": None
        if all_points_pass and exact_pass
        else "profile or exact finite-gamma reference gate failed",
        "config_hash": config_hash(config),
        "source_hashes": {
            "source_checkpoint_manifest": sha256_file(
                root
                / "outputs/runs/v5/checkpoints/allen_cahn"
                / f"seed_{seed}/checkpoint_manifest.json"
            ),
            "source_model_state": manifest["model_state_hash"],
            **runtime_hashes,
        },
        "provenance": provenance,
        "gamma_alpha": float(config["gamma_alpha"]),
        "gamma": gamma,
        "lambda_max": lambda_max,
        "m": residual_count,
        "n_theta": int(theta0.numel()),
        "independent_start_from_common_theta0": True,
        "continuation_used": False,
        "center_loss_mean": center_loss,
        "exact_reference": {**exact, "full_hessian_symmetry_relative_error": symmetry},
        "H_red_exact_gamma": exact_value,
        "profile_points": point_rows,
        "curvatures": curvatures,
        "all_profile_points_pass": all_points_pass,
        "profile_point_count": len(point_rows),
        "profile_pass_count": sum(row["status"] == "PASS" for row in point_rows),
        "finest_profile_exact_relative_error": _finite_or_none(exact_error),
        "last_two_curvature_relative_change": _finite_or_none(resolution_change),
        "selection_forbidden_metrics_computed": False,
        "elapsed_seconds": time.perf_counter() - started,
    }
    write_json_atomic(destination / "result.json", record)
    return record


def _summarize(config: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = []
    for arm in config["arms"]:
        arm_rows = [row for row in rows if row["arm_id"] == arm["id"]]
        changes = [
            row["last_two_curvature_relative_change"]
            for row in arm_rows
            if row["last_two_curvature_relative_change"] is not None
        ]
        errors = [
            row["finest_profile_exact_relative_error"]
            for row in arm_rows
            if row["finest_profile_exact_relative_error"] is not None
        ]
        summary = {
            "arm_id": arm["id"],
            "planned_seed_count": len(arm_rows),
            "all_points_pass_seed_count": sum(row["all_profile_points_pass"] for row in arm_rows),
            "total_profile_point_count": sum(row["profile_point_count"] for row in arm_rows),
            "total_profile_pass_count": sum(row["profile_pass_count"] for row in arm_rows),
            "median_last_two_curvature_relative_change": statistics.median(changes)
            if changes
            else None,
            "median_finest_profile_exact_relative_error": statistics.median(errors)
            if errors
            else None,
        }
        summary["selection_key"] = [
            -summary["all_points_pass_seed_count"],
            -summary["total_profile_pass_count"],
            summary["median_last_two_curvature_relative_change"]
            if summary["median_last_two_curvature_relative_change"] is not None
            else math.inf,
            summary["median_finest_profile_exact_relative_error"]
            if summary["median_finest_profile_exact_relative_error"] is not None
            else math.inf,
            arm["id"],
        ]
        summaries.append(summary)
    selected = min(summaries, key=lambda value: value["selection_key"])
    freezeable = selected["all_points_pass_seed_count"] >= int(
        config["selection_rule"]["minimum_seed_count_for_freeze"]
    )
    return {
        "schema_version": 1,
        "protocol_id": config["protocol_id"],
        "phase": config["phase"],
        "namespace": config["namespace"],
        "selection_rule": config["selection_rule"],
        "forbidden_metrics_read": False,
        "planned_denominator": len(config["development_seeds"]),
        "terminal_count": len(rows),
        "arm_summaries": summaries,
        "selected_development_arm": selected["arm_id"],
        "freezeable_under_development_rule": freezeable,
        "confirmation_authorized": False,
        "source_records": [
            {
                "path": f"{config['output_root']}/arm_{row['arm_id']}/seed_{row['seed']}/result.json",
                "seed": row["seed"],
                "arm_id": row["arm_id"],
            }
            for row in rows
        ],
    }


def run_s2(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config = load_config(root / "configs/paper_strengthening/development.yaml")
    if config["confirmation_authorized"] is not False:
        raise RuntimeError("S2 must not authorize confirmation")
    provenance = environment_provenance(root, "float64", "cpu")
    rows = []
    for arm in config["arms"]:
        for seed in config["development_seeds"]:
            rows.append(_run_seed(root, config, arm, int(seed), provenance))
    summary = _summarize(config, rows)
    summary["config_hash"] = config_hash(config)
    summary["provenance"] = provenance
    write_json_atomic(root / config["output_root"] / "S2_DEVELOPMENT_SUMMARY.json", summary)
    return summary
