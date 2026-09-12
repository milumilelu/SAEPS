"""Independent finite-difference reference for the one-mode heat equation.

This module deliberately does not call the analytic observation functions or
the PINN residual.  It solves the semi-discrete Dirichlet heat equation with a
matrix-eigen decomposition, then interpolates the numerical state at requested
observation points.  It is small enough for refinement checks in RI-1/R2.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class HeatFDResult:
    """Numerical state and metadata for one refinement level."""

    x: np.ndarray
    t: np.ndarray
    values: np.ndarray
    interior_count: int
    spacing: float


def _interior_eigendecomposition(interior_count: int) -> tuple[np.ndarray, np.ndarray, float]:
    if int(interior_count) < 4:
        raise ValueError("interior_count must be at least four")
    n = int(interior_count)
    h = 1.0 / (n + 1)
    lap = np.diag(np.full(n, -2.0 / h**2))
    off = np.full(n - 1, 1.0 / h**2)
    lap += np.diag(off, 1) + np.diag(off, -1)
    eigenvalues, eigenvectors = np.linalg.eigh(lap)
    return eigenvalues, eigenvectors, h


def heat_fd_temperature(
    x: np.ndarray,
    t: np.ndarray,
    *,
    k: float,
    C: float,
    amplitude: float = 1.0,
    interior_count: int = 64,
) -> HeatFDResult:
    """Solve ``C*T_t=k*T_xx`` on ``[0,1]`` with homogeneous Dirichlet data.

    ``x`` and ``t`` are flattened paired observation coordinates.  The
    initial condition is sampled as ``a*sin(pi*x)`` on the numerical grid.
    A matrix exponential is evaluated through the symmetric Laplacian's
    eigenpairs, so the only approximation is spatial discretisation and
    interpolation (no analytic heat solution is used).
    """

    x_arr = np.asarray(x, dtype=float).reshape(-1)
    t_arr = np.asarray(t, dtype=float).reshape(-1)
    if x_arr.shape != t_arr.shape:
        raise ValueError("x and t must have the same shape")
    if np.any((x_arr < 0.0) | (x_arr > 1.0)) or np.any(t_arr < 0.0):
        raise ValueError("coordinates must satisfy x in [0,1] and t >= 0")
    if k <= 0.0 or C <= 0.0:
        raise ValueError("k and C must be positive")
    eigenvalues, eigenvectors, h = _interior_eigendecomposition(interior_count)
    grid = np.linspace(0.0, 1.0, int(interior_count) + 2)
    u0 = float(amplitude) * np.sin(np.pi * grid[1:-1])
    coefficients = eigenvectors.T @ u0
    values = np.empty_like(x_arr)
    for index, (x_value, t_value) in enumerate(zip(x_arr, t_arr)):
        if t_value == 0.0:
            values[index] = float(amplitude) * np.sin(np.pi * x_value)
            continue
        interior = eigenvectors @ (coefficients * np.exp(eigenvalues * (k / C) * t_value))
        full = np.concatenate(([0.0], interior, [0.0]))
        values[index] = np.interp(x_value, grid, full)
    return HeatFDResult(x_arr, t_arr, values, int(interior_count), h)


def finite_difference_sensitivity(
    x: np.ndarray,
    t: np.ndarray,
    *,
    k: float,
    C: float,
    amplitude: float = 1.0,
    interior_count: int = 64,
    relative_step: float = 1.0e-5,
) -> np.ndarray:
    """Centered finite-difference sensitivities with columns ``(k,C,a)``."""

    if relative_step <= 0.0:
        raise ValueError("relative_step must be positive")
    params = np.array([float(k), float(C), float(amplitude)], dtype=float)
    columns: list[np.ndarray] = []
    for index in range(3):
        step = relative_step * max(abs(params[index]), 1.0e-8)
        plus = params.copy(); plus[index] += step
        minus = params.copy(); minus[index] -= step
        yp = heat_fd_temperature(x, t, k=plus[0], C=plus[1], amplitude=plus[2], interior_count=interior_count).values
        ym = heat_fd_temperature(x, t, k=minus[0], C=minus[1], amplitude=minus[2], interior_count=interior_count).values
        columns.append((yp - ym) / (2.0 * step))
    return np.stack(columns, axis=1)


def refinement_difference(
    x: np.ndarray,
    t: np.ndarray,
    *,
    k: float,
    C: float,
    amplitude: float = 1.0,
    coarse_count: int = 32,
    fine_count: int = 64,
) -> float:
    """Return the maximum coarse/fine discrepancy in observed temperature."""

    coarse = heat_fd_temperature(x, t, k=k, C=C, amplitude=amplitude, interior_count=coarse_count).values
    fine = heat_fd_temperature(x, t, k=k, C=C, amplitude=amplitude, interior_count=fine_count).values
    return float(np.max(np.abs(coarse - fine))) if coarse.size else 0.0


__all__ = ["HeatFDResult", "heat_fd_temperature", "finite_difference_sensitivity", "refinement_difference"]
