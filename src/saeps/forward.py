"""Independent periodic finite-difference reference solvers for scalar screening."""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class ForwardSolution:
    values: torch.Tensor
    spatial_points: int
    time_steps: int
    final_time: float
    benchmark: str
    parameter: float


def _spatial_derivatives(state: torch.Tensor, spacing: float) -> tuple[torch.Tensor, torch.Tensor]:
    left = torch.roll(state, 1)
    right = torch.roll(state, -1)
    first = (right - left) / (2.0 * spacing)
    second = (right - 2.0 * state + left) / spacing**2
    return first, second


def solve_periodic_scalar(
    benchmark: str,
    parameter: float,
    spatial_points: int = 128,
    time_steps: int = 2000,
    final_time: float = 0.4,
    dtype: torch.dtype = torch.float64,
    allen_cahn_diffusion: float = 0.01,
) -> ForwardSolution:
    if parameter <= 0.0 or spatial_points < 8 or time_steps < 1 or final_time <= 0.0:
        raise ValueError("invalid forward-solver input")
    x = torch.arange(spatial_points, dtype=dtype) / spatial_points
    if benchmark == "Burgers":
        state = torch.sin(2.0 * torch.pi * x)
    elif benchmark == "Allen-Cahn":
        state = 0.5 * torch.sin(2.0 * torch.pi * x)
    else:
        raise ValueError(f"unknown scalar benchmark: {benchmark}")
    spacing = 1.0 / spatial_points
    step = final_time / time_steps
    history = torch.empty((time_steps + 1, spatial_points), dtype=dtype)
    history[0] = state

    def right_hand_side(current: torch.Tensor) -> torch.Tensor:
        first, second = _spatial_derivatives(current, spacing)
        if benchmark == "Burgers":
            return -current * first + parameter * second
        return allen_cahn_diffusion * second + parameter * (current - current**3)

    for index in range(1, time_steps + 1):
        k1 = right_hand_side(state)
        k2 = right_hand_side(state + 0.5 * step * k1)
        k3 = right_hand_side(state + 0.5 * step * k2)
        k4 = right_hand_side(state + step * k3)
        state = state + step * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
        if not torch.all(torch.isfinite(state)):
            raise RuntimeError(f"{benchmark} forward solution became non-finite at step {index}")
        history[index] = state
    return ForwardSolution(history, spatial_points, time_steps, final_time, benchmark, float(parameter))


def interpolate_solution(
    solution: ForwardSolution, x: torch.Tensor, t: torch.Tensor
) -> torch.Tensor:
    if x.shape != t.shape or x.dtype != solution.values.dtype:
        raise ValueError("query x/t must share shape and solution dtype")
    if torch.any(t < 0.0) or torch.any(t > solution.final_time):
        raise ValueError("query time lies outside solution interval")
    spatial = torch.remainder(x, 1.0) * solution.spatial_points
    x0 = torch.floor(spatial).to(torch.long) % solution.spatial_points
    x1 = (x0 + 1) % solution.spatial_points
    wx = spatial - torch.floor(spatial)
    temporal = t / solution.final_time * solution.time_steps
    t0 = torch.floor(temporal).to(torch.long).clamp(max=solution.time_steps)
    t1 = (t0 + 1).clamp(max=solution.time_steps)
    wt = temporal - torch.floor(temporal)
    lower = (1.0 - wx) * solution.values[t0, x0] + wx * solution.values[t0, x1]
    upper = (1.0 - wx) * solution.values[t1, x0] + wx * solution.values[t1, x1]
    return (1.0 - wt) * lower + wt * upper

