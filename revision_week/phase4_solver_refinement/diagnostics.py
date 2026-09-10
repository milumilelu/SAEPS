"""Unified Phase 4 diagnostics for raw and proximal refinement states.

All quantities are computed against the same objective as the solve: Route R
diagnostics use the raw physical objective, Route P diagnostics use the
fixed-reference proximal objective L_gamma. H_raw always denotes the raw
physical objective's Hessian; the finite-damped A_fd = H_raw + gamma_analysis*I
with gamma_analysis = nominal_alpha * lambda_max(J_theta^T J_theta) evaluated
at the analyzed state, matching the Phase 2 analysis convention. Route P
additionally reports H_prox, the theta-block Hessian of the solved proximal
objective, and the exact identity H_prox - H_raw = gamma_solve * I.
"""
from __future__ import annotations
import numpy as np
import torch

from objective_adapter import residual_block_sizes, sha256_tensor
from core import numerical_mu, sym


def _safe_min(mu):
    value = mu.get('lambda_min_A_numeric')
    return float(value) if value is not None else None


def _safe_margin(mu):
    value = mu.get('numerical_margin')
    return float(value) if value is not None and np.isfinite(value) else None


def route_ell(residual, coordinate, gamma, anchor):
    """Route objective ell(theta) as a scalar torch function of theta."""
    def ell(t):
        base = 0.5 * residual(t, coordinate).square().sum()
        if gamma == 0.0:
            return base
        return base + 0.5 * gamma * (t - anchor).square().sum()
    return ell


def joint_matrices(residual, theta, coordinate, gamma, anchor):
    """Joint (theta, lambda) Hessians of the raw and route objectives.

    Returns (h_raw, h_route, J_theta). h_route equals h_raw for gamma=0 and
    equals h_raw with gamma*I added on the theta block for the proximal route.
    """
    n = theta.numel()
    joint = torch.cat((theta.detach(), coordinate.detach()))
    raw_ell = lambda j: 0.5 * residual(j[:n], j[n:]).square().sum()
    h_raw = torch.func.hessian(raw_ell)(joint).detach().numpy()

    def route_ell_joint(j):
        base = 0.5 * residual(j[:n], j[n:]).square().sum()
        if gamma == 0.0:
            return base
        return base + 0.5 * gamma * (j[:n] - anchor).square().sum()

    h_route = torch.func.hessian(route_ell_joint)(joint).detach().numpy()
    J = torch.func.jacrev(lambda j: residual(j[:n], j[n:]))(joint).detach().numpy()
    return h_raw, h_route, J[:, :n]


def block_eigen(matrix):
    """Eigen summary of a symmetric matrix via the project margin machinery."""
    mu = numerical_mu(sym(matrix))
    return dict(lambda_min=_safe_min(mu), spd_status=mu['spd_status'],
                margin=_safe_margin(mu),
                mu_value=None if mu['mu_value'] is None else float(mu['mu_value']))


def stability_block(h_raw_joint, n, gamma):
    """Raw theta-block plus its finite-damped variant with numerical margins."""
    H_raw = sym(h_raw_joint[:n, :n])
    A_fd = H_raw + gamma * np.eye(n)
    mu_raw = numerical_mu(H_raw)
    mu_fd = numerical_mu(A_fd)
    record = dict(gamma=gamma, H_raw_norm_2=float(np.linalg.norm(H_raw, 2)),
                  lambda_min_H_raw=_safe_min(mu_raw), H_raw_spd=mu_raw['spd_status'],
                  H_raw_margin=_safe_margin(mu_raw),
                  lambda_min_A_fd=_safe_min(mu_fd), A_fd_spd=mu_fd['spd_status'],
                  A_fd_margin=_safe_margin(mu_fd),
                  stability_pass=bool(mu_fd['mu_value'] is not None))
    return record, H_raw


def state_diagnostics(residual, theta, coordinate, gamma, anchor, route, alpha):
    """Complete diagnostic bundle for one state under the route objective."""
    theta = theta.detach().clone()
    anchor = anchor.detach().clone()
    ell = route_ell(residual, coordinate, gamma, anchor)
    raw_ell = lambda t: 0.5 * residual(t, coordinate).square().sum()
    r = residual(theta, coordinate)
    m = int(r.numel())
    n = int(theta.numel())
    loss_raw_sum = float(0.5 * r.square().sum())
    theta_norm = float(np.linalg.norm(theta.numpy()))
    displacement = float(np.linalg.norm((theta - anchor).numpy()))
    proximal_shift = gamma * (theta - anchor)
    route_gradient = torch.func.grad(ell)(theta).detach().numpy()
    raw_gradient = torch.func.grad(raw_ell)(theta).detach().numpy()
    normalized = float(np.linalg.norm(route_gradient) / (m * max(theta_norm, 1.0)))
    h_raw_joint, h_route_joint, J_theta = joint_matrices(residual, theta, coordinate, gamma, anchor)
    g_theta = sym(J_theta.T @ J_theta)
    lambda_max = float(np.linalg.eigvalsh(g_theta)[-1])
    gamma_analysis = alpha * lambda_max
    H_raw_record, H_raw = stability_block(h_raw_joint, n, gamma_analysis)
    H_prox = sym(h_route_joint[:n, :n])
    mu_prox = numerical_mu(H_prox)
    H_prox_record = dict(gamma_solve=gamma,
                         lambda_min_H_prox=_safe_min(mu_prox),
                         H_prox_spd=mu_prox['spd_status'],
                         H_prox_margin=_safe_margin(mu_prox),
                         proximal_stability_pass=bool(mu_prox['mu_value'] is not None))
    identity = dict(hessian_identity_residual_fro=float(np.linalg.norm(H_prox - H_raw - gamma * np.eye(n))),
                    hessian_identity_residual_max=float(np.max(np.abs(H_prox - H_raw - gamma * np.eye(n)))))
    scale = max(theta_norm, 1.0)
    if route == 'raw':
        A_target = H_raw + gamma_analysis * np.eye(n)
    else:
        A_target = H_prox
    diagnostics = dict(
        route=route, m=m, n=n, p=int(coordinate.numel()),
        loss_raw_sum=loss_raw_sum, loss_raw_mean=loss_raw_sum / m,
        proximal_term=0.5 * gamma * displacement ** 2 if route == 'P' else 0.0,
        proximal_gradient_norm=float(np.linalg.norm(proximal_shift.numpy())),
        route_gradient_sum_norm=float(np.linalg.norm(route_gradient)),
        raw_gradient_sum_norm=float(np.linalg.norm(raw_gradient)),
        normalized_gradient_route=normalized,
        lambda_max_state_block=lambda_max, gamma_analysis=gamma_analysis,
        H_raw=H_raw_record, H_prox=H_prox_record, hessian_identity=identity,
        theta_norm=theta_norm, theta_displacement=displacement,
        relative_theta_displacement=displacement / scale,
    )
    try:
        A_target = H_raw + gamma_analysis * np.eye(n) if route == 'R' else H_prox
        A_inverse_g = np.linalg.solve(A_target, route_gradient)
        diagnostics['eta_state'] = float(np.linalg.norm(A_inverse_g) / scale)
        diagnostics['eta_E'] = float(route_gradient @ A_inverse_g)
        diagnostics['eta_status'] = 'computed'
    except np.linalg.LinAlgError:
        diagnostics['eta_state'] = None
        diagnostics['eta_E'] = None
        diagnostics['eta_status'] = 'A_target_not_invertible'
    matrices = dict(H_raw_joint=h_raw_joint, H_route_joint=h_route_joint,
                    J_theta=J_theta, g_theta=g_theta, H_raw=H_raw, H_prox=H_prox,
                    route_gradient=route_gradient, raw_gradient=raw_gradient,
                    gamma_analysis=gamma_analysis)
    return diagnostics, matrices


def residual_blocks(residual, theta, coordinate, payload):
    """Weighted training-block norms at one state."""
    vector = residual(theta, coordinate).detach().cpu().numpy()
    blocks = residual_block_sizes(payload, torch.from_numpy(vector))
    if blocks is None:
        return dict(status='UNAVAILABLE', reason='block layout does not sum to residual length')
    parts = {}
    start = 0
    for name, size in blocks:
        chunk = vector[start:start + size]
        parts[name] = float(np.sqrt(float(np.sum(chunk ** 2))))
        start += size
    return dict(status='OK', blocks=parts)


def reduced_curvature(matrices, n, route, gamma_analysis):
    """F_star reduced Schur curvature of the route analysis objective."""
    h_route = matrices['H_route_joint']
    B = sym(h_route[:n, n:])
    C = sym(h_route[n:, n:])
    A = matrices['H_raw'] + gamma_analysis * np.eye(n) if route == 'raw' else matrices['H_prox']
    record = dict(A_damping='gamma_analysis' if route == 'raw' else 'gamma_solve',
                  A_lambda_min=block_eigen(A)['lambda_min'])
    try:
        F = sym(C - B.T @ np.linalg.solve(A, B))
        values = np.linalg.eigvalsh(F)
        record.update(F_star=[[float(v) for v in row] for row in F],
                      F_star_min=float(values[0]), F_star_max=float(values[-1]),
                      status='computed')
    except np.linalg.LinAlgError:
        record.update(F_star=None, status='A_target_not_invertible')
    return record


def curvature_record(center, route, stage, theta, matrices, diagnostics, prev_K, seconds, target):
    """K8/K10/K12 curvature checkpoint with drift against the previous one."""
    analysis_joint = matrices['H_raw_joint'] if route == 'raw' else matrices['H_route_joint']
    K = sym(analysis_joint)
    record = dict(center=center, route=route, stage=stage, target=target,
                  state_theta_sha256=sha256_tensor(theta),
                  loss_raw_sum=diagnostics['loss_raw_sum'],
                  normalized_gradient_route=diagnostics['normalized_gradient_route'],
                  gamma_analysis=diagnostics['gamma_analysis'],
                  seconds=seconds,
                  K_norms=dict(fro=float(np.linalg.norm(K, 'fro')),
                               spectral=float(np.linalg.norm(K, 2))),
                  K_eigen=block_eigen(K),
                  F_reduced=reduced_curvature(matrices, len(theta), route,
                                              diagnostics['gamma_analysis']))
    if prev_K is not None:
        fro = float(np.linalg.norm(K - prev_K, 'fro') / max(float(np.linalg.norm(K, 'fro')), 1.0))
        spectral = float(np.linalg.norm(K - prev_K, 2) / max(float(np.linalg.norm(K, 2)), 1.0))
        record['K_drift_vs_previous'] = dict(fro_relative=fro, spectral_relative=spectral,
                                             gate=0.05,
                                             stability_pass=bool(fro <= 0.05 and spectral <= 0.05))
    return record, K


def physical_fit(before_diag, after_diag, blocks_before, blocks_after, gates, route):
    """Physical-fit preservation relative changes and verdict."""
    total_before = float(before_diag['loss_raw_sum'])
    total_after = float(after_diag['loss_raw_sum'])
    relative = (total_after - total_before) / max(abs(total_before), 1e-30)
    record = dict(raw_total_before=total_before, raw_total_after=total_after,
                  raw_total_relative=relative,
                  raw_total_relative_max=gates['raw_total_loss_relative_increase_max'])
    anomaly = route == 'raw' and relative > gates['raw_total_loss_relative_increase_max']
    record['raw_total_anomaly_R'] = bool(anomaly)
    if blocks_before.get('status') == 'OK' and blocks_after.get('status') == 'OK':
        changes = {}
        for name, value_before in blocks_before['blocks'].items():
            value_after = float(blocks_after['blocks'][name])
            delta = (value_after - float(value_before)) / max(abs(float(value_before)), 1e-30)
            changes[name] = dict(before=float(value_before), after=value_after,
                                 relative=delta,
                                 relative_max=gates['any_training_block_relative_increase_max'],
                                 within=bool(delta <= gates['any_training_block_relative_increase_max']))
        record['blocks'] = changes
    else:
        record['blocks'] = dict(status='UNAVAILABLE',
                                reason='training-block layout unavailable at before or after state')
    record['validation_status'] = 'UNAVAILABLE'
    record['validation_reason'] = 'historical payload carries no validation data; not fabricated'
    fit_pass = not anomaly
    if route == 'proximal':
        fit_pass = fit_pass and relative <= gates['raw_total_loss_relative_increase_max']
        if isinstance(record['blocks'], dict) and 'status' not in record['blocks']:
            fit_pass = fit_pass and all(item['within'] for item in record['blocks'].values())
    record['fit_pass'] = bool(fit_pass)
    return record


def decide_terminal(route, stage1, diag_after, curvature, fit, solver_abort=None):
    """Terminal status and labels from the frozen decision precedence."""
    gradient_pass = bool(stage1['target_reached'])
    stability = (diag_after['H_prox']['proximal_stability_pass'] if route == 'proximal'
                 else diag_after['H_raw']['stability_pass'])
    raw_local_minimum = bool(diag_after['H_raw']['H_raw_spd'] == 'numerically_SPD')
    labels = dict(reference_gradient_pass=gradient_pass,
                  finite_damped_or_proximal_stability_pass=bool(stability),
                  curvature_stability=None,
                  physical_fit_preserved=bool(fit['fit_pass']),
                  REFERENCE_CAPABLE=False,
                  raw_local_minimum=False)
    if curvature['K10_saved'] and curvature.get('drift_pass'):
        labels['curvature_stability'] = 'STABLE'
    elif curvature['K10_saved']:
        labels['curvature_stability'] = 'UNSTABLE'
    else:
        labels['curvature_stability'] = 'UNRESOLVED'
    result = dict(status=None, failure_reason=None, labels=labels,
                  scientific_binding_valid=False)
    if gradient_pass:
        if not stability:
            result.update(status='STABILITY_FAIL',
                          failure_reason='route stability matrix not resolvably positive')
        elif labels['curvature_stability'] == 'UNRESOLVED':
            result.update(status='CURVATURE_STABILITY_UNRESOLVED',
                          failure_reason='1e-10 polish state not reached within the frozen stage budget')
        elif labels['curvature_stability'] == 'UNSTABLE':
            result.update(status='CURVATURE_UNSTABLE',
                          failure_reason='K10 vs K8 relative drift exceeds 0.05')
        elif not fit['fit_pass']:
            result.update(status='PHYSICAL_FIT_FAIL',
                          failure_reason='frozen physical-fit gate violated')
        else:
            result.update(status='PASS', failure_reason=None)
            labels['REFERENCE_CAPABLE'] = True
            labels['raw_local_minimum'] = bool(raw_local_minimum)
            result['scientific_binding_valid'] = True
    else:
        termination = str(stage1['termination'])
        if solver_abort is not None:
            result.update(status='NUMERICAL_FAILURE',
                          failure_reason=f'solver abort: {termination}')
        elif termination in ('nfev_budget_exhausted', 'wall_budget_exhausted'):
            result.update(status='RESOURCE_LIMIT', failure_reason=termination)
        elif termination.startswith('scipy_stop'):
            message = str(stage1.get('scipy_stop', {}).get('message', ''))
            result.update(status='STATIONARITY_FAIL',
                          failure_reason='gradient stagnation: scipy stopped on its own criteria; ' + message)
        else:
            result.update(status='NUMERICAL_FAILURE', failure_reason='unclassified termination: ' + termination)
    return result
