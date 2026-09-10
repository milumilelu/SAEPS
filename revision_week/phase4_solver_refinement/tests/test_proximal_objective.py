"""Phase 4 unit tests for the fixed-reference proximal objective identities."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import torch

from objective_adapter import ProximalLeastSquaresObjective, ResidualEvaluator, sha256_tensor
from diagnostics import joint_matrices, route_ell, state_diagnostics
from least_squares_solver import solve_stage
from common import Deadline
import diagnostics


def synthetic_case(n=10, seed=5):
    generator = torch.Generator().manual_seed(seed)
    theta0 = 0.4 * torch.randn(n, dtype=torch.float64, generator=generator)
    coordinate = torch.tensor([0.9, 1.7], dtype=torch.float64)

    def residual(theta, lam):
        base = torch.stack([
            0.5 * (theta[0] ** 2 - 1.0) + 0.3 * theta[1] * lam[0],
            theta[0] + 0.7 * theta[2] - 0.2 * lam[1],
            torch.sin(theta[1] * lam[0]) + 0.25 * theta[3],
        ])
        extra = 0.03 * torch.sin(torch.arange(4, dtype=torch.float64) * theta[2] * lam[1])
        return torch.cat([base, extra])

    return residual, theta0, coordinate


def test_augmented_residual_identity():
    residual, theta0, coordinate = synthetic_case()
    gamma = 1e-4
    prox = ProximalLeastSquaresObjective(residual, coordinate, theta0, gamma)
    theta = 0.2 * torch.randn_like(theta0)
    augmented = prox.residual_augmented(theta)
    raw = residual(theta, coordinate)
    expected = float(0.5 * raw.square().sum() + 0.5 * gamma * (theta - theta0).square().sum())
    actual = float(0.5 * augmented.square().sum())
    assert abs(actual - expected) <= 1e-13 * max(1.0, abs(expected))


def test_gradient_identity():
    residual, theta0, coordinate = synthetic_case()
    gamma = 2e-4
    prox_ell = route_ell(residual, coordinate, gamma, theta0)
    raw_ell = lambda t: 0.5 * residual(t, coordinate).square().sum()
    theta = 0.3 * torch.randn_like(theta0)
    gradient_prox = torch.func.grad(prox_ell)(theta)
    gradient_raw = torch.func.grad(raw_ell)(theta)
    expected = gradient_raw + gamma * (theta - theta0)
    assert float((gradient_prox - expected).norm()) <= 1e-12 * max(1.0, float(gradient_prox.norm()))


def test_hessian_identity():
    residual, theta0, coordinate = synthetic_case()
    gamma = 3e-4
    h_raw, h_prox, _ = joint_matrices(residual, theta0, coordinate, gamma, theta0)
    n = theta0.numel()
    residual_matrix = h_prox[:n, :n] - h_raw[:n, :n] - gamma * np.eye(n)
    assert float(np.max(np.abs(residual_matrix))) <= 1e-12 * max(1.0, float(np.max(np.abs(h_raw[:n, :n]))))


def test_state_diagnostics_route_records():
    residual, theta0, coordinate = synthetic_case()
    alpha = 1e-8
    diag, matrices = state_diagnostics(residual, theta0, coordinate, 5.0, theta0, 'proximal', alpha)
    assert diag['route'] == 'proximal' and diag['m'] == 7 and diag['n'] == 10
    assert 'lambda_min_A_fd' in diag['H_raw']
    assert diag['H_prox']['gamma_solve'] == 5.0
    assert diag['H_prox']['proximal_stability_pass'] is True


def test_decide_terminal_never_claims_raw_local_minimum_for_prox_only():
    residual, theta0, coordinate = synthetic_case()
    stage = dict(target_reached=True, termination='target_reached', scipy_stop=None)
    diag = dict(route='P',
                H_raw=dict(H_raw_spd='not_SPD', stability_pass=False),
                H_prox=dict(proximal_stability_pass=True),
                normalized_gradient_route=1e-12)
    curvature = dict(K8_saved=True, K10_saved=True, K12_saved=True, drift_pass=True)
    fit = dict(fit_pass=True)
    verdict = diagnostics.decide_terminal('proximal', stage, diag, curvature, fit)
    assert verdict['status'] == 'PASS'
    assert verdict['labels']['REFERENCE_CAPABLE'] is True
    assert verdict['labels']['raw_local_minimum'] is False
