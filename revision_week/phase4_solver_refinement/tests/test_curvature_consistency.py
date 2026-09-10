"""Phase 4 curvature consistency tests on a synthetic constant-Hessian problem."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import torch

from diagnostics import curvature_record, reduced_curvature, state_diagnostics
from least_squares_solver import solve_stage
from numerics import Objective
from objective_adapter import ResidualEvaluator


def linear_case(n=8, m_rows=20, seed=17):
    generator = torch.Generator().manual_seed(seed)
    A = 0.3 * torch.randn(m_rows, n, dtype=torch.float64, generator=generator)
    B = 0.4 * torch.randn(m_rows, 2, dtype=torch.float64, generator=generator)
    theta0 = 0.3 * torch.randn(n, dtype=torch.float64, generator=generator)
    coordinate = torch.tensor([0.7, 1.1], dtype=torch.float64)

    def residual(theta, lam):
        return A @ theta + B @ lam + 0.2 * torch.ones_like(B @ lam)

    return residual, theta0, coordinate, A, B


def test_joint_hessian_matches_analytic_mtm():
    residual, theta0, coordinate, A, B = linear_case()
    diag, matrices = state_diagnostics(residual, theta0, coordinate, 0.0, theta0, 'raw', 1e-8)
    actual = matrices['H_raw_joint'][:theta0.numel(), :theta0.numel()]
    expected = A.detach().numpy().T @ A.detach().numpy()
    scale = max(float(np.linalg.norm(expected)), 1.0)
    assert float(np.linalg.norm(actual - expected)) / scale <= 1e-10


def test_curvature_stability_on_constant_hessian():
    residual, theta0, coordinate, A, B = linear_case()
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


def test_reduced_curvature_shape_with_two_parameters():
    """F_star is p x p; a broadcast bug would silently return n x n for p=1 and
    raise for p=2 (regression guard)."""
    residual, theta0, coordinate, A, B = linear_case()
    h_raw, h_route, _ = joint_matrices_blocks(residual, theta0, coordinate)
    A_t = A.detach().numpy().T @ A.detach().numpy()
    gamma = 1e-8
    matrices = dict(H_route_joint=h_route, H_raw_joint=h_raw, H_raw=A_t,
                    H_prox=A_t + gamma * np.eye(theta0.numel()))
    record = reduced_curvature(matrices, theta0.numel(), 'proximal', gamma)
    assert record['F_star'] is not None
    assert len(record['F_star']) == 2 and len(record['F_star'][0]) == 2
    AB = A.detach().numpy().T @ B.detach().numpy()
    expected = (B.detach().numpy().T @ B.detach().numpy()) - AB.T @ np.linalg.solve(A_t + gamma * np.eye(theta0.numel()), AB)
    assert float(np.max(np.abs(np.asarray(record['F_star']) - expected))) <= 1e-10 * max(1.0, float(np.max(np.abs(expected))))


def joint_matrices_blocks(residual, theta, coordinate):
    from diagnostics import joint_matrices
    return joint_matrices(residual, theta, coordinate, 0.0, theta)
