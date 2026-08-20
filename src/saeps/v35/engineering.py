"""V3.5 center rescue and augmented scaled-LSQR candidates."""

from __future__ import annotations

import copy
import math
from typing import Any, Callable

import torch

from saeps.autodiff import ResidualLinearization
from saeps.solvers import least_squares_qr
from saeps.v31.local_minimum import optimize_state_local_minimum


def center_with_registered_rescue(
    objective: Callable[[torch.Tensor], torch.Tensor],
    theta0: torch.Tensor,
    local_specification: dict[str, Any],
    enhanced_specification: dict[str, Any],
) -> tuple[torch.Tensor | None, dict[str, Any]]:
    baseline_state, baseline = optimize_state_local_minimum(
        objective, theta0, local_specification
    )
    if baseline_state is not None:
        return baseline_state, {
            "selected_method": "baseline_v3_4_exact_trust",
            "baseline": baseline,
            "enhanced": None,
            "status": "PASS",
        }
    enhanced_local = copy.deepcopy(local_specification)
    enhanced_local["maximum_escape_cycles"] = int(
        local_specification["maximum_escape_cycles"]
    ) + int(enhanced_specification["maximum_rescue_steps"])
    enhanced_local["trust_initial_relative_radius"] = float(
        enhanced_specification["initial_relative_radius"]
    )
    enhanced_local["trust_minimum_relative_radius"] = float(
        enhanced_specification["minimum_relative_radius"]
    )
    enhanced_local["trust_maximum_relative_radius"] = float(
        enhanced_specification["maximum_relative_radius"]
    )
    enhanced_state, enhanced = optimize_state_local_minimum(
        objective, theta0, enhanced_local
    )
    return enhanced_state, {
        "selected_method": "enhanced_extended_exact_trust"
        if enhanced_state is not None
        else None,
        "baseline": baseline,
        "enhanced": enhanced,
        "status": "PASS" if enhanced_state is not None else "NUMERICAL_FAILURE",
    }


def scaled_augmented_lsqr_candidates(
    linearization: ResidualLinearization,
    parameter_column: torch.Tensor,
    gamma: float,
    tolerance: float,
    max_iterations: int,
    refinement_passes: int,
) -> dict[str, Any]:
    state_size = linearization.theta.numel()
    residual_size = parameter_column.numel()
    square_root_gamma = math.sqrt(gamma)
    diagonal = torch.zeros_like(linearization.theta)
    basis = torch.eye(
        state_size,
        dtype=linearization.theta.dtype,
        device=linearization.theta.device,
    )
    for index, column in enumerate(basis):
        product = linearization.jvp_theta(column)
        diagonal[index] = torch.dot(product, product) + gamma
    scale = torch.sqrt(diagonal)

    def forward_unscaled(vector: torch.Tensor) -> torch.Tensor:
        return torch.cat(
            [linearization.jvp_theta(vector), square_root_gamma * vector]
        )

    def adjoint_unscaled(vector: torch.Tensor) -> torch.Tensor:
        return (
            linearization.vjp_theta(vector[:residual_size])
            + square_root_gamma * vector[residual_size:]
        )

    def forward_scaled(vector: torch.Tensor) -> torch.Tensor:
        return forward_unscaled(vector / scale)

    def adjoint_scaled(vector: torch.Tensor) -> torch.Tensor:
        return adjoint_unscaled(vector) / scale

    right_hand_side = torch.cat(
        [parameter_column, torch.zeros_like(linearization.theta)]
    )
    normal_rhs_norm = float(
        torch.linalg.vector_norm(adjoint_unscaled(right_hand_side)).item()
    ) + 1.0e-30

    def solve_correction(rhs: torch.Tensor) -> Any:
        return least_squares_qr(
            forward_scaled,
            adjoint_scaled,
            rhs,
            state_size,
            tolerance,
            max_iterations,
        )

    initial = solve_correction(right_hand_side)
    solution = initial.solution / scale

    def audit(current: torch.Tensor) -> tuple[float, float]:
        augmented_residual = forward_unscaled(current) - right_hand_side
        relative_normal = float(
            torch.linalg.vector_norm(adjoint_unscaled(augmented_residual)).item()
        ) / normal_rhs_norm
        curvature = float(torch.dot(augmented_residual, augmented_residual).item())
        return relative_normal, curvature

    initial_residual, initial_curvature = audit(solution)
    refinement_rows = []
    total_iterations = int(initial.iterations)
    for refinement in range(refinement_passes):
        residual_rhs = right_hand_side - forward_unscaled(solution)
        correction = solve_correction(residual_rhs)
        solution = solution + correction.solution / scale
        total_iterations += int(correction.iterations)
        verified, curvature = audit(solution)
        refinement_rows.append(
            {
                "pass_index": refinement + 1,
                "iterations": correction.iterations,
                "scaled_normal_residual": correction.relative_normal_residual,
                "verified_original_relative_normal_residual": verified,
                "Fse": curvature,
            }
        )
    final_residual, final_curvature = audit(solution)
    return {
        "scaling": "exact development diag(Jtheta^T Jtheta + gamma I) via JVP basis",
        "setup_jvp_count": state_size,
        "scaled_LSQR": {
            "Fse": initial_curvature,
            "iterations": initial.iterations,
            "verified_original_relative_normal_residual": initial_residual,
        },
        "scaled_LSQR_iterative_refinement": {
            "Fse": final_curvature,
            "total_iterations": total_iterations,
            "verified_original_relative_normal_residual": final_residual,
            "passes": refinement_rows,
        },
    }

