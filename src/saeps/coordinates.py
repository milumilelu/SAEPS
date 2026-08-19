"""Physical-parameter coordinate transforms."""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class IdentityCoordinate:
    def to_physical(self, coordinate: torch.Tensor) -> torch.Tensor:
        return coordinate

    def from_physical(self, physical: torch.Tensor) -> torch.Tensor:
        return physical


@dataclass(frozen=True)
class LogCoordinate:
    minimum_physical: float = 0.0

    def to_physical(self, coordinate: torch.Tensor) -> torch.Tensor:
        return torch.exp(coordinate)

    def from_physical(self, physical: torch.Tensor) -> torch.Tensor:
        if torch.any(physical <= self.minimum_physical):
            raise ValueError("log-coordinate physical values must be strictly positive")
        return torch.log(physical)

