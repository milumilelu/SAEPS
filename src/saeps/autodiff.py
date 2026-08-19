"""Autodiff and finite-difference residual linearization."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import torch

ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def _validate_vector(name: str, value: torch.Tensor) -> None:
    if not torch.is_tensor(value) or value.ndim != 1 or not value.is_floating_point():
        raise ValueError(f"{name} must be a one-dimensional floating tensor")
    if not torch.all(torch.isfinite(value)):
        raise ValueError(f"{name} contains non-finite values")


@dataclass
class ResidualLinearization:
    residual_function: ResidualFunction
    theta: torch.Tensor
    parameter: torch.Tensor
    operation_counts: dict[str, int] = field(default_factory=dict, init=False)
    _residual_size: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        _validate_vector("theta", self.theta)
        _validate_vector("parameter", self.parameter)
        if self.theta.dtype != self.parameter.dtype or self.theta.device != self.parameter.device:
            raise ValueError("theta and parameter must share dtype and device")
        self.theta = self.theta.detach().clone()
        self.parameter = self.parameter.detach().clone()
        residual = self.residual()
        _validate_vector("residual", residual)
        self._residual_size = residual.numel()

    def _count(self, name: str) -> None:
        self.operation_counts[name] = self.operation_counts.get(name, 0) + 1

    def residual(self) -> torch.Tensor:
        self._count("residual")
        value = self.residual_function(self.theta, self.parameter).reshape(-1)
        _validate_vector("residual", value)
        return value

    def jvp_theta(self, vector: torch.Tensor) -> torch.Tensor:
        _validate_vector("theta tangent", vector)
        if vector.shape != self.theta.shape:
            raise ValueError("theta tangent shape mismatch")
        self._count("jvp_theta")
        _, product = torch.func.jvp(
            lambda current: self.residual_function(current, self.parameter).reshape(-1),
            (self.theta,),
            (vector,),
        )
        return product

    def vjp_theta(self, cotangent: torch.Tensor) -> torch.Tensor:
        _validate_vector("residual cotangent", cotangent)
        if cotangent.numel() != self._residual_size:
            raise ValueError("residual cotangent shape mismatch")
        self._count("vjp_theta")
        _, pullback = torch.func.vjp(
            lambda current: self.residual_function(current, self.parameter).reshape(-1),
            self.theta,
        )
        return pullback(cotangent)[0]

    def jvp_parameter(self, vector: torch.Tensor) -> torch.Tensor:
        _validate_vector("parameter tangent", vector)
        if vector.shape != self.parameter.shape:
            raise ValueError("parameter tangent shape mismatch")
        self._count("jvp_parameter")
        _, product = torch.func.jvp(
            lambda current: self.residual_function(self.theta, current).reshape(-1),
            (self.parameter,),
            (vector,),
        )
        return product

    def vjp_parameter(self, cotangent: torch.Tensor) -> torch.Tensor:
        _validate_vector("residual cotangent", cotangent)
        if cotangent.numel() != self._residual_size:
            raise ValueError("residual cotangent shape mismatch")
        self._count("vjp_parameter")
        _, pullback = torch.func.vjp(
            lambda current: self.residual_function(self.theta, current).reshape(-1),
            self.parameter,
        )
        return pullback(cotangent)[0]

    def explicit_jacobians(self) -> tuple[torch.Tensor, torch.Tensor]:
        self._count("explicit_jacobians")
        jacobian_theta, jacobian_parameter = torch.func.jacrev(
            lambda state, physical: self.residual_function(state, physical).reshape(-1),
            argnums=(0, 1),
        )(self.theta, self.parameter)
        return jacobian_theta, jacobian_parameter

    def parameter_columns_matrix_free(self) -> torch.Tensor:
        basis = torch.eye(
            self.parameter.numel(), dtype=self.parameter.dtype, device=self.parameter.device
        )
        return torch.stack([self.jvp_parameter(column) for column in basis], dim=1)


def finite_difference_jacobian(
    function: Callable[[torch.Tensor], torch.Tensor],
    point: torch.Tensor,
    step: float,
) -> torch.Tensor:
    _validate_vector("finite-difference point", point)
    if step <= 0:
        raise ValueError("finite-difference step must be positive")
    columns: list[torch.Tensor] = []
    for index in range(point.numel()):
        perturbation = torch.zeros_like(point)
        perturbation[index] = step
        plus = function(point + perturbation).reshape(-1)
        minus = function(point - perturbation).reshape(-1)
        columns.append((plus - minus) / (2.0 * step))
    return torch.stack(columns, dim=1)
