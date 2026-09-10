"""Phase 4 unit tests for the objective adapters; synthetic problems only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import torch

from objective_adapter import (Objective, ProximalLeastSquaresObjective,
                               ResidualEvaluator, SolverAbort, sha256_tensor)


def synthetic_residual(n=12, seed=3, m_extra=2):
    generator = torch.Generator().manual_seed(seed)
    theta0 = 0.5 * torch.randn(n, dtype=torch.float64, generator=generator)
    coordinate = torch.tensor([0.7, 1.3], dtype=torch.float64)

    def residual(theta, lam):
        base = torch.stack([
            0.3 * (theta[0] ** 2 - 1.0) + 0.2 * theta[1] * lam[0],
            theta[0] + 0.4 * theta[2] - 0.1 * lam[1],
            torch.sin(theta[1] * lam[0]) + 0.2 * theta[3],
        ])
        extra = 0.05 * torch.sin(torch.arange(m_extra, dtype=torch.float64) * theta[2] * lam[1])
        return torch.cat([base, extra])

    return residual, theta0, coordinate


def test_raw_objective_identity():
    residual, theta0, coordinate = synthetic_residual()
    obj = Objective(residual, coordinate, theta0, 0.0)
    r = residual(theta0, coordinate)
    expected = float(0.5 * r.square().sum())
    assert abs(obj.value(theta0) - expected) <= 1e-12 * max(1.0, abs(expected))


def test_normalized_gradient_definition():
    from least_squares_solver import normalized_gradient
    residual, theta0, coordinate = synthetic_residual()
    obj = Objective(residual, coordinate, theta0, 0.0)
    gradient = torch.func.grad(obj.tensor)(theta0)
    expected = float(gradient.norm() / (obj.m * max(float(theta0.norm()), 1.0)))
    assert abs(normalized_gradient(gradient.numpy(), theta0, obj.m) - expected) <= 1e-14


def test_evaluator_counts_and_last_iterate():
    residual, theta0, coordinate = synthetic_residual()
    ev = ResidualEvaluator(residual, coordinate, theta0, 0.0, deadline=None)
    value = ev.fun_numpy(theta0.numpy())
    jacobian = ev.jac_numpy(theta0.numpy())
    assert value.shape == (5,)
    assert jacobian.shape == (5, 12)
    assert ev.nfev == 1 and ev.njev == 1
    assert np.allclose(ev.last_x, theta0.numpy())


def test_proximal_solver_anchor_frozen():
    residual, theta0, coordinate = synthetic_residual()
    gamma = 1e-3
    prox = ProximalLeastSquaresObjective(residual, coordinate, theta0, gamma)
    ev = ResidualEvaluator(residual, coordinate, theta0, gamma, deadline=None)
    before = sha256_tensor(prox.theta0)
    assert before == sha256_tensor(theta0)
    from scipy.optimize import least_squares
    out = least_squares(ev.fun_numpy, theta0.numpy().copy(), jac=ev.jac_numpy,
                        method='trf', tr_solver='exact', x_scale='jac', loss='linear',
                        ftol=1e-14, xtol=1e-14, gtol=1e-14, max_nfev=2000)
    assert sha256_tensor(prox.theta0) == before
    assert np.isfinite(out.x).all()


def test_nonfinite_residual_is_controlled():
    residual, theta0, coordinate = synthetic_residual()

    def bad(theta, lam):
        raise ZeroDivisionError('synthetic failure')

    ev = ResidualEvaluator(bad, coordinate, theta0, 0.0, deadline=None)
    try:
        ev.fun_numpy(theta0.numpy())
    except SolverAbort as abort:
        assert abort.kind == 'residual_exception'
    else:
        raise AssertionError('expected SolverAbort')
