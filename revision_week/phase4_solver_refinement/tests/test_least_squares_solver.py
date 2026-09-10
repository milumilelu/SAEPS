"""Phase 4 unit tests for the staged least-squares solver."""
from __future__ import annotations
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import torch

from objective_adapter import Objective, ResidualEvaluator
from common import Deadline
from least_squares_solver import normalized_gradient, solve_stage


def rosenbrock_case():
    def residual(theta, lam):
        return torch.stack([
            10.0 * (theta[1] - theta[0] ** 2),
            1.0 - theta[0],
        ])

    theta0 = torch.tensor([-1.2, 1.0], dtype=torch.float64)
    coordinate = torch.zeros(0, dtype=torch.float64)
    return residual, theta0, coordinate


def test_jacobian_matches_independent_construction():
    """jacrev of the augmented residual vs [jacrev(raw); sqrt(gamma)*I]."""
    residual, theta0, coordinate = rosenbrock_case()
    gamma = 1e-3
    ev_raw = ResidualEvaluator(residual, coordinate, theta0, 0.0, deadline=None)
    ev_prox = ResidualEvaluator(residual, coordinate, theta0, gamma, deadline=None)
    theta = 0.37 * torch.randn_like(theta0)
    J_raw = torch.func.jacrev(lambda t: residual(t, coordinate))(theta)
    eye = torch.eye(theta.numel(), dtype=torch.float64)
    expected = torch.cat((J_raw, math.sqrt(gamma) * eye), dim=0)
    actual = torch.from_numpy(ev_prox.jac_numpy(theta.numpy()))
    scale = max(float(expected.norm()), 1.0)
    assert float((actual - expected).norm()) / scale <= 1e-10


def test_solver_reaches_binding_target():
    residual, theta0, coordinate = rosenbrock_case()
    obj = Objective(residual, coordinate, theta0, 0.0)
    ev = ResidualEvaluator(residual, coordinate, theta0, 0.0, deadline=None)
    stage = solve_stage(ev, theta0.numpy().copy(), 1e-8, obj, 'K8',
                        deadline=None, wall_cap=600.0, nfev_pool=24000,
                        chunk_nfev=500, tol=1e-14)
    assert stage['target_reached']
    assert float(np.linalg.norm(stage['x'] - np.array([1.0, 1.0]))) < 1e-6
    assert stage['last_gate']['normalized_gradient'] <= 1e-8


def test_stage_reports_budget_exhaustion():
    residual, theta0, coordinate = rosenbrock_case()
    obj = Objective(residual, coordinate, theta0, 0.0)
    ev = ResidualEvaluator(residual, coordinate, theta0, 0.0, deadline=None)
    stage = solve_stage(ev, theta0.numpy().copy(), 1e-30, obj, 'impossible',
                        deadline=None, wall_cap=600.0, nfev_pool=3,
                        chunk_nfev=500, tol=1e-14)
    assert not stage['target_reached']
    assert stage['termination'] == 'nfev_budget_exhausted'


def test_stage_reports_wall_budget_as_recorded_reason():
    residual, theta0, coordinate = rosenbrock_case()
    obj = Objective(residual, coordinate, theta0, 0.0)
    ev = ResidualEvaluator(residual, coordinate, theta0, 0.0, deadline=Deadline(0.0))
    stage = solve_stage(ev, theta0.numpy().copy(), -1.0, obj, 'K8',
                        deadline=Deadline(0.0), wall_cap=600.0,
                        nfev_pool=24000, chunk_nfev=500, tol=1e-14)
    assert not stage['target_reached']
    assert stage['termination'] == 'wall_budget_exhausted'
