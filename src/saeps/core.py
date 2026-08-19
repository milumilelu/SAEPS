"""Explicit and matrix-free SAEPS computations."""

from __future__ import annotations

from dataclasses import dataclass

import torch

from saeps.autodiff import ResidualLinearization
from saeps.solvers import CGResult, conjugate_gradient


class CGConvergenceError(RuntimeError):
    pass


def raw_curvature(jacobian_parameter: torch.Tensor) -> torch.Tensor:
    return jacobian_parameter.T @ jacobian_parameter


def exact_svd_complement_projector(
    jacobian_theta: torch.Tensor, relative_tolerance: float
) -> tuple[torch.Tensor, int]:
    if relative_tolerance <= 0:
        raise ValueError("SVD relative tolerance must be positive")
    left, singular_values, _ = torch.linalg.svd(jacobian_theta, full_matrices=False)
    if singular_values.numel() == 0:
        rank = 0
    else:
        cutoff = relative_tolerance * float(singular_values[0].item())
        rank = int(torch.count_nonzero(singular_values > cutoff).item())
    identity = torch.eye(
        jacobian_theta.shape[0], dtype=jacobian_theta.dtype, device=jacobian_theta.device
    )
    if rank == 0:
        return identity, rank
    range_basis = left[:, :rank]
    return identity - range_basis @ range_basis.T, rank


def explicit_tikhonov_operator(jacobian_theta: torch.Tensor, gamma: float) -> torch.Tensor:
    if gamma <= 0:
        raise ValueError("gamma must be positive")
    identity_theta = torch.eye(
        jacobian_theta.shape[1], dtype=jacobian_theta.dtype, device=jacobian_theta.device
    )
    identity_residual = torch.eye(
        jacobian_theta.shape[0], dtype=jacobian_theta.dtype, device=jacobian_theta.device
    )
    normal = jacobian_theta.T @ jacobian_theta + gamma * identity_theta
    solved = torch.linalg.solve(normal, jacobian_theta.T)
    return identity_residual - jacobian_theta @ solved


def state_eliminated_curvature(
    jacobian_parameter: torch.Tensor, operator_matrix: torch.Tensor
) -> torch.Tensor:
    return jacobian_parameter.T @ operator_matrix @ jacobian_parameter


def state_eliminated_score(
    jacobian_parameter: torch.Tensor,
    operator_matrix: torch.Tensor,
    residual: torch.Tensor,
) -> torch.Tensor:
    return jacobian_parameter.T @ operator_matrix @ residual


def retained_sensitivity(
    eliminated_curvature: torch.Tensor,
    fixed_curvature: torch.Tensor,
    epsilon: float = 1.0e-30,
) -> torch.Tensor:
    if eliminated_curvature.shape != fixed_curvature.shape:
        raise ValueError("curvature shape mismatch")
    return torch.diagonal(eliminated_curvature) / (torch.diagonal(fixed_curvature) + epsilon)


@dataclass(frozen=True)
class MatrixFreeApplication:
    value: torch.Tensor
    solve: CGResult


@dataclass(frozen=True)
class MatrixFreeSAEPSResult:
    residual: torch.Tensor
    jacobian_parameter: torch.Tensor
    raw_curvature: torch.Tensor
    eliminated_curvature: torch.Tensor
    eliminated_score: torch.Tensor
    eta: torch.Tensor
    solves: tuple[CGResult, ...]
    operation_counts: dict[str, int]


class MatrixFreeEliminator:
    def __init__(
        self,
        linearization: ResidualLinearization,
        gamma: float,
        cg_tolerance: float,
        cg_max_iterations: int,
    ) -> None:
        if gamma <= 0:
            raise ValueError("gamma must be positive")
        self.linearization = linearization
        self.gamma = float(gamma)
        self.cg_tolerance = float(cg_tolerance)
        self.cg_max_iterations = int(cg_max_iterations)

    def normal_operator(self, vector: torch.Tensor) -> torch.Tensor:
        return self.linearization.vjp_theta(self.linearization.jvp_theta(vector)) + self.gamma * vector

    def apply(self, residual_vector: torch.Tensor) -> MatrixFreeApplication:
        right_hand_side = self.linearization.vjp_theta(residual_vector)
        solve = conjugate_gradient(
            self.normal_operator,
            right_hand_side,
            tolerance=self.cg_tolerance,
            max_iterations=self.cg_max_iterations,
        )
        if not solve.converged:
            raise CGConvergenceError(
                f"CG failed: iterations={solve.iterations}, relative_residual={solve.relative_residual:.3e}"
            )
        value = residual_vector - self.linearization.jvp_theta(solve.solution)
        return MatrixFreeApplication(value, solve)


def compute_matrix_free_saeps(
    linearization: ResidualLinearization,
    gamma: float,
    cg_tolerance: float,
    cg_max_iterations: int,
) -> MatrixFreeSAEPSResult:
    residual = linearization.residual()
    jacobian_parameter = linearization.parameter_columns_matrix_free()
    eliminator = MatrixFreeEliminator(
        linearization, gamma, cg_tolerance, cg_max_iterations
    )
    applications = tuple(
        eliminator.apply(jacobian_parameter[:, index])
        for index in range(jacobian_parameter.shape[1])
    )
    residual_application = eliminator.apply(residual)
    eliminated_columns = torch.stack([item.value for item in applications], dim=1)
    fixed_curvature = raw_curvature(jacobian_parameter)
    eliminated_curvature = jacobian_parameter.T @ eliminated_columns
    eliminated_score = jacobian_parameter.T @ residual_application.value
    solves = tuple(item.solve for item in applications) + (residual_application.solve,)
    return MatrixFreeSAEPSResult(
        residual=residual,
        jacobian_parameter=jacobian_parameter,
        raw_curvature=fixed_curvature,
        eliminated_curvature=eliminated_curvature,
        eliminated_score=eliminated_score,
        eta=retained_sensitivity(eliminated_curvature, fixed_curvature),
        solves=solves,
        operation_counts=dict(linearization.operation_counts),
    )

