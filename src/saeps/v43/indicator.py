"""Matrix-free directional form of the first-order reduced correction."""

from __future__ import annotations

from typing import Any, Callable

import torch


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def directional_first_order_correction(
    residual_function: ResidualFunction,
    theta: torch.Tensor,
    parameter: torch.Tensor,
    gamma: float,
) -> dict[str, Any]:
    """Evaluate ``w.T @ (H-J.T@J) @ w`` without forming Hessian blocks."""

    theta_size = theta.numel()
    joint = torch.cat([theta, parameter]).detach()

    def residual_joint(current: torch.Tensor) -> torch.Tensor:
        return residual_function(current[:theta_size], current[theta_size:]).reshape(-1)

    jacobian_theta = torch.func.jacrev(
        lambda current_theta: residual_function(current_theta, parameter).reshape(-1)
    )(theta)
    jacobian_parameter = torch.func.jacrev(
        lambda current_parameter: residual_function(theta, current_parameter).reshape(-1)
    )(parameter)
    identity = torch.eye(theta_size, dtype=theta.dtype, device=theta.device)
    state_solution = torch.linalg.solve(
        jacobian_theta.T @ jacobian_theta + gamma * identity,
        jacobian_theta.T @ jacobian_parameter,
    )
    direction = torch.cat([-state_solution[:, 0], torch.ones(1, dtype=theta.dtype, device=theta.device)])

    def loss_joint(current: torch.Tensor) -> torch.Tensor:
        residual = residual_joint(current)
        return 0.5 * torch.sum(residual.square())

    _, hessian_direction = torch.func.jvp(torch.func.grad(loss_joint), (joint,), (direction,))
    _, residual_direction = torch.func.jvp(residual_joint, (joint,), (direction,))
    hessian_quadratic = torch.dot(direction, hessian_direction)
    gauss_newton_quadratic = torch.dot(residual_direction, residual_direction)
    correction = hessian_quadratic - gauss_newton_quadratic
    return {
        "method": "directional_HVP_minus_directional_GN",
        "forms_full_hessian": False,
        "state_solution_norm": float(torch.linalg.vector_norm(state_solution).item()),
        "joint_direction_norm": float(torch.linalg.vector_norm(direction).item()),
        "hessian_directional_curvature": float(hessian_quadratic.item()),
        "gauss_newton_directional_curvature": float(gauss_newton_quadratic.item()),
        "first_order_reduced_correction": float(correction.item()),
        "hvp_count": 1,
        "residual_jvp_count": 1,
    }

