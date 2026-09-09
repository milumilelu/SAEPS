"""P1B-D: minimal one-step parameter-update pilot on the two predetermined controls.

Implements revision_week/outputs/day2/PHASE1B_PROTOCOL.yaml exactly (frozen
before this run). Roots: burgers_55, allen_cahn_84 (controls; no replacement).
Methods RAW / SAEPS-GN / SO / EXACT-REDUCED-ORACLE differ only in the scalar
reduced curvature F_m used by the protected step; candidate state solves and
initialization are shared (GN predictor). SO-ADAPT excluded. Objective decrease
and true parameter error are reported separately.
"""
from __future__ import annotations
import os
for key in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS']:
    os.environ[key] = '1'
import csv, hashlib, json, math, platform, subprocess, sys, time
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'src'))
from saeps.config import load_config  # noqa: E402
from saeps.p5_confirmation import _runtime_config  # noqa: E402
from saeps.scalar import make_scalar_points, solve_truth, scalar_residual  # noqa: E402
import posthoc_exact_fixed_state_v1 as v1  # noqa: E402  (tested curvature_blocks)

OUT = ROOT / 'revision_week/outputs/day2'
REC = OUT / 'recovery'
RUN_ID, EXPERIMENT_ID = 'day2', 'P1B_D'
TASK_BOOK = Path(r'C:/Users/RZF/Desktop/博士课题资料/SAEPS/任务说明/CODEX_SAEPS_PHASE1B_FOLLOWUP.md')
ROOTS = ['burgers_55', 'allen_cahn_84']
METHODS = ['RAW', 'SAEPS-GN', 'SO', 'EXACT-REDUCED-ORACLE']
DELTA = 0.05
TRUST_RADIUS = 0.1
COEFFICIENTS = [1.0, 0.5]
ARMIJO_C1 = 1e-4
BETA_RULE = 1e-6
INNER_SOLVE_CAP_S = 300
MAX_CANDIDATE_SOLVES = 32
TOTAL_BUDGET_S = 2 * 60 * 60


def digest(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save_json(p: Path, obj) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    tmp.replace(p)


def _git(*args) -> str:
    r = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True)
    return r.stdout.decode('utf-8', errors='replace').strip()


def schur(tl, ll, tt, gamma):
    n = tt.shape[0]
    return float(ll[0, 0]) - float(tl.T @ np.linalg.solve(tt + gamma * np.eye(n), tl))


class Counters:
    def __init__(self):
        self.objective_evals = 0
        self.gradient_evals = 0
        self.solve_seconds = 0.0
        self.converged = False
        self.hit_cap = False


def profile_solve(residual, theta_c, lam_value, gamma, theta_init, gate_norm, cap_s=INNER_SOLVE_CAP_S):
    """Shared candidate/start solver: LBFGS on theta for L_gamma at fixed lambda."""
    cnt = Counters()
    theta = theta_init.detach().clone().requires_grad_(True)
    lam = torch.tensor([float(lam_value)], dtype=torch.float64)

    def anchored(th: torch.Tensor) -> torch.Tensor:
        r = residual(th, lam)
        return 0.5 * torch.sum(r.square()) + 0.5 * gamma * torch.sum((th - theta_c) ** 2)

    opt = torch.optim.LBFGS([theta], max_iter=300, tolerance_grad=1e-10,
                            tolerance_change=1e-16, history_size=100, line_search_fn='strong_wolfe')
    t0 = time.perf_counter()

    def closure():
        cnt.objective_evals += 1
        opt.zero_grad(set_to_none=True)
        loss = anchored(theta)
        loss.backward()
        cnt.gradient_evals += 1
        return loss

    opt.step(closure)
    cnt.solve_seconds = time.perf_counter() - t0
    cnt.hit_cap = cnt.solve_seconds > cap_s
    with torch.no_grad():
        r = residual(theta, lam)
        m_count = float(r.numel())
        cnt.final_loss = float(anchored(theta).item())
        cnt.theta = theta.detach().clone()
    g = torch.autograd.grad(anchored(theta), theta)[0]
    cnt.final_grad_norm = float(torch.linalg.vector_norm(g))
    # stationarity gates use the historical mean-form convention:
    # normalized gradient of 0.5*mean(r^2) = sum-gradient / m_count
    cnt.final_grad_normalized = (cnt.final_grad_norm / m_count) / max(float(torch.linalg.vector_norm(theta.detach())), 1.0)
    cnt.converged = bool(cnt.final_grad_normalized <= gate_norm)
    return cnt


def main() -> int:
    started = time.perf_counter()
    torch.set_default_dtype(torch.float64)
    torch.set_num_threads(1)
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    candidate_solves = 0
    start_solves = 0
    refinements = 0
    cost_notes = []

    for root_id in ROOTS:
        name = root_id.rsplit('_', 1)[0]
        seed = int(root_id.rsplit('_', 1)[1])
        ck = np.load(REC / root_id / 'state_checkpoint.npz')
        prov = json.loads((REC / root_id / 'provenance.json').read_text(encoding='utf-8'))
        if name == 'burgers':
            v42 = load_config(ROOT / 'configs/v4_2/locked_corrected_confirmation.yaml')
            v36 = load_config(ROOT / v42['source_v3_6_scientific_protocol']['path'])
            scalar = load_config(ROOT / v36['source_files']['scalar_config']['path'])
            runtime = _runtime_config(scalar)
            curvature_cfg, gate_key_cfg = v36, v36
            truth = solve_truth(runtime, 'Burgers')
            gate_grad = float(curvature_cfg['center']['required_objective_gradient_tolerance'])
        else:
            spec = load_config(ROOT / 'configs/v4_4/locked_allen_cahn_confirmation.yaml')
            runtime = load_config(ROOT / spec['protected_sources']['scalar_runtime']['path'])
            runtime['network']['hidden_width'] = 8
            curvature_cfg = load_config(ROOT / spec['protected_sources']['curvature_protocol']['path'])
            gate_grad = float(curvature_cfg['center']['required_objective_gradient_tolerance'])
            truth = solve_truth(runtime, 'Allen-Cahn')
        points = make_scalar_points(runtime, seed)
        bench = 'Burgers' if name == 'burgers' else 'Allen-Cahn'

        def residual(th: torch.Tensor, lp: torch.Tensor) -> torch.Tensor:
            return scalar_residual(th, lp, bench, points, truth, runtime)

        theta_c = torch.tensor(ck['theta'], dtype=torch.float64)
        lam_c = float(ck['log_parameter'][0])
        gamma = float(ck['gamma'])
        z_g = ck['gn_response_Z']  # (n,1) GN state response at the root
        g_tt, g_tl, g_ll = ck['G_tt'], ck['G_tl'], ck['G_ll']
        h_tt, h_tl, h_ll = ck['H_tt_sym'], ck['H_tl'], ck['H_ll']
        n = theta_c.numel()
        truth_parameter = float(runtime['benchmarks'][bench]['truth_parameter'])
        lambda_phys_c = float(torch.exp(torch.tensor(lam_c)))
        param_err_before = abs(lambda_phys_c - truth_parameter) / truth_parameter

        # --- root qualification (frozen gates; anchored state gradient at root) ---
        lam0 = torch.tensor([lam_c], dtype=torch.float64)
        res0 = residual(theta_c, lam0)
        m_count = float(res0.numel())
        th0 = theta_c.clone().requires_grad_(True)
        loss0 = 0.5 * torch.sum(residual(th0, lam0).square())  # anchor term is 0 at theta_c
        g_state_root = torch.autograd.grad(loss0, th0)[0]
        root_state_grad_norm = float(torch.linalg.vector_norm(g_state_root))
        # historical center-gate convention: normalized gradient of the MEAN objective
        root_state_grad_normalized = (root_state_grad_norm / m_count) / max(float(torch.linalg.vector_norm(theta_c)), 1.0)
        lam_grad_probe = torch.tensor([lam_c], dtype=torch.float64).requires_grad_(True)
        loss_probe = 0.5 * torch.sum(residual(theta_c, lam_grad_probe).square())
        g_lambda_root = float(torch.autograd.grad(loss_probe, lam_grad_probe)[0][0])
        ck_g_lambda = float(ck['gradient_lambda_sum_objective'][0])
        g_lambda = g_lambda_root
        gradient_consistency = abs(g_lambda - ck_g_lambda) / max(abs(g_lambda), 1e-30)

        t_curv0 = time.perf_counter()
        f_raw = float(g_ll[0, 0])
        f_gn = schur(g_tl, g_ll, g_tt, gamma)
        a_mat = h_tt + gamma * np.eye(n)
        z_g_mat = z_g
        f_so = float(h_ll[0, 0]) - float(h_tl.T @ z_g_mat) - float(z_g_mat.T @ h_tl) + float(z_g_mat.T @ a_mat @ z_g_mat)
        f_oracle = schur(h_tl, h_ll, h_tt, gamma)
        curv_cost = time.perf_counter() - t_curv0
        beta = BETA_RULE * max(f_raw, 1e-8)
        curvatures = dict(zip(METHODS, [f_raw, f_gn, f_so, f_oracle]))
        moved = {m: curvatures[m] + beta for m in METHODS}
        root_qualified = (root_state_grad_normalized <= gate_grad) and all(v > 0 for v in moved.values())

        # objective-eval noise (same inputs twice)
        phi_noise = abs(float((0.5 * torch.sum(residual(theta_c, lam0).square())).item())
                        - float((0.5 * torch.sum(residual(theta_c, lam0).square())).item()))

        cost_notes.append(dict(root_id=root_id, kind='root_qualification',
                               root_state_grad_normalized=root_state_grad_normalized,
                               root_state_grad_norm_sum_form=root_state_grad_norm,
                               residual_count_m=m_count, gate=gate_grad,
                               gradient_consistency=gradient_consistency,
                               curvatures=curvatures, moved=moved, beta=beta, g_lambda=g_lambda,
                               param_err_before=param_err_before, qualified=root_qualified))

        if not root_qualified:
            for sign in (+1, -1):
                for m in METHODS:
                    rows.append(dict(run_id=RUN_ID, root_id=root_id, offset_id=f'{sign * DELTA:+.2f}', method=m,
                                     start_valid=False, step_accepted=False, failure_reason='root_not_qualified',
                                     branch_consistency_status='n/a'))
            continue

        for sign in (+1, -1):
            offset_id = f'{sign * DELTA:+.2f}'
            lam_s = lam_c + sign * DELTA
            # --- common start solve (shared by all methods) ---
            theta_init_s = theta_c - torch.tensor(z_g[:, 0], dtype=torch.float64) * (sign * DELTA)
            start = profile_solve(residual, theta_c, lam_s, gamma, theta_init_s, gate_grad)
            start_solves += 1
            cost_notes.append(dict(root_id=root_id, offset_id=offset_id, kind='common_start',
                                   seconds=start.solve_seconds, converged=start.converged,
                                   final_grad_normalized=start.final_grad_normalized))
            start_valid = bool(start.converged and not start.hit_cap)
            param_err_start = abs(float(torch.exp(torch.tensor(lam_s))) - truth_parameter) / truth_parameter
            if not start_valid:
                for m in METHODS:
                    rows.append(dict(run_id=RUN_ID, root_id=root_id, offset_id=offset_id, method=m,
                                     start_valid=False, raw_step=None, shift_beta=None, clipped_step=None,
                                     trust_radius_active=None, trial_coefficient=None, predicted_decrease=None,
                                     actual_profile_decrease=None, actual_predicted_ratio_if_resolved=None,
                                     parameter_error_before=param_err_start, parameter_error_after=None,
                                     step_accepted=False, candidate_state_valid=False,
                                     branch_consistency_status='common_start_failed',
                                     objective_evals=start.objective_evals, gradient_evals=start.gradient_evals,
                                     HVP_count=0, curvature_cost=None, candidate_solve_cost=start.solve_seconds,
                                     total_cost=start.solve_seconds, failure_reason='common_start_failed'))
                continue
            theta_s = start.theta
            phi_start = start.final_loss

            # --- curvatures, lambda-gradient and GN response AT the start ---
            # (fresh from the real residual; identical quantity family as day1,
            #  never loaded from historical records)
            t_curv0 = time.perf_counter()
            blocks_s = v1.curvature_blocks(residual, theta_s, torch.tensor([lam_s], dtype=torch.float64), gamma)
            g_tt_s = np.asarray(blocks_s['G_tt_tensor'])
            g_tl_s = np.asarray(blocks_s['G_tl_tensor'])
            g_ll_s = np.asarray(blocks_s['G_ll_tensor'])
            h_tt_s = np.asarray(blocks_s['H_tt_sym_tensor'])
            h_tl_s = np.asarray(blocks_s['H_tl_tensor'])
            h_ll_s = np.asarray(blocks_s['H_ll_tensor'])
            z_g_s = np.asarray(blocks_s['gn_solution_tensor'])  # GN response AT the start
            lam_probe = torch.tensor([lam_s], dtype=torch.float64).requires_grad_(True)
            g_lambda_s = float(torch.autograd.grad(0.5 * torch.sum(residual(theta_s, lam_probe).square()), lam_probe)[0][0])
            f_raw_s = float(g_ll_s[0, 0])
            f_gn_s = schur(g_tl_s, g_ll_s, g_tt_s, gamma)
            a_s = h_tt_s + gamma * np.eye(n)
            zc = z_g_s
            f_so_s = (float(h_ll_s[0, 0]) - float(h_tl_s.T @ zc) - float(zc.T @ h_tl_s)
                      + float(zc.T @ a_s @ zc))
            f_oracle_s = schur(h_tl_s, h_ll_s, h_tt_s, gamma)
            beta_s = BETA_RULE * max(f_raw_s, 1e-8)
            curvatures_s = dict(zip(METHODS, [f_raw_s, f_gn_s, f_so_s, f_oracle_s]))
            moved_s = {m: curvatures_s[m] + beta_s for m in METHODS}
            curv_cost_s = time.perf_counter() - t_curv0
            cost_notes.append(dict(root_id=root_id, offset_id=offset_id, kind='start_curvature',
                                   seconds=curv_cost_s, curvatures=curvatures_s, moved=moved_s,
                                   beta=beta_s, g_lambda_start=g_lambda_s,
                                   param_err_start=param_err_start))

            for m in METHODS:
                row = dict(run_id=RUN_ID, root_id=root_id, offset_id=offset_id, method=m,
                           start_valid=True, raw_step=None, shift_beta=beta_s,
                           clipped_step=None, trust_radius_active=None, trial_coefficient=None,
                           predicted_decrease=None, actual_profile_decrease=None,
                           actual_predicted_ratio_if_resolved=None,
                           parameter_error_before=param_err_start, parameter_error_after=None,
                           step_accepted=False, candidate_state_valid=False,
                           branch_consistency_status='consistent',
                           objective_evals=0, gradient_evals=0, HVP_count=0,
                           curvature_cost=curv_cost_s, candidate_solve_cost=0.0, total_cost=None,
                           failure_reason=None)
                f_m = curvatures_s[m]
                d_raw = -g_lambda_s / moved_s[m]
                row['raw_step'] = abs(d_raw)
                row['signed_raw_step'] = d_raw
                d_clip = float(np.clip(d_raw, -TRUST_RADIUS, TRUST_RADIUS))
                row['clipped_step'] = d_clip
                row['trust_radius_active'] = bool(abs(d_raw) > TRUST_RADIUS)
                accepted = False
                cand_cost = 0.0
                for coef in COEFFICIENTS:
                    if candidate_solves >= MAX_CANDIDATE_SOLVES:
                        row['failure_reason'] = 'budget_exhausted'
                        break
                    dl = coef * d_clip
                    lam_t = lam_s + dl  # step FROM the common start
                    theta_init = theta_s - torch.tensor(z_g_s[:, 0], dtype=torch.float64) * dl
                    cand = profile_solve(residual, theta_c, lam_t, gamma, theta_init, gate_grad)
                    candidate_solves += 1
                    cand_cost += cand.solve_seconds
                    row['objective_evals'] += cand.objective_evals
                    row['gradient_evals'] += cand.gradient_evals
                    phi_before = phi_start  # L_gamma(theta_s, lam_s), anchor at theta_c
                    phi_after = cand.final_loss
                    pred = -(dl * g_lambda_s + 0.5 * dl * dl * f_m)
                    actual = phi_before - phi_after
                    row['trial_coefficient'] = coef
                    row['predicted_decrease'] = pred
                    row['actual_profile_decrease'] = actual
                    if abs(actual) > max(phi_noise, 0.0) and abs(pred) > 1e-30:
                        row['actual_predicted_ratio_if_resolved'] = actual / pred
                    lam_t_phys = float(torch.exp(torch.tensor(lam_t)))
                    row['parameter_error_after'] = abs(lam_t_phys - truth_parameter) / truth_parameter
                    row['candidate_state_valid'] = bool(cand.converged and not cand.hit_cap)
                    row['trial_lambda'] = lam_t
                    row['phi_noise_estimate'] = phi_noise
                    if cand.converged and pred > 0 and (actual >= ARMIJO_C1 * pred):
                        accepted = True
                        break
                row['step_accepted'] = accepted
                row['candidate_solve_cost'] = cand_cost
                row['total_cost'] = cand_cost + curv_cost_s
                if not accepted and row['failure_reason'] is None:
                    row['failure_reason'] = 'step_rejected_both_coefficients'
                rows.append(row)
                print(json.dumps({k: row.get(k) for k in ('root_id', 'offset_id', 'method', 'raw_step',
                                                          'clipped_step', 'trial_coefficient', 'predicted_decrease',
                                                          'actual_profile_decrease', 'step_accepted',
                                                          'parameter_error_before', 'parameter_error_after',
                                                          'failure_reason')}, ensure_ascii=False), flush=True)
                if time.perf_counter() - started > TOTAL_BUDGET_S:
                    print(json.dumps(dict(status='budget_exhausted')), flush=True)
                    break
            if time.perf_counter() - started > TOTAL_BUDGET_S:
                break

    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (OUT / 'ONE_STEP_PILOT.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    save_json(OUT / 'p1b_d_summary.json', dict(
        run_id=RUN_ID, experiment_id=EXPERIMENT_ID, parent_commit=_git('rev-parse', 'HEAD'),
        task_book_sha256=digest(TASK_BOOK), protocol_sha256=digest(OUT / 'PHASE1B_PROTOCOL.yaml'),
        roots=ROOTS, methods=METHODS, delta=DELTA, trust_radius=TRUST_RADIUS,
        coefficients=COEFFICIENTS, armijo_c1=ARMIJO_C1, beta_rule=BETA_RULE,
        rows=len(rows), candidate_solves=candidate_solves, start_solves=start_solves,
        refinements=refinements, cost_notes=cost_notes,
        wall_seconds=time.perf_counter() - started,
        environment=dict(python=platform.python_version(), torch=torch.__version__,
                         numpy=np.__version__, threads=1, device='cpu'),
    ))
    print(json.dumps(dict(rows=len(rows), candidate_solves=candidate_solves,
                          start_solves=start_solves, wall=time.perf_counter() - started), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
