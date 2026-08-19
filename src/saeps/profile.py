"""Benchmark-independent nonlinear frozen and state-reoptimized profiles."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import torch


Objective = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


class ProfileFitError(RuntimeError):
    """Raised when a profile is incomplete or fails locked fit-quality rules."""


@dataclass(frozen=True)
class ProfilePoint:
    offset: float
    coordinate: torch.Tensor
    loss: float | None
    status: str
    failure_reason: str | None
    theta: torch.Tensor | None
    outer_steps: int
    closure_calls: int
    normalized_gradient: float | None
    relative_loss_change: float | None
    optimizer_terminated: bool
    loss_plateau: bool
    gradient_converged: bool


@dataclass(frozen=True)
class QuadraticFit:
    intercept: float
    slope: float
    curvature: float
    minimum: float
    r_squared: float
    normalized_rmse: float
    design_condition: float
    offsets: tuple[float, ...]
    losses: tuple[float, ...]


def _validate_direction(coordinate: torch.Tensor, direction: torch.Tensor) -> None:
    if coordinate.ndim != 1 or direction.shape != coordinate.shape:
        raise ValueError("coordinate and direction must be equal-shaped vectors")
    if coordinate.dtype != direction.dtype or coordinate.device != direction.device:
        raise ValueError("coordinate and direction must share dtype and device")
    if not torch.all(torch.isfinite(coordinate)) or not torch.all(torch.isfinite(direction)):
        raise ValueError("coordinate or direction contains non-finite values")
    if float(torch.linalg.vector_norm(direction).item()) == 0.0:
        raise ValueError("profile direction must be nonzero")


def profile_frozen(
    objective: Objective,
    theta0: torch.Tensor,
    coordinate0: torch.Tensor,
    direction: torch.Tensor,
    offsets: Sequence[float],
) -> list[ProfilePoint]:
    _validate_direction(coordinate0, direction)
    results: list[ProfilePoint] = []
    for offset in offsets:
        coordinate = coordinate0 + float(offset) * direction
        try:
            value = objective(theta0, coordinate)
            if value.ndim != 0 or not torch.isfinite(value):
                raise ValueError("objective must return a finite scalar")
            results.append(
                ProfilePoint(
                    float(offset), coordinate.detach().clone(), float(value.item()), "PASS", None,
                    theta0.detach().clone(), 0, 0, None, None, True, True, True
                )
            )
        except Exception as error:
            results.append(
                ProfilePoint(
                    float(offset), coordinate.detach().clone(), None, "PROFILE_FAILURE",
                    f"{type(error).__name__}: {error}", None, 0, 0, None, None, False, False, False
                )
            )
    return results


def _normalized_gradient(loss: torch.Tensor, state: torch.Tensor) -> float:
    gradient = torch.autograd.grad(loss, state)[0]
    scale = max(float(torch.linalg.vector_norm(state).item()), 1.0)
    return float(torch.linalg.vector_norm(gradient).item()) / scale


def _reoptimize_point(
    objective: Objective,
    theta0: torch.Tensor,
    coordinate: torch.Tensor,
    offset: float,
    optimizer_config: dict[str, Any],
    stopping: dict[str, Any],
) -> ProfilePoint:
    state = torch.nn.Parameter(theta0.detach().clone())
    optimizer = torch.optim.LBFGS(
        [state],
        max_iter=int(optimizer_config["inner_iterations"]),
        history_size=int(optimizer_config["history_size"]),
        tolerance_grad=float(optimizer_config["tolerance_grad"]),
        tolerance_change=float(optimizer_config["tolerance_change"]),
        line_search_fn=str(optimizer_config["line_search"]),
    )
    closure_calls = 0
    outer_losses: list[float] = []
    optimizer_terminated = False
    try:
        for outer_step in range(1, int(optimizer_config["outer_steps_max"]) + 1):
            def closure() -> torch.Tensor:
                nonlocal closure_calls
                closure_calls += 1
                optimizer.zero_grad(set_to_none=True)
                value = objective(state, coordinate)
                if value.ndim != 0 or not torch.isfinite(value):
                    raise ValueError("objective must return a finite scalar")
                value.backward()
                return value

            optimizer.step(closure)
            optimizer_terminated = True
            value = objective(state, coordinate)
            if value.ndim != 0 or not torch.isfinite(value):
                raise ValueError("objective must return a finite scalar")
            loss_value = float(value.item())
            outer_losses.append(loss_value)
            gradient = _normalized_gradient(value, state)
            window = int(stopping["plateau_window"])
            plateau = False
            relative_change: float | None = None
            if len(outer_losses) >= window:
                recent = outer_losses[-window:]
                changes = [abs(recent[index + 1] - recent[index]) for index in range(len(recent) - 1)]
                relative_change = max(changes, default=0.0) / max(abs(recent[-1]), 1.0)
                plateau = relative_change <= float(stopping["relative_loss_change"])
            gradient_ok = gradient <= float(stopping["normalized_gradient"])
            if (
                outer_step >= int(stopping["minimum_outer_steps"])
                and optimizer_terminated
                and plateau
                and gradient_ok
            ):
                return ProfilePoint(
                    offset, coordinate.detach().clone(), loss_value, "PASS", None,
                    state.detach().clone(), outer_step, closure_calls, gradient,
                    relative_change, True, True, True
                )
        final_value = objective(state, coordinate)
        final_gradient = _normalized_gradient(final_value, state)
        window = int(stopping["plateau_window"])
        recent = outer_losses[-window:]
        changes = [abs(recent[index + 1] - recent[index]) for index in range(len(recent) - 1)]
        relative_change = max(changes, default=float("inf")) / max(abs(outer_losses[-1]), 1.0)
        plateau = len(outer_losses) >= window and relative_change <= float(stopping["relative_loss_change"])
        gradient_ok = final_gradient <= float(stopping["normalized_gradient"])
        return ProfilePoint(
            offset, coordinate.detach().clone(), float(final_value.item()), "PROFILE_FAILURE",
            "combined optimizer/plateau/gradient stopping rule not satisfied", state.detach().clone(),
            len(outer_losses), closure_calls, final_gradient, relative_change,
            optimizer_terminated, plateau, gradient_ok
        )
    except Exception as error:
        return ProfilePoint(
            offset, coordinate.detach().clone(), None, "PROFILE_FAILURE",
            f"{type(error).__name__}: {error}", None, len(outer_losses), closure_calls,
            None, None, optimizer_terminated, False, False
        )


def profile_reoptimized(
    objective: Objective,
    theta0: torch.Tensor,
    coordinate0: torch.Tensor,
    direction: torch.Tensor,
    offsets: Sequence[float],
    optimizer_config: dict[str, Any],
    stopping: dict[str, Any],
) -> list[ProfilePoint]:
    _validate_direction(coordinate0, direction)
    if theta0.ndim != 1 or not theta0.is_floating_point():
        raise ValueError("theta0 must be a floating vector")
    return [
        _reoptimize_point(
            objective,
            theta0,
            coordinate0 + float(offset) * direction,
            float(offset),
            optimizer_config,
            stopping,
        )
        for offset in offsets
    ]


def fit_local_quadratic(
    points: Sequence[ProfilePoint],
    fit_quality: dict[str, Any],
    expected_offsets: Sequence[float] | None = None,
) -> QuadraticFit:
    if len(points) < 3:
        raise ProfileFitError("at least three profile points are required")
    if any(point.status != "PASS" or point.loss is None for point in points):
        raise ProfileFitError("profile contains failed or missing points; interpolation is forbidden")
    offsets = [point.offset for point in points]
    if len(set(offsets)) != len(offsets):
        raise ProfileFitError("profile contains duplicate offsets")
    if expected_offsets is not None and sorted(offsets) != sorted(float(value) for value in expected_offsets):
        raise ProfileFitError("profile offsets do not match the complete expected set")
    dtype = points[0].coordinate.dtype
    x = torch.tensor(offsets, dtype=dtype)
    y = torch.tensor([float(point.loss) for point in points], dtype=dtype)
    design = torch.stack([torch.ones_like(x), x, 0.5 * x.square()], dim=1)
    coefficients = torch.linalg.lstsq(design, y).solution
    prediction = design @ coefficients
    residual = y - prediction
    total = y - y.mean()
    residual_sum = torch.dot(residual, residual)
    total_sum = torch.dot(total, total)
    r_squared = 1.0 if float(total_sum.item()) == 0.0 else 1.0 - float((residual_sum / total_sum).item())
    normalized_rmse = float(torch.sqrt(torch.mean(residual.square())).item()) / max(
        float(torch.max(y).item() - torch.min(y).item()), torch.finfo(dtype).eps
    )
    condition = float(torch.linalg.cond(design).item())
    curvature = float(coefficients[2].item())
    slope = float(coefficients[1].item())
    if r_squared < float(fit_quality["minimum_r_squared"]):
        raise ProfileFitError(f"quadratic R^2 {r_squared} below locked threshold")
    if normalized_rmse > float(fit_quality["maximum_normalized_rmse"]):
        raise ProfileFitError("quadratic normalized RMSE exceeds locked threshold")
    if condition > float(fit_quality["maximum_design_condition"]):
        raise ProfileFitError("quadratic design condition exceeds locked threshold")
    if bool(fit_quality["positive_curvature_required"]) and curvature <= 0.0:
        raise ProfileFitError("quadratic curvature is not positive")
    minimum = -slope / curvature
    order = sorted(range(len(offsets)), key=lambda index: offsets[index])
    return QuadraticFit(
        float(coefficients[0].item()), slope, curvature, minimum, r_squared,
        normalized_rmse, condition, tuple(offsets[index] for index in order),
        tuple(float(y[index].item()) for index in order)
    )


def estimate_curvature(fit: QuadraticFit) -> float:
    return fit.curvature


def estimate_profile_minimum(fit: QuadraticFit) -> float:
    return fit.minimum


def compare_curvature(
    saeps_curvature: float, raw_curvature: float, profile_curvature: float, epsilon: float = 1.0e-30
) -> dict[str, float]:
    denominator = abs(profile_curvature) + epsilon
    return {
        "E_saeps": abs(saeps_curvature - profile_curvature) / denominator,
        "E_raw": abs(raw_curvature - profile_curvature) / denominator,
        "D_paired": (
            abs(raw_curvature - profile_curvature)
            - abs(saeps_curvature - profile_curvature)
        )
        / denominator,
    }

