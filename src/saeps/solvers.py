"""Deterministic matrix-free linear solvers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class CGResult:
    solution: torch.Tensor
    converged: bool
    iterations: int
    absolute_residual: float
    relative_residual: float


def conjugate_gradient(
    operator: Callable[[torch.Tensor], torch.Tensor],
    right_hand_side: torch.Tensor,
    tolerance: float,
    max_iterations: int,
) -> CGResult:
    if right_hand_side.ndim != 1 or not right_hand_side.is_floating_point():
        raise ValueError("right_hand_side must be a floating vector")
    if tolerance <= 0 or max_iterations < 1:
        raise ValueError("invalid CG tolerance or iteration limit")
    solution = torch.zeros_like(right_hand_side)
    right_norm = torch.linalg.vector_norm(right_hand_side)
    denominator = float(right_norm.item()) + 1.0e-30
    if float(right_norm.item()) == 0.0:
        return CGResult(solution, True, 0, 0.0, 0.0)

    residual = right_hand_side - operator(solution)
    direction = residual.clone()
    residual_squared = torch.dot(residual, residual)
    converged = False
    iteration = 0
    for iteration in range(1, max_iterations + 1):
        operator_direction = operator(direction)
        curvature = torch.dot(direction, operator_direction)
        if not torch.isfinite(curvature) or float(curvature.item()) <= 0.0:
            break
        step = residual_squared / curvature
        solution = solution + step * direction
        new_residual = residual - step * operator_direction
        new_residual_squared = torch.dot(new_residual, new_residual)
        relative = float(torch.sqrt(new_residual_squared).item()) / denominator
        residual = new_residual
        if relative <= tolerance:
            converged = True
            residual_squared = new_residual_squared
            break
        beta = new_residual_squared / residual_squared
        direction = residual + beta * direction
        residual_squared = new_residual_squared

    verified_residual = operator(solution) - right_hand_side
    absolute = float(torch.linalg.vector_norm(verified_residual).item())
    relative = absolute / denominator
    converged = converged and relative <= tolerance
    return CGResult(solution, converged, iteration, absolute, relative)

