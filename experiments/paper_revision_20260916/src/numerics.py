"""Small, independent numerical checks for the SAEPS paper revision.

All derivatives refer to ell = 0.5 * sum(residual**2).
These helpers are NOT a training runner or a replacement for frozen SAEPS code.
"""
from __future__ import annotations
from pathlib import Path
from typing import Callable
import numpy as np
import torch

Residual = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def objective_blocks(residual: Residual, theta: torch.Tensor,
                     parameter: torch.Tensor) -> dict[str, np.ndarray]:
    """Differentiate a small residual map. Use float64 and fixed sampled points."""
    if theta.ndim != 1 or parameter.ndim != 1 or theta.numel() == 0 or parameter.numel() == 0:
        raise ValueError('theta and parameter must be nonempty vectors')
    if theta.dtype != torch.float64 or parameter.dtype != torch.float64:
        raise ValueError('This reference checker requires float64')
    if theta.device != parameter.device:
        raise ValueError('State and parameter devices differ')
    n = theta.numel()
    q = torch.cat([theta.detach(), parameter.detach()])
    def rfun(v: torch.Tensor) -> torch.Tensor:
        value = residual(v[:n], v[n:])
        if value.ndim != 1:
            raise ValueError('Residual must be a one-dimensional vector')
        return value
    def loss(v: torch.Tensor) -> torch.Tensor:
        return 0.5 * rfun(v).square().sum()
    r = rfun(q)
    if r.numel() == 0 or not bool(torch.isfinite(r).all()):
        raise ValueError('Residual must be nonempty and finite')
    j = torch.func.jacrev(rfun)(q)
    h = torch.func.hessian(loss)(q)
    g = torch.func.grad(loss)(q)
    def a(x: torch.Tensor) -> np.ndarray:
        return x.detach().cpu().numpy().copy()
    return dict(residual=a(r), J_theta=a(j[:, :n]), J_parameter=a(j[:, n:]),
                H_theta_theta=a(h[:n, :n]), H_theta_parameter=a(h[:n, n:]),
                H_parameter_parameter=a(h[n:, n:]), gradient_theta=a(g[:n]),
                gradient_parameter=a(g[n:]), theta=a(theta), parameter=a(parameter),
                objective_sum=np.array(float(loss(q).detach())),
                residual_count=np.array(r.numel(), dtype=np.int64))


def _symmetric(a: np.ndarray, name: str) -> np.ndarray:
    if a.ndim != 2 or a.shape[0] != a.shape[1] or not np.isfinite(a).all():
        raise ValueError(f'{name} is not a finite square matrix')
    err = np.linalg.norm(a-a.T) / max(np.linalg.norm(a), 1e-30)
    if err > 1e-8:
        raise ValueError(f'{name} symmetry error {err:.3g} exceeds 1e-8')
    return (a+a.T)/2


def reduced_matrices(blocks: dict[str, np.ndarray], gamma: float,
                     metric: np.ndarray | None = None,
                     eigen_relative_tolerance: float = 1e-10) -> dict:
    """Compute matched-damping references without repairing an inadmissible Hessian.

An algebraic exact-Hessian Schur reference is withheld for an inadmissible state block.
A positive state block does NOT certify numerical state stationarity.
This is independent of whether SAEPS is closer than the raw baseline.
"""
    if not np.isfinite(gamma) or gamma <= 0:
        raise ValueError('gamma must be finite and positive')
    jt, jp = np.asarray(blocks['J_theta']), np.asarray(blocks['J_parameter'])
    if jt.ndim != 2 or jp.ndim != 2 or jt.shape[0] != jp.shape[0]:
        raise ValueError('Incompatible Jacobian shapes')
    if not np.isfinite(jt).all() or not np.isfinite(jp).all():
        raise ValueError('Nonfinite Jacobian')
    n, p = jt.shape[1], jp.shape[1]
    if n == 0 or p == 0:
        raise ValueError('Empty state or parameter dimension')
    metric = np.eye(n) if metric is None else _symmetric(np.asarray(metric), 'metric')
    if metric.shape != (n,n):
        raise ValueError('State metric shape mismatch')
    np.linalg.cholesky(metric)
    gtt, b, raw = jt.T @ jt, jt.T @ jp, jp.T @ jp
    m = _symmetric(gtt+gamma*metric, 'GN state block')
    z = np.linalg.solve(m, b)
    cgn = b.T @ z
    fse = _symmetric(raw-cgn, 'SAEPS')
    htt = _symmetric(np.asarray(blocks['H_theta_theta']), 'Htt')
    htp = np.asarray(blocks['H_theta_parameter'])
    hpp = _symmetric(np.asarray(blocks['H_parameter_parameter']), 'Hpp')
    if htt.shape != (n,n) or htp.shape != (n,p) or hpp.shape != (p,p):
        raise ValueError('Hessian block shape mismatch')
    if not np.isfinite(htp).all():
        raise ValueError('Nonfinite mixed block')
    k = _symmetric(htt+gamma*metric, 'Exact state block')
    ev = np.linalg.eigvalsh(k)
    tol = max(1e-14, eigen_relative_tolerance * max(abs(ev).max(), 1e-30))
    exact_valid = bool(ev[0] > tol)
    stt, stp, spp = htt-gtt, htp-b, hpp-raw
    fso = fse + spp - stp.T@z - z.T@stp + z.T@stt@z
    result = dict(F_raw=raw, F_SAEPS=fse, C_GN=cgn, F_SO=fso,
                  S_theta_theta=stt, S_theta_parameter=stp,
                  S_parameter_parameter=spp, exact_valid=exact_valid,
                  state_min_eigenvalue=float(ev[0]), state_max_eigenvalue=float(ev[-1]),
                  eigen_acceptance_threshold=float(tol), gamma=float(gamma),
                  H_reduced=None, C_exact=None, newton_response=None,
                  exact_state_block_admissible=exact_valid, stationarity_certified=False,
                  reference_scope='ALGEBRAIC_SCHUR_ONLY; check state stationarity separately',
                  normal_residual=float(np.linalg.norm(m@z-b)/max(np.linalg.norm(b),1e-30)),
                  exact_solve_residual=None)
    if exact_valid:
        h = np.linalg.solve(k, htp)
        ce = htp.T @ h
        result['H_reduced'] = _symmetric(hpp-ce, 'Hred')
        result['C_exact'] = ce
        result['exact_solve_residual'] = float(np.linalg.norm(k@h-htp)/max(np.linalg.norm(htp),1e-30))
        if 'gradient_theta' in blocks:
            state_gradient = blocks.get('penalty_gradient_theta', blocks['gradient_theta'])
            if np.asarray(state_gradient).shape != (n,) or not np.isfinite(state_gradient).all():
                raise ValueError('Invalid state gradient')
            result['newton_response'] = -np.linalg.solve(k, state_gradient)
    return result


def log_affine_identity(blocks: dict[str, np.ndarray]) -> dict[str, float | bool]:
    """Check S_ll = diag(g_l), applicable ONLY to elementwise exponentiated affine coefficients."""
    jp = np.asarray(blocks['J_parameter'])
    actual = np.asarray(blocks['H_parameter_parameter']) - jp.T@jp
    expected = np.diag(np.atleast_1d(blocks['gradient_parameter']))
    error = float(np.linalg.norm(actual-expected))
    scale = max(float(np.linalg.norm(actual)), float(np.linalg.norm(expected)),
                float(np.linalg.norm(jp.T@jp)), 1.0)
    # Mixed absolute/relative tolerance avoids declaring cancellation noise a failure.
    tolerance = 1e-10*scale + 1e-12
    return dict(absolute_error=error, scaled_error=error/scale,
                tolerance=tolerance, identity_pass=bool(error <= tolerance))


def save_blocks(path: str | Path, blocks: dict[str, np.ndarray], gamma: float) -> None:
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as out:
        np.savez_compressed(out, **blocks, gamma=np.array(float(gamma)))


def load_blocks(path: str | Path) -> tuple[dict[str, np.ndarray], float]:
    with np.load(path, allow_pickle=False) as z:
        result = {k:z[k].copy() for k in z.files}
    gamma = float(result.pop('gamma'))
    required = {'J_theta','J_parameter','H_theta_theta','H_theta_parameter',
                'H_parameter_parameter','gradient_parameter'}
    missing = required-result.keys()
    if missing:
        raise ValueError(f'Missing blocks: {sorted(missing)}')
    return result, gamma
