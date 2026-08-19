"""Resolution-certified gamma profile with branch-continuity diagnostics."""

from __future__ import annotations

import copy
import math
from typing import Any, Callable

import torch

from saeps.scalar import scalar_network
from saeps.v31.local_minimum import exact_state_diagnostics, optimize_state_local_minimum
from saeps.v31.pipeline import _mean_residual_objective


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def _local_specification(base: dict[str, Any], tolerance: float) -> dict[str, Any]:
    result = copy.deepcopy(base)
    result["normalized_gradient_tolerance"] = tolerance
    result["stopping"]["normalized_gradient"] = tolerance
    return result


def _function_values(
    theta: torch.Tensor,
    width: int,
    grid: tuple[torch.Tensor, torch.Tensor],
) -> torch.Tensor:
    return scalar_network(theta, grid[0], grid[1], width)[0]


def _relative_distance(left: torch.Tensor, right: torch.Tensor, floor: float) -> float:
    return float(torch.linalg.vector_norm(left - right).item()) / max(
        float(torch.linalg.vector_norm(right).item()), floor
    )


def _suboptimality_estimate(
    objective: Callable[[torch.Tensor], torch.Tensor],
    theta: torch.Tensor,
    local_specification: dict[str, Any],
) -> tuple[dict[str, Any], float | None]:
    diagnostics, gradient, eigenvalues, eigenvectors = exact_state_diagnostics(
        objective, theta, local_specification
    )
    if float(eigenvalues[0].item()) <= 0.0:
        return diagnostics, None
    coordinates = eigenvectors.T @ gradient
    estimate = 0.5 * torch.sum(coordinates.square() / eigenvalues)
    return diagnostics, float(estimate.item())


def _profile_level(
    residual_function: ResidualFunction,
    theta_center: torch.Tensor,
    parameter_center: torch.Tensor,
    gamma: float,
    h_values: list[float],
    local_specification: dict[str, Any],
    accuracy_name: str,
    width: int,
    grid: tuple[torch.Tensor, torch.Tensor],
    branch_specification: dict[str, Any],
) -> tuple[dict[str, Any], dict[float, torch.Tensor]]:
    residual_count = int(residual_function(theta_center, parameter_center).numel())
    center_objective = _mean_residual_objective(
        residual_function, parameter_center, theta_center, gamma, True
    )
    center_loss = float(center_objective(theta_center).item())
    center_diagnostics, center_error = _suboptimality_estimate(
        center_objective, theta_center, local_specification
    )
    floor = float(branch_specification["relative_floor"])
    states: dict[float, torch.Tensor] = {}
    records: dict[float, dict[str, Any]] = {}
    branches: dict[str, list[dict[str, Any]]] = {"negative": [], "positive": []}

    for sign, branch_name in [(-1.0, "negative"), (1.0, "positive")]:
        parent_state: torch.Tensor | None = theta_center
        parent_offset = 0.0
        for h in sorted(h_values):
            offset = sign * h
            parameter = parameter_center + offset * torch.ones_like(parameter_center)
            if parent_state is None:
                record = {
                    "offset": offset,
                    "parent_offset": parent_offset,
                    "branch": branch_name,
                    "status": "NUMERICAL_FAILURE",
                    "failure_reason": "continuation parent failed",
                    "loss_mean": None,
                    "optimization_suboptimality_estimate_mean": None,
                    "weight_parent_relative_distance": None,
                    "function_parent_relative_distance": None,
                    "optimization": None,
                }
            else:
                objective = _mean_residual_objective(
                    residual_function, parameter, theta_center, gamma, True
                )
                optimized, optimization = optimize_state_local_minimum(
                    objective, parent_state, local_specification
                )
                if optimized is None:
                    record = {
                        "offset": offset,
                        "parent_offset": parent_offset,
                        "branch": branch_name,
                        "status": optimization["status"],
                        "failure_reason": optimization["failure_reason"],
                        "loss_mean": None,
                        "optimization_suboptimality_estimate_mean": None,
                        "weight_parent_relative_distance": None,
                        "function_parent_relative_distance": None,
                        "optimization": optimization,
                    }
                else:
                    point_diagnostics, point_error = _suboptimality_estimate(
                        objective, optimized, local_specification
                    )
                    parent_values = _function_values(parent_state, width, grid)
                    current_values = _function_values(optimized, width, grid)
                    record = {
                        "offset": offset,
                        "parent_offset": parent_offset,
                        "branch": branch_name,
                        "status": optimization["status"],
                        "failure_reason": optimization["failure_reason"],
                        "loss_mean": float(objective(optimized).item()),
                        "optimization_suboptimality_estimate_mean": point_error,
                        "weight_parent_relative_distance": _relative_distance(
                            optimized, parent_state, 1.0
                        ),
                        "function_parent_relative_distance": _relative_distance(
                            current_values, parent_values, floor
                        ),
                        "function_distance_alert": (
                            _relative_distance(current_values, parent_values, floor)
                            > float(branch_specification["function_distance_alert"])
                        ),
                        "exact_point_diagnostics": point_diagnostics,
                        "optimization": optimization,
                    }
                    states[offset] = optimized.detach().clone()
                    parent_state = optimized
            records[offset] = record
            branches[branch_name].append(record)
            parent_offset = offset

    estimates = []
    for h in h_values:
        negative = records[-h]
        positive = records[h]
        pair_pass = negative["status"] == "PASS" and positive["status"] == "PASS"
        curvature = (
            residual_count
            * (positive["loss_mean"] - 2.0 * center_loss + negative["loss_mean"])
            / (h * h)
            if pair_pass
            else None
        )
        endpoint_errors = [
            negative["optimization_suboptimality_estimate_mean"],
            center_error,
            positive["optimization_suboptimality_estimate_mean"],
        ]
        curvature_budget = (
            residual_count
            * (endpoint_errors[0] + 2.0 * endpoint_errors[1] + endpoint_errors[2])
            / (h * h)
            if pair_pass and all(value is not None for value in endpoint_errors)
            else None
        )
        estimates.append(
            {
                "h": h,
                "curvature": curvature,
                "pair_status": "PASS" if pair_pass else "NUMERICAL_FAILURE",
                "optimization_curvature_error_estimate": curvature_budget,
                "optimization_curvature_relative_budget": (
                    curvature_budget / max(abs(curvature), 1.0e-8)
                    if curvature_budget is not None and curvature is not None
                    else None
                ),
            }
        )
    points = [records[offset] for offset in sorted(records)]
    return (
        {
            "accuracy_level": accuracy_name,
            "gradient_tolerance": float(
                local_specification["normalized_gradient_tolerance"]
            ),
            "center_loss_mean": center_loss,
            "center_exact_diagnostics": center_diagnostics,
            "center_suboptimality_estimate_mean": center_error,
            "branches": branches,
            "points": points,
            "passed_points": sum(point["status"] == "PASS" for point in points),
            "curvature_estimates": estimates,
            "status": "PASS"
            if len(points) == 8 and all(point["status"] == "PASS" for point in points)
            else "PROFILE_FAILURE",
        },
        states,
    )


def run_resolution_profile(
    residual_function: ResidualFunction,
    theta_center: torch.Tensor,
    parameter_center: torch.Tensor,
    gamma: float,
    local_specification: dict[str, Any],
    profile_specification: dict[str, Any],
    branch_specification: dict[str, Any],
    width: int,
    final_time: float,
) -> dict[str, Any]:
    dtype = theta_center.dtype
    x_axis = torch.linspace(
        0.0, 1.0, int(branch_specification["x_points"]), dtype=dtype
    )
    t_axis = torch.linspace(
        0.0, final_time, int(branch_specification["t_points"]), dtype=dtype
    )
    x_grid, t_grid = torch.meshgrid(x_axis, t_axis, indexing="ij")
    grid = (x_grid.reshape(-1), t_grid.reshape(-1))
    h_values = [float(value) for value in profile_specification["h_values"]]
    levels: dict[str, Any] = {}
    states: dict[str, dict[float, torch.Tensor]] = {}
    for name in ["nominal", "strict"]:
        level, level_states = _profile_level(
            residual_function,
            theta_center,
            parameter_center,
            gamma,
            h_values,
            _local_specification(
                local_specification,
                float(profile_specification["accuracy_levels"][name]),
            ),
            name,
            width,
            grid,
            branch_specification,
        )
        levels[name] = level
        states[name] = level_states

    nominal = {row["h"]: row for row in levels["nominal"]["curvature_estimates"]}
    strict = {row["h"]: row for row in levels["strict"]["curvature_estimates"]}
    floor = float(profile_specification["denominator_absolute_floor"])
    scales = []
    for h in h_values:
        nominal_value = nominal[h]["curvature"]
        strict_value = strict[h]["curvature"]
        accuracy = (
            abs(strict_value - nominal_value) / max(abs(strict_value), floor)
            if strict_value is not None and nominal_value is not None
            else None
        )
        budget = strict[h]["optimization_curvature_relative_budget"]
        points_pass = strict[h]["pair_status"] == "PASS"
        certified = (
            points_pass
            and budget is not None
            and budget
            <= float(profile_specification["optimization_error_relative_tolerance"])
            and accuracy is not None
            and accuracy <= float(profile_specification["accuracy_relative_tolerance"])
        )
        status = (
            "CERTIFIED"
            if certified
            else "RESOLUTION_LIMIT"
            if points_pass
            else "PROFILE_POINT_FAILURE"
        )
        scales.append(
            {
                "h": h,
                "strict_curvature": strict_value,
                "nominal_curvature": nominal_value,
                "optimization_curvature_error_estimate": strict[h][
                    "optimization_curvature_error_estimate"
                ],
                "optimization_curvature_relative_budget": budget,
                "nominal_strict_relative_difference": accuracy,
                "resolution_status": status,
            }
        )

    certified_h = {row["h"] for row in scales if row["resolution_status"] == "CERTIFIED"}
    ascending = sorted(h_values)
    longest = 0
    current = 0
    for h in ascending:
        if h in certified_h:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    required = int(profile_specification["certified_adjacent_scales_required"])
    window_pass = longest >= required

    cross_accuracy = []
    floor_branch = float(branch_specification["relative_floor"])
    for offset in sorted(states["strict"]):
        if offset not in states["nominal"]:
            continue
        strict_values = _function_values(states["strict"][offset], width, grid)
        nominal_values = _function_values(states["nominal"][offset], width, grid)
        cross_accuracy.append(
            {
                "offset": offset,
                "nominal_strict_weight_relative_distance": _relative_distance(
                    states["strict"][offset], states["nominal"][offset], 1.0
                ),
                "nominal_strict_function_relative_distance": _relative_distance(
                    strict_values, nominal_values, floor_branch
                ),
            }
        )
    all_parent_distances = [
        point["function_parent_relative_distance"]
        for level in levels.values()
        for point in level["points"]
        if point["function_parent_relative_distance"] is not None
    ]
    branch_complete = len(cross_accuracy) == 8 and len(all_parent_distances) == 16
    return {
        "role": "FINITE_RADIUS_VALIDATION",
        "gamma": gamma,
        "accuracy_levels": levels,
        "resolution_scales": scales,
        "certified_h_values": sorted(certified_h, reverse=True),
        "longest_adjacent_certified_window": longest,
        "certified_window_gate": "PASS" if window_pass else "FAIL",
        "branch_continuity_audit": {
            "status": "PASS" if branch_complete else "NUMERICAL_FAILURE",
            "grid_shape": [
                int(branch_specification["x_points"]),
                int(branch_specification["t_points"]),
            ],
            "nominal_strict_by_offset": cross_accuracy,
            "maximum_parent_function_relative_distance": max(all_parent_distances)
            if all_parent_distances
            else None,
            "alert_threshold_nonbinding": float(
                branch_specification["function_distance_alert"]
            ),
        },
        "status": "PASS" if window_pass and branch_complete else "PROFILE_FAILURE",
    }
