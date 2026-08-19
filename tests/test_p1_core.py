from __future__ import annotations

from pathlib import Path

import torch

from saeps.coordinates import IdentityCoordinate, LogCoordinate
from saeps.p1_validation import run_core_validation
from saeps.residual import stack_weighted_residuals
from saeps.solvers import conjugate_gradient


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_coordinates_round_trip() -> None:
    physical = torch.tensor([0.2, 3.0], dtype=torch.float64)
    assert torch.equal(IdentityCoordinate().to_physical(physical), physical)
    coordinate = LogCoordinate().from_physical(physical)
    assert torch.allclose(LogCoordinate().to_physical(coordinate), physical, atol=1.0e-15, rtol=0.0)


def test_weighted_residual_stack() -> None:
    blocks = {"pde": torch.tensor([1.0, -2.0], dtype=torch.float64), "data": torch.tensor([3.0], dtype=torch.float64)}
    actual = stack_weighted_residuals(blocks, {"pde": 4.0, "data": 9.0})
    assert torch.equal(actual, torch.tensor([2.0, -4.0, 9.0], dtype=torch.float64))


def test_cg_solves_actual_spd_system() -> None:
    matrix = torch.tensor([[4.0, 1.0], [1.0, 3.0]], dtype=torch.float64)
    right = torch.tensor([1.0, 2.0], dtype=torch.float64)
    result = conjugate_gradient(lambda vector: matrix @ vector, right, 1.0e-12, 10)
    assert result.converged
    assert result.relative_residual <= 1.0e-12
    assert torch.allclose(result.solution, torch.linalg.solve(matrix, right), atol=1.0e-12, rtol=0.0)


def test_p1_end_to_end_real_neural_residual(tmp_path: Path) -> None:
    result = run_core_validation(REPO_ROOT / "configs/p1_core.yaml", tmp_path, REPO_ROOT, write_output=False)
    assert result["status"] == "PASS"
    assert all(result["checks"].values())
    assert len(result["metrics"]["operator_relative_errors"]) == 10
    assert result["operation_counts"].get("explicit_jacobians", 0) == 0

