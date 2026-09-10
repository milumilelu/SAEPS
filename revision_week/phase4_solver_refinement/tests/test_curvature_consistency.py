"""Phase 4 curvature consistency tests on a synthetic constant-Hessian problem."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import torch

from diagnostics import curvature_record, state_diagnostics
from least_squares_solver import solve_stage
from numerics import Objective
from objective_adapter import ResidualEvaluator


def linear_case(n=8, m_rows=20, seed=17):
    generator = torch.Generator().manual_seed(seed)
    A = 0.3 * torch.randn(m_rows, n, dtype=torch.float64, generator=generator)
    b = 0.5 * torch.randn(m_rows, dtype=torch.float64, generator=generator)
    theta0 = 0.3 * torch.randn(n, dtype=torch.float64, generator=generator)
    coordinate = torch.tensor([1.0], dtype=torch.float64)

    def residual(theta, lam):
        return A @ theta + b + 0.1 * lam[0]

    return residual, theta0, coordinate, A


def test_joint_hessian_matches_analytic_mtm():
    residual, theta0, coordinate, A = linear_case()
    diag, matrices = state_diagnostics(residual, theta0, coordinate, 0.0, theta0, 'raw', 1e-8)
    actual = matrices['H_raw_joint'][:theta0.numel(), :theta0.numel()]
    expected = A.detach().numpy().T @ A.detach().numpy()
    scale = max(float(np.linalg.norm(expected)), 1.0)
    assert float(np.linalg.norm(actual - expected)) / scale <= 1e-10


def test_curvature_stability_on_constant_hessian():
    residual, theta0, coordinate, A = linear_case()
    obj = Objective(residual, coordinate, theta0, 0.0)
    ev = ResidualEvaluator(residual, coordinate, theta0, 0.0, deadline=None)
    stage = solve_stage(ev, theta0.numpy().copy(), 1e-8, obj, 'K8',
                        deadline=None, wall_cap=600.0, nfev_pool=24000,
                        chunk_nfev=500, tol=1e-14)
    assert stage['target_reached']
    theta8 = torch.from_numpy(stage['x'].copy())
    diag8, matrices8 = state_diagnostics(residual, theta8, coordinate, 0.0, theta0, 'raw', 1e-8)
    record8, K8 = curvature_record('synthetic', 'raw', 'K8', theta8, matrices8, diag8, None,
                                   stage['seconds'], 1e-8)
    stage10 = solve_stage(ev, stage['x'].copy(), 1e-10, obj, 'K10',
                          deadline=None, wall_cap=600.0, nfev_pool=2000,
                          chunk_nfev=500, tol=1e-14)
    assert stage10['target_reached']
    theta10 = torch.from_numpy(stage10['x'].copy())
    diag10, matrices10 = state_diagnostics(residual, theta10, coordinate, 0.0, theta0, 'raw', 1e-8)
    record10, K10 = curvature_record('synthetic', 'raw', 'K10', theta10, matrices10, diag10,
                                     K8, stage10['seconds'], 1e-10)
    drift = record10['K_drift_vs_previous']
    assert drift['fro_relative'] <= 0.05 and drift['spectral_relative'] <= 0.05
    assert drift['stability_pass'] is True


def test_state_records_binding_gradient():
    residual, theta0, coordinate, A = linear_case()
    diag, _ = state_diagnostics(residual, theta0, coordinate, 0.0, theta0, 'raw', 1e-8)
    assert math.isfinite(diag['normalized_gradient_route'])
