"""Directional curvature for fixed sum-of-squares targets; damping added once.

The quadratic formula extends scripts/upgrade_pilot/pilot_curvature_correction.py
quadratic_curvature to arbitrary parameter dimension and inexact responses.
Dense references are separate from candidate evaluation and stopping.
"""
from __future__ import annotations
from collections.abc import Callable
import numpy as np


def sym(x: np.ndarray) -> np.ndarray:
    return (x + x.T) / 2


def quadratic(c: np.ndarray, b: np.ndarray, a: np.ndarray, z: np.ndarray) -> np.ndarray:
    """Complete symmetric quadratic, valid even when a @ z != b."""
    return sym(c - b.T @ z - z.T @ b + z.T @ a @ z)


def evaluate(g: np.ndarray, h: np.ndarray, n: int, gamma: float,
             z: np.ndarray) -> dict:
    """Return GN/SO quadratics, defects and direct-vs-correction discrepancy."""
    if not np.isfinite(gamma) or gamma <= 0:
        raise ValueError('gamma must be fixed, finite and positive')
    if not all(np.isfinite(x).all() for x in (g, h, z)):
        raise ValueError('nonfinite input')
    if g.shape != h.shape or g.shape != (n + z.shape[1], n + z.shape[1]):
        raise ValueError('joint dimensions inconsistent')
    for x in (g, h):
        if np.linalg.norm(x-x.T) > 1e-8 * max(np.linalg.norm(x), 1e-30):
            raise ValueError('asymmetric joint matrix')
    m = g[:n, :n] + gamma * np.eye(n)
    a = h[:n, :n] + gamma * np.eye(n)
    bg, b = g[:n, n:], h[:n, n:]
    v = np.vstack((-z, np.eye(z.shape[1])))
    q = quadratic(g[n:, n:], bg, m, z)
    f = quadratic(h[n:, n:], b, a, z)
    return dict(Q_G=q, F_SO=f, D=b-a@z, R_G=bg-m@z,
                correction=sym(v.T@(h-g)@v),
                formula_error=float(np.linalg.norm(f-q-v.T@(h-g)@v)))


def reference(h: np.ndarray, n: int, gamma: float) -> np.ndarray:
    """Independent algebraic Schur reference; no candidate or defect inputs."""
    return sym(h[n:, n:] - h[:n, n:].T @ np.linalg.solve(
        h[:n, :n]+gamma*np.eye(n), h[:n, n:]))


def update(f: np.ndarray, d: np.ndarray, w: np.ndarray, aw: np.ndarray) -> np.ndarray:
    """Inexact upgrade identity. No assumption that A W = D."""
    return sym(f-d.T@w-w.T@d+w.T@aw)


def numerical_mu(a: np.ndarray) -> dict:
    """Dense-assisted double-precision estimate, never a verified certificate.

    Residual/orthogonality/asymmetry and a roundoff margin are recorded. The
    margin is a numerical safeguard, NOT a rigorously rounded error enclosure.
    """
    if not np.isfinite(a).all():
        return dict(mu_value=None, bound_status='indicator_only', spd_status='nonfinite')
    scale = max(float(np.linalg.norm(a, 2)), np.finfo(float).tiny)
    asym = float(np.linalg.norm(a-a.T, 2))
    vals, vecs = np.linalg.eigh(sym(a))
    resid = float(np.linalg.norm(a@vecs-vecs*vals, 2))
    orth = float(np.linalg.norm(vecs.T@vecs-np.eye(len(a)), 2))
    margin = resid + orth*scale + asym/2 + 32*len(a)*np.finfo(float).eps*scale
    mu = float(vals[0]-margin)
    ok = mu > 0 and asym <= 1e-8*scale and orth < 1e-8
    return dict(mu_value=mu if ok else None, lambda_min_A_numeric=float(vals[0]),
                eigen_residual=resid, orthogonality_error=orth, symmetry_error=asym/scale,
                numerical_margin=margin, mu_source='dense_eigh_with_numerical_margin',
                bound_status='numerical_bound_estimate' if ok else 'indicator_only',
                spd_status='numerically_SPD' if ok else ('not_SPD' if vals[0] < -margin else 'spd_unresolved'))


def error_control(f: np.ndarray, d: np.ndarray, mu: float | None) -> dict:
    """Conditional absolute/spectral bound; relative bound only if ||F|| > U."""
    if mu is None or not np.isfinite(mu) or mu <= 0:
        return dict(U_absolute=None, U_relative_if_available=None, relative_status='mu_unresolved')
    u = float(np.linalg.norm(d, 2)**2/mu)
    scale = float(np.linalg.norm(f, 2))
    return dict(U_absolute=u, U_relative_if_available=u/(scale-u) if scale > u else None,
                relative_status='finite' if scale > u else 'no_finite_relative_guarantee')


def refine(a: np.ndarray, b: np.ndarray, c: np.ndarray, z: np.ndarray,
           mu: float | None, tolerance: float, budget: int) -> dict:
    """Dense-assisted diagonal PCG defect refinement, fixed matvec budget/RHS.

    Oracle-free stopping uses the conditional bound estimate. Multi-column
    iterations have no claimed Loewner monotonicity. Exact reference is absent.
    """
    if mu is None or mu <= 0:
        return dict(status='mu_unresolved', Z=z, trace=[], A_matvec_count=0)
    if not all(np.isfinite(x).all() for x in (a,b,c,z)):
        return dict(status='nonfinite', Z=z, trace=[], A_matvec_count=0)
    z = z.copy()
    d = b-a@z
    count = z.shape[1]
    r = d.copy(); q = r/np.diag(a)[:, None]; direction = q.copy()
    rq = np.sum(r*q, axis=0)
    trace = []
    for k in range(budget+1):
        f = quadratic(c,b,a,z)
        bounds = error_control(f,d,mu)
        trace.append(dict(iteration=k, defect_norm=float(np.linalg.norm(d)), **bounds))
        rel = bounds['U_relative_if_available']
        if rel is not None and rel <= tolerance:
            return dict(status='numerical_tolerance_met', Z=z, trace=trace, A_matvec_count=count)
        if k == budget:
            break
        ad = a@direction; count += z.shape[1]
        denom = np.sum(direction*ad,axis=0)
        active = rq > np.finfo(float).tiny
        if np.any(denom[active] <= 0):
            return dict(status='not_SPD', Z=z, trace=trace, A_matvec_count=count)
        alpha = np.divide(rq,denom,out=np.zeros_like(rq),where=active)
        z += direction*alpha
        r -= ad*alpha
        q = r/np.diag(a)[:,None]
        new = np.sum(r*q,axis=0)
        beta = np.divide(new,rq,out=np.zeros_like(new),where=active)
        direction = q+direction*beta; rq = new
        d = b-a@z; count += z.shape[1]  # explicitly verified defect; charged
    return dict(status='tolerance_not_met', Z=z, trace=trace, A_matvec_count=count)


def directional_operators(jvp: Callable, hvp: Callable, z: np.ndarray,
                          gamma: float) -> dict:
    """SO directional evaluation via caller JVP/HVP, no dense derivatives.

    Counts only this evaluation; GN solve and spectrum estimation are separate.
    """
    n,p = z.shape
    v = np.vstack((-z,np.eye(p)))
    jv = np.column_stack([jvp(v[:,i]) for i in range(p)])
    hv = np.column_stack([hvp(v[:,i]) for i in range(p)])
    return dict(Q_G=sym(jv.T@jv+gamma*z.T@z), F_SO=sym(v.T@hv+gamma*z.T@z),
                D=hv[:n]-gamma*z, jvp_count=p, hvp_count=p, vjp_count=0)
