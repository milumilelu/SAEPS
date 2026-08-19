"""P3 acceptance validation on a nonlinear-optimization profile with known curvature."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import torch

from saeps.config import config_hash, load_config
from saeps.profile import (
    ProfileFitError,
    ProfilePoint,
    compare_curvature,
    estimate_curvature,
    estimate_profile_minimum,
    fit_local_quadratic,
    profile_frozen,
    profile_reoptimized,
)
from saeps.provenance import environment_provenance, make_run_id
from saeps.seed import set_deterministic_seed


def _synthetic_problem(dtype: torch.dtype) -> tuple[Any, torch.Tensor, torch.Tensor, torch.Tensor, float, float]:
    state_metric = torch.tensor([[3.0, 0.4], [0.4, 2.0]], dtype=dtype)
    absorption = torch.tensor([0.7, -0.4], dtype=dtype)
    known_curvature = 1.6
    known_minimum = 0.03

    def objective(theta: torch.Tensor, coordinate: torch.Tensor) -> torch.Tensor:
        q = coordinate[0]
        displacement = theta - absorption * q
        return (
            0.5 * displacement @ state_metric @ displacement
            + 0.5 * known_curvature * (q - known_minimum) ** 2
            + 0.2
        )

    theta0 = torch.zeros(2, dtype=dtype)
    coordinate0 = torch.zeros(1, dtype=dtype)
    direction = torch.ones(1, dtype=dtype)
    raw_curvature = known_curvature + float((absorption @ state_metric @ absorption).item())
    return objective, theta0, coordinate0, direction, known_curvature, raw_curvature


def _max_point_difference(first: list[ProfilePoint], second: list[ProfilePoint]) -> float:
    first_map = {point.offset: point for point in first}
    second_map = {point.offset: point for point in second}
    if set(first_map) != set(second_map):
        return float("inf")
    return max(
        abs(float(first_map[offset].loss) - float(second_map[offset].loss))
        for offset in first_map
        if first_map[offset].loss is not None and second_map[offset].loss is not None
    )


def run_profile_validation(
    config_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
    *,
    write_output: bool = True,
) -> dict[str, Any]:
    started = time.perf_counter()
    config = load_config(config_path)
    if config.get("phase") != "P3" or config.get("dtype") != "float64":
        raise ValueError("P3 acceptance requires the locked float64 P3 config")
    set_deterministic_seed(20260819)
    dtype = getattr(torch, config["dtype"])
    objective, theta0, coordinate0, direction, known_curvature, raw_curvature = _synthetic_problem(dtype)
    offsets = [float(value) for value in config["profile_points"]]
    frozen = profile_frozen(objective, theta0, coordinate0, direction, offsets)
    reoptimized = profile_reoptimized(
        objective, theta0, coordinate0, direction, offsets, config["optimizer"], config["stopping"]
    )
    frozen_fit = fit_local_quadratic(frozen, config["fit_quality"], offsets)
    reoptimized_fit = fit_local_quadratic(reoptimized, config["fit_quality"], offsets)

    permuted_offsets = [offsets[index] for index in [4, 0, 6, 2, 5, 1, 3]]
    permuted = profile_reoptimized(
        objective, theta0, coordinate0, direction, permuted_offsets, config["optimizer"], config["stopping"]
    )
    repeated = profile_reoptimized(
        objective, theta0, coordinate0, direction, offsets, config["optimizer"], config["stopping"]
    )
    order_error = _max_point_difference(reoptimized, permuted)
    reproducibility_error = _max_point_difference(reoptimized, repeated)

    failure_optimizer = dict(config["optimizer"])
    failure_optimizer["outer_steps_max"] = 1
    forced_failure = profile_reoptimized(
        objective, theta0, coordinate0, direction, [0.1], failure_optimizer, config["stopping"]
    )
    missing_rejected = False
    try:
        fit_local_quadratic(
            [*reoptimized[:2], forced_failure[0], *reoptimized[3:]],
            config["fit_quality"],
            offsets,
        )
    except ProfileFitError:
        missing_rejected = True

    acceptance = config["acceptance"]
    curvature_error = abs(estimate_curvature(reoptimized_fit) - known_curvature) / known_curvature
    frozen_error = abs(estimate_curvature(frozen_fit) - raw_curvature) / raw_curvature
    minimum_error = abs(estimate_profile_minimum(reoptimized_fit) - 0.03)
    checks = {
        "all_reoptimized_points_pass": all(point.status == "PASS" for point in reoptimized),
        "known_reoptimized_curvature": curvature_error
        <= float(acceptance["known_curvature_relative_error"]),
        "known_frozen_curvature": frozen_error
        <= float(acceptance["known_curvature_relative_error"]),
        "known_minimum": minimum_error <= float(acceptance["known_minimum_absolute_error"]),
        "point_order_invariance": order_error
        <= float(acceptance["order_invariance_absolute_tolerance"]),
        "independent_initialization_reproducibility": reproducibility_error
        <= float(acceptance["reproducibility_absolute_tolerance"]),
        "failed_point_status": forced_failure[0].status == "PROFILE_FAILURE",
        "missing_point_not_interpolated": missing_rejected,
        "combined_stopping_rule": all(
            point.optimizer_terminated and point.loss_plateau and point.gradient_converged
            for point in reoptimized
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    provenance = environment_provenance(repo_root, config["dtype"], "cpu")
    digest = config_hash(config)
    run_id = make_run_id("P3-profile", 20260819, digest, provenance["timestamp"])
    result = {
        "schema_version": 1,
        "phase": "P3",
        "run_id": run_id,
        "status": status,
        "config_hash": digest,
        "known": {"reoptimized_curvature": known_curvature, "frozen_curvature": raw_curvature, "minimum": 0.03},
        "estimated": {
            "reoptimized_curvature": reoptimized_fit.curvature,
            "frozen_curvature": frozen_fit.curvature,
            "minimum": reoptimized_fit.minimum,
            "reoptimized_r_squared": reoptimized_fit.r_squared,
            "reoptimized_normalized_rmse": reoptimized_fit.normalized_rmse,
        },
        "errors": {
            "reoptimized_curvature_relative": curvature_error,
            "frozen_curvature_relative": frozen_error,
            "minimum_absolute": minimum_error,
            "order_invariance_max_absolute": order_error,
            "reproducibility_max_absolute": reproducibility_error,
        },
        "comparison_example": compare_curvature(known_curvature, raw_curvature, reoptimized_fit.curvature),
        "points": [
            {
                "offset": point.offset,
                "loss": point.loss,
                "status": point.status,
                "outer_steps": point.outer_steps,
                "closure_calls": point.closure_calls,
                "normalized_gradient": point.normalized_gradient,
                "relative_loss_change": point.relative_loss_change,
            }
            for point in reoptimized
        ],
        "forced_failure": {"status": forced_failure[0].status, "failure_reason": forced_failure[0].failure_reason},
        "checks": checks,
        "provenance": provenance,
        "elapsed_seconds": time.perf_counter() - started,
    }
    if write_output:
        destination = Path(output_root) / run_id
        destination.mkdir(parents=True, exist_ok=False)
        with (destination / "result.json").open("w", encoding="utf-8") as stream:
            json.dump(result, stream, allow_nan=False, indent=2, sort_keys=True)
            stream.write("\n")
    if status != "PASS":
        raise RuntimeError(f"P3 validation failed: {[name for name, passed in checks.items() if not passed]}")
    return result

