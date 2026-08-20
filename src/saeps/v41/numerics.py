"""Separated numerical references and gate graph for v4.1."""

from __future__ import annotations

import math
from typing import Any

import torch


def _augmented_matrix(jacobian_theta: torch.Tensor, gamma: float) -> torch.Tensor:
    return torch.cat(
        [
            jacobian_theta,
            math.sqrt(gamma)
            * torch.eye(
                jacobian_theta.shape[1],
                dtype=jacobian_theta.dtype,
                device=jacobian_theta.device,
            ),
        ],
        dim=0,
    )


def explicit_curvature_reference(
    jacobian_theta: torch.Tensor,
    jacobian_parameter: torch.Tensor,
    gamma: float,
    relative_normal_tolerance: float = 1.0e-10,
    identity_tolerance: float = 1.0e-10,
) -> dict[str, Any]:
    """Direct reference using only the binding parameter-curvature RHS."""

    augmented = _augmented_matrix(jacobian_theta, gamma)
    rhs = torch.cat(
        [
            jacobian_parameter,
            torch.zeros(
                jacobian_theta.shape[1],
                jacobian_parameter.shape[1],
                dtype=jacobian_parameter.dtype,
                device=jacobian_parameter.device,
            ),
        ],
        dim=0,
    )
    solution = torch.linalg.lstsq(augmented, rhs, driver="gelsd").solution
    residual = augmented @ solution - rhs
    normal = augmented.T @ residual
    normal_rhs = augmented.T @ rhs
    relative_normal = float(torch.linalg.vector_norm(normal).item()) / max(
        float(torch.linalg.vector_norm(normal_rhs).item()), 1.0e-30
    )
    curvature = residual.T @ residual
    projection = jacobian_parameter.T @ (
        jacobian_parameter - jacobian_theta @ solution
    )
    identity_error = float(torch.linalg.matrix_norm(curvature - projection).item()) / max(
        float(torch.linalg.matrix_norm(curvature).item()), 1.0e-30
    )
    passed = relative_normal <= relative_normal_tolerance and identity_error <= identity_tolerance
    singular = torch.linalg.svdvals(augmented)
    return {
        "parameter_reference_status": "PASS" if passed else "NUMERICAL_FAILURE",
        "binding": True,
        "rhs": "J_lambda_only",
        "Fse_explicit": float(curvature[0, 0].item()),
        "relative_normal_residual": relative_normal,
        "objective_projection_identity_relative_error": identity_error,
        "singular_value_minimum": float(singular.min().item()),
        "singular_value_maximum": float(singular.max().item()),
    }


def explicit_score_diagnostic(
    jacobian_theta: torch.Tensor,
    residual_vector: torch.Tensor,
    gamma: float,
    relative_normal_tolerance: float = 1.0e-10,
) -> dict[str, Any]:
    """Independent nonbinding residual/score RHS diagnostic."""

    augmented = _augmented_matrix(jacobian_theta, gamma)
    rhs = torch.cat(
        [residual_vector.reshape(-1, 1), torch.zeros(jacobian_theta.shape[1], 1, dtype=residual_vector.dtype, device=residual_vector.device)],
        dim=0,
    )
    solution = torch.linalg.lstsq(augmented, rhs, driver="gelsd").solution
    augmented_residual = augmented @ solution - rhs
    relative_normal = float(torch.linalg.vector_norm(augmented.T @ augmented_residual).item()) / max(
        float(torch.linalg.vector_norm(augmented.T @ rhs).item()), 1.0e-30
    )
    return {
        "score_solver_status": "PASS" if relative_normal <= relative_normal_tolerance else "SOLVER_FAILURE",
        "binding": False,
        "rhs": "residual_score_only",
        "relative_normal_residual": relative_normal,
    }


def binding_curvature_gate(
    parameter_reference_status: str,
    curvature_solver_status: str,
    score_solver_status: str,
) -> dict[str, Any]:
    passed = parameter_reference_status == "PASS" and curvature_solver_status == "PASS"
    return {
        "CURVATURE_GATE": "PASS" if passed else "SOLVER_FAILURE",
        "binding_inputs": {
            "parameter_reference_status": parameter_reference_status,
            "curvature_solver_status": curvature_solver_status,
        },
        "nonbinding_diagnostics": {"score_solver_status": score_solver_status},
    }

