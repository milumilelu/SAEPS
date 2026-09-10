"""Phase 4 synthetic negative-curvature tests (Section 14.7)."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import torch

from core import numerical_mu, sym
from diagnostics import decide_terminal, joint_matrices, state_diagnostics
from least_squares_solver import solve_stage
from objective_adapter import ResidualEvaluator
from numerics import Objective


def negative_curvature_case():
    """ell(theta) = 0.5 * ||r||^2 with a raw Hessian that is indefinite near theta=0."""

    def residual(theta, lam):
        return torch.stack([
            0.5 * (theta[0] ** 2 - 1.0),
            theta[1],
        ])

    theta_start = torch.tensor([0.1, 0.2], dtype=torch.float64)
    coordinate = torch.tensor([1.0], dtype=torch.float64)
    return residual, theta_start, coordinate


def test_raw_stability_fails_while_proximal_can_pass():
    residual, theta_start, coordinate = negative_curvature_case()
    diag, matrices = state_diagnostics(residual, theta_start, coordinate, 0.0,
                                       theta_start, 'raw', 1e-8)
    n = theta_start.numel()
    H_raw = sym(matrices['H_raw_joint'][:n, :n])
    mu_raw = numerical_mu(H_raw)
    assert mu_raw['mu_value'] is None and mu_raw['lambda_min_A_numeric'] < 0
    small = numerical_mu(H_raw + 0.1 * np.eye(n))
    assert small['mu_value'] is None
    large = numerical_mu(H_raw + 5.0 * np.eye(n))
    assert large['mu_value'] is not None and large['mu_value'] > 0


def test_proximal_solve_labels_stable_but_not_raw_minimum():
    residual, theta_start, coordinate = negative_curvature_case()
    gamma = 5.0
    obj = Objective(residual, coordinate, theta_start, gamma)
    ev = ResidualEvaluator(residual, coordinate, theta_start, gamma, deadline=None)
    stage = solve_stage(ev, theta_start.numpy().copy(), 1e-8, obj, 'K8',
                        deadline=None, wall_cap=600.0, nfev_pool=24000,
                        chunk_nfev=500, tol=1e-14)
    assert stage['target_reached']
    theta_final = torch.from_numpy(stage['x'].copy())
    diag, _ = state_diagnostics(residual, theta_final, coordinate, gamma,
                                theta_start, 'proximal', 1e-8)
    stage_record = dict(target_reached=True, termination='target_reached', scipy_stop=None)
    curvature = dict(K8_saved=True, K10_saved=True, K12_saved=True, drift_pass=True)
    fit = dict(fit_pass=True)
    verdict = decide_terminal('proximal', stage_record, diag, curvature, fit)
    assert verdict['status'] == 'PASS'
    assert verdict['labels']['REFERENCE_CAPABLE'] is True
    assert verdict['labels']['raw_local_minimum'] is False


def test_joint_matrices_proximal_identity_on_synthetic_case():
    residual, theta_start, coordinate = negative_curvature_case()
    gamma = 5.0
    h_raw, h_route, _ = joint_matrices(residual, theta_start, coordinate, gamma, theta_start)
    n = theta_start.numel()
    assert float(np.max(np.abs(h_route[:n, :n] - h_raw[:n, :n] - gamma * np.eye(n)))) <= 1e-12
