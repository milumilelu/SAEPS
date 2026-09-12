"""Analytic identifiability references and small SAEPS counterexamples.

The routines in this namespace deliberately use finite dimensional residual
Jacobians and the closed form heat-equation solution.  They do not depend on a
PINN checkpoint, so they provide an independent reference for regression
tests and for the identifiability pilot.
"""

from __future__ import annotations

from typing import Any

import torch


def finite_gamma_reduced_curvature(
    jacobian_state: torch.Tensor,
    jacobian_parameter: torch.Tensor,
    gamma: float,
) -> torch.Tensor:
    """Return ``Jp.T [I-Jw(Jw.T Jw+gamma I)^-1 Jw.T] Jp``.

    ``jacobian_state`` may have zero columns; in that case no state is
    eliminated and the result is the raw physical-parameter curvature.
    """

    if gamma <= 0:
        raise ValueError("gamma must be positive")
    if jacobian_state.ndim != 2 or jacobian_parameter.ndim != 2:
        raise ValueError("Jacobians must be matrices")
    if jacobian_state.shape[0] != jacobian_parameter.shape[0]:
        raise ValueError("Jacobians must have the same residual dimension")
    residual_dim = jacobian_parameter.shape[0]
    identity = torch.eye(
        residual_dim, dtype=jacobian_parameter.dtype, device=jacobian_parameter.device
    )
    if jacobian_state.shape[1] == 0:
        operator = identity
    else:
        normal = jacobian_state.T @ jacobian_state
        normal = normal + float(gamma) * torch.eye(
            jacobian_state.shape[1], dtype=jacobian_state.dtype, device=jacobian_state.device
        )
        operator = identity - jacobian_state @ torch.linalg.solve(normal, jacobian_state.T)
    return jacobian_parameter.T @ operator @ jacobian_parameter


def exact_zero_damping_curvature(
    jacobian_state: torch.Tensor,
    jacobian_parameter: torch.Tensor,
    relative_tolerance: float = 1.0e-12,
) -> torch.Tensor:
    """Curvature after unrestricted linear state adaptation (SVD projector)."""

    if relative_tolerance <= 0:
        raise ValueError("relative_tolerance must be positive")
    if jacobian_state.ndim != 2 or jacobian_parameter.ndim != 2:
        raise ValueError("Jacobians must be matrices")
    if jacobian_state.shape[0] != jacobian_parameter.shape[0]:
        raise ValueError("Jacobians must have the same residual dimension")
    if jacobian_state.shape[1] == 0:
        return jacobian_parameter.T @ jacobian_parameter
    left, singular_values, _ = torch.linalg.svd(jacobian_state, full_matrices=False)
    rank = 0
    if singular_values.numel():
        cutoff = float(relative_tolerance) * float(singular_values[0].item())
        rank = int(torch.count_nonzero(singular_values > cutoff).item())
    identity = torch.eye(
        jacobian_state.shape[0], dtype=jacobian_state.dtype, device=jacobian_state.device
    )
    if rank:
        basis = left[:, :rank]
        identity = identity - basis @ basis.T
    return jacobian_parameter.T @ identity @ jacobian_parameter


def heat_temperature(
    x: torch.Tensor,
    t: torch.Tensor,
    k: float | torch.Tensor,
    C: float | torch.Tensor,
    amplitude: float | torch.Tensor = 1.0,
) -> torch.Tensor:
    """Single-mode solution ``a sin(pi x) exp(-pi^2 (k/C) t)``."""

    k_value = torch.as_tensor(k, dtype=x.dtype, device=x.device)
    c_value = torch.as_tensor(C, dtype=x.dtype, device=x.device)
    a_value = torch.as_tensor(amplitude, dtype=x.dtype, device=x.device)
    return a_value * torch.sin(torch.pi * x) * torch.exp(-torch.pi**2 * (k_value / c_value) * t)


def heat_temperature_sensitivities(
    x: torch.Tensor,
    t: torch.Tensor,
    k: float,
    C: float,
    amplitude: float = 1.0,
) -> torch.Tensor:
    """Analytic observation sensitivities with columns ``(k, C, amplitude)``."""

    if k <= 0 or C <= 0:
        raise ValueError("k and C must be positive")
    if amplitude == 0:
        raise ValueError("amplitude must be non-zero for its relative derivative")
    temperature = heat_temperature(x, t, k, C, amplitude)
    pi2_t = torch.pi**2 * t
    d_k = temperature * (-pi2_t / float(C))
    d_C = temperature * (pi2_t * float(k) / float(C) ** 2)
    d_a = temperature / float(amplitude)
    return torch.stack((d_k, d_C, d_a), dim=-1)


def numerical_rank(matrix: torch.Tensor, relative_tolerance: float = 1.0e-10) -> int:
    """SVD rank using a scale-relative cutoff."""

    if matrix.ndim != 2:
        raise ValueError("matrix must be two-dimensional")
    if relative_tolerance <= 0:
        raise ValueError("relative_tolerance must be positive")
    singular_values = torch.linalg.svdvals(matrix)
    if singular_values.numel() == 0 or float(singular_values[0].item()) == 0.0:
        return 0
    cutoff = float(relative_tolerance) * float(singular_values[0].item())
    return int(torch.count_nonzero(singular_values > cutoff).item())


def counterexample_metadata() -> dict[str, Any]:
    """Machine-readable descriptions used by the protocol and audit tooling."""

    return {
        "state_parameter_compensation": {
            "residual": "w + p - y",
            "jacobian_state": [[1.0]],
            "jacobian_parameter": [[1.0]],
            "zero_damping_rank": 0,
            "finite_gamma_curvature": "gamma/(1+gamma)",
        },
        "parameter_only_rank_deficiency": {
            "jacobian_parameter": [[1.0, 1.0], [2.0, 2.0]],
            "identifiable_combination": "p1 + p2",
            "rank": 1,
        },
        "heat_temperature_only_k_C": {
            "solution": "a*sin(pi*x)*exp(-pi^2*(k/C)*t)",
            "identifiable_combination": "k/C",
            "parameter_sensitivity_rank": 1,
        },
    }


__all__ = [
    "counterexample_metadata",
    "exact_zero_damping_curvature",
    "finite_gamma_reduced_curvature",
    "heat_temperature",
    "heat_temperature_sensitivities",
    "numerical_rank",
]
