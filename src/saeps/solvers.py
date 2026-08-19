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


@dataclass(frozen=True)
class LSQRResult:
    solution: torch.Tensor
    converged: bool
    iterations: int
    objective_residual_norm: float
    normal_residual_norm: float
    relative_normal_residual: float


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


def preconditioned_conjugate_gradient(
    operator: Callable[[torch.Tensor], torch.Tensor],
    right_hand_side: torch.Tensor,
    inverse_preconditioner: Callable[[torch.Tensor], torch.Tensor],
    tolerance: float,
    max_iterations: int,
) -> CGResult:
    """Solve an SPD system with verified left-preconditioned CG."""
    if right_hand_side.ndim != 1 or not right_hand_side.is_floating_point():
        raise ValueError("right_hand_side must be a floating vector")
    if tolerance <= 0 or max_iterations < 1:
        raise ValueError("invalid PCG tolerance or iteration limit")
    solution = torch.zeros_like(right_hand_side)
    right_norm = torch.linalg.vector_norm(right_hand_side)
    denominator = float(right_norm.item()) + 1.0e-30
    if float(right_norm.item()) == 0.0:
        return CGResult(solution, True, 0, 0.0, 0.0)

    residual = right_hand_side - operator(solution)
    preconditioned = inverse_preconditioner(residual)
    if preconditioned.shape != residual.shape or not torch.all(torch.isfinite(preconditioned)):
        raise ValueError("inverse preconditioner returned an invalid vector")
    direction = preconditioned.clone()
    residual_preconditioned = torch.dot(residual, preconditioned)
    if float(residual_preconditioned.item()) <= 0.0:
        verified = operator(solution) - right_hand_side
        absolute = float(torch.linalg.vector_norm(verified).item())
        return CGResult(solution, False, 0, absolute, absolute / denominator)

    converged = False
    iteration = 0
    for iteration in range(1, max_iterations + 1):
        operator_direction = operator(direction)
        curvature = torch.dot(direction, operator_direction)
        if not torch.isfinite(curvature) or float(curvature.item()) <= 0.0:
            break
        step = residual_preconditioned / curvature
        solution = solution + step * direction
        residual = residual - step * operator_direction
        relative = float(torch.linalg.vector_norm(residual).item()) / denominator
        if relative <= tolerance:
            converged = True
            break
        next_preconditioned = inverse_preconditioner(residual)
        next_residual_preconditioned = torch.dot(residual, next_preconditioned)
        if (
            not torch.isfinite(next_residual_preconditioned)
            or float(next_residual_preconditioned.item()) <= 0.0
        ):
            break
        beta = next_residual_preconditioned / residual_preconditioned
        direction = next_preconditioned + beta * direction
        preconditioned = next_preconditioned
        residual_preconditioned = next_residual_preconditioned

    verified_residual = operator(solution) - right_hand_side
    absolute = float(torch.linalg.vector_norm(verified_residual).item())
    relative = absolute / denominator
    converged = converged and relative <= tolerance
    return CGResult(solution, converged, iteration, absolute, relative)


def least_squares_qr(
    forward_operator: Callable[[torch.Tensor], torch.Tensor],
    adjoint_operator: Callable[[torch.Tensor], torch.Tensor],
    right_hand_side: torch.Tensor,
    solution_size: int,
    tolerance: float,
    max_iterations: int,
) -> LSQRResult:
    """Golub--Kahan LSQR with a verified normal-residual stopping rule."""
    if right_hand_side.ndim != 1 or not right_hand_side.is_floating_point():
        raise ValueError("right_hand_side must be a floating vector")
    if solution_size < 1 or tolerance <= 0 or max_iterations < 1:
        raise ValueError("invalid LSQR dimensions, tolerance, or iteration limit")

    solution = torch.zeros(
        solution_size,
        dtype=right_hand_side.dtype,
        device=right_hand_side.device,
    )
    beta = torch.linalg.vector_norm(right_hand_side)
    if float(beta.item()) == 0.0:
        return LSQRResult(solution, True, 0, 0.0, 0.0, 0.0)
    left = right_hand_side / beta
    right = adjoint_operator(left)
    if right.shape != solution.shape:
        raise ValueError("adjoint operator returned the wrong shape")
    alpha = torch.linalg.vector_norm(right)
    if float(alpha.item()) == 0.0:
        residual_norm = float(beta.item())
        return LSQRResult(solution, True, 0, residual_norm, 0.0, 0.0)
    right = right / alpha
    direction = right.clone()
    phi_bar = beta
    rho_bar = alpha
    adjoint_rhs_norm = float(torch.linalg.vector_norm(adjoint_operator(right_hand_side)).item())
    denominator = adjoint_rhs_norm + 1.0e-30
    converged = False
    iteration = 0

    for iteration in range(1, max_iterations + 1):
        next_left = forward_operator(right) - alpha * left
        beta = torch.linalg.vector_norm(next_left)
        if float(beta.item()) > 0.0:
            next_left = next_left / beta
        next_right = adjoint_operator(next_left) - beta * right
        alpha = torch.linalg.vector_norm(next_right)
        if float(alpha.item()) > 0.0:
            next_right = next_right / alpha

        rho = torch.sqrt(rho_bar.square() + beta.square())
        if float(rho.item()) == 0.0:
            break
        cosine = rho_bar / rho
        sine = beta / rho
        theta = sine * alpha
        rho_bar = -cosine * alpha
        phi = cosine * phi_bar
        phi_bar = sine * phi_bar
        solution = solution + (phi / rho) * direction
        direction = next_right - (theta / rho) * direction
        left = next_left
        right = next_right

        residual = forward_operator(solution) - right_hand_side
        normal_residual = adjoint_operator(residual)
        relative = float(torch.linalg.vector_norm(normal_residual).item()) / denominator
        if relative <= tolerance:
            converged = True
            break

    verified_residual = forward_operator(solution) - right_hand_side
    verified_normal = adjoint_operator(verified_residual)
    residual_norm = float(torch.linalg.vector_norm(verified_residual).item())
    normal_norm = float(torch.linalg.vector_norm(verified_normal).item())
    relative = normal_norm / denominator
    return LSQRResult(
        solution,
        converged and relative <= tolerance,
        iteration,
        residual_norm,
        normal_norm,
        relative,
    )
