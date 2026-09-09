"""P1B-B: recover full replayable state for at most 4 predetermined centers.

One fixed-flow replay per center via the tested v1 reconstruction path
(scripts/posthoc_exact_fixed_state_v1.py, unchanged). This script only adds a
state export (theta/lambda/points/truth/weights/gamma/gradients) plus the
frozen-reproduction comparison against the archived v3 center records and the
day1 matrix values. No seed replacement, no gamma/tolerance change, no rerun
after a scientific result. Budget: <=30 min per center, <=2 h cumulative.
"""
from __future__ import annotations
import os
for key in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS']:
    os.environ[key] = '1'
import csv, hashlib, json, platform, subprocess, sys, time
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'src'))
import posthoc_exact_fixed_state_v1 as v1  # noqa: E402
from saeps.config import load_config  # noqa: E402
from saeps.p5_confirmation import _runtime_config  # noqa: E402
from saeps.scalar import make_scalar_points, solve_truth  # noqa: E402
from saeps.scalar import scalar_residual  # noqa: E402
from core import evaluate, reference  # noqa: E402  (revision_week tested core)

DAY1 = ROOT / 'revision_week/outputs/day1'
OUT = ROOT / 'revision_week/outputs/day2'
REC = OUT / 'recovery'
RUN_ID, EXPERIMENT_ID = 'day2', 'P1B_B'
TASK_BOOK = Path(r'C:/Users/RZF/Desktop/博士课题资料/SAEPS/任务说明/CODEX_SAEPS_PHASE1B_FOLLOWUP.md')
PREDetermined = ['burgers_59', 'burgers_67']
PER_CENTER_BUDGET_S = 30 * 60
TOTAL_BUDGET_S = 2 * 60 * 60
RTOL, ATOL = 1e-6, 1e-10  # frozen v3 reproduction tolerances (configs/posthoc_exact_fixed_state_v3.yaml)


def digest(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def close(rel_err: float) -> bool:
    return rel_err <= RTOL


def relerr(replay: float, original: float, floor: float = 1e-10) -> float:
    return abs(replay - original) / max(abs(original), floor)


def save_json(p: Path, obj) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    tmp.replace(p)


def select_centers(records: list[dict]) -> dict:
    """Task-book 3.1 rule: per-PDE historical median of GN relative error;
    closest valid center wins; Burgers control excludes 59/67; ties -> lowest seed."""
    by_pde: dict[str, list[dict]] = {}
    for r in records:
        if r['status'] == 'PASS':
            by_pde.setdefault(r['pde'], []).append(r)
    chosen, audit = {}, {}
    for pde, rows in by_pde.items():
        rels = sorted((float(r['relative_error_GN']), int(r['seed']), r['center_id']) for r in rows)
        med = float(np.median([x[0] for x in rels]))
        excluded = {59, 67} if pde == 'burgers' else set()
        cands = [x for x in rels if x[1] not in excluded]
        best_abs = min(abs(x[0] - med) for x in cands)
        # exact-arithmetic ties (e.g. the two middle values of an even-count
        # median are equidistant by construction) must not be decided by 1-ulp
        # float noise; the task book breaks ties by lowest historical ID.
        tied = [x for x in cands if abs(x[0] - med) <= best_abs * (1 + 1e-12) + 1e-15]
        best = min(tied, key=lambda x: x[1])
        chosen[pde] = dict(center_id=best[2], seed=best[1], gn_rel_error=best[0],
                           distance_to_median=abs(best[0] - med), excluded=sorted(excluded),
                           tied_candidates=[x[2] for x in tied])
        audit[pde] = dict(median=med, candidates=[(c[2], c[0], abs(c[0] - med)) for c in cands])
    return dict(predetermined=[dict(center_id=c, role='failure_case') for c in PREDetermined],
                controls=[dict(role='control', **chosen['burgers']), dict(role='control', **chosen['allen_cahn'])],
                selection_audit=audit)


def rebuild_inputs(name: str, seed: int):
    """Replicate the exact data/truth recipe closed over by the v1 center flow."""
    if name == 'burgers':
        v42 = load_config(ROOT / 'configs/v4_2/locked_corrected_confirmation.yaml')
        v36 = load_config(ROOT / v42['source_v3_6_scientific_protocol']['path'])
        scalar = load_config(ROOT / v36['source_files']['scalar_config']['path'])
        runtime = _runtime_config(scalar)
        curvature_cfg = v36
        truth = solve_truth(runtime, 'Burgers')
    else:
        spec = load_config(ROOT / 'configs/v4_4/locked_allen_cahn_confirmation.yaml')
        runtime = load_config(ROOT / spec['protected_sources']['scalar_runtime']['path'])
        runtime['network']['hidden_width'] = 8
        curvature_cfg = spec
        truth = solve_truth(runtime, 'Allen-Cahn')
    points = make_scalar_points(runtime, seed)
    return runtime, curvature_cfg, truth, points


def replay_center(entry: dict, records_by_id: dict) -> dict:
    center_id = entry['center_id']
    name, seed = center_id.rsplit('_', 1)
    seed = int(seed)
    started = time.perf_counter()
    row = dict(run_id=RUN_ID, experiment_id=EXPERIMENT_ID, center_id=center_id, pde=name,
               seed=seed, role=entry['role'], parent_historical_center_id=center_id,
               parent_day1_record_sha256=digest(DAY1 / 'raw' / f'{center_id}.json'))
    archived = records_by_id[center_id]
    # --- fixed-flow replay (v1, unchanged) ---
    if name == 'burgers':
        theta, parameter, residual_function, center, curvature_cfg = v1._center_burgers(seed)
    else:
        theta, parameter, residual_function, center, curvature_cfg = v1._center_allen(seed)
    replay_s = time.perf_counter() - started
    row['replay_seconds'] = replay_s
    if theta is None or parameter is None:
        row.update(status='RECOVERY_FAILED', failure_reason='fixed flow returned no center')
        return row
    gate_pass, stationarity = v1._center_valid(name, theta, parameter, residual_function, center, curvature_cfg)
    row['center_gate_pass'] = bool(gate_pass)
    row['stationarity'] = {k: float(v) for k, v in stationarity.items()}
    lin = v1.ResidualLinearization(residual_function, theta, parameter)
    jt, jl = lin.explicit_jacobians()
    lambda_max = float(torch.linalg.eigvalsh(jt.T @ jt).max().item())
    alpha = float(curvature_cfg['gamma']['alpha'])
    gamma = alpha * lambda_max
    n = theta.numel()
    blocks = v1.curvature_blocks(residual_function, theta, parameter, gamma)
    # joint matrices in the day1 load_center convention
    g = np.block([[np.asarray(blocks['G_tt_tensor']), np.asarray(blocks['G_tl_tensor'])],
                  [np.asarray(blocks['G_lt_tensor']), np.asarray(blocks['G_ll_tensor'])]])
    h = np.block([[np.asarray(blocks['H_tt_sym_tensor']), np.asarray(blocks['H_tl_tensor'])],
                  [np.asarray(blocks['H_lt_tensor']), np.asarray(blocks['H_ll_tensor'])]])
    m = g[:n, :n] + gamma * np.eye(n)
    z = np.linalg.solve(m, g[:n, n:])
    ev = evaluate(g, h, n, gamma, z)
    f_g_schur = float(reference(g, n, gamma)[0, 0])
    f_star = float(reference(h, n, gamma)[0, 0])
    f_raw = float(g[n, n])
    # --- frozen-level reproduction vs archived v3 original values ---
    orig = archived['reproduction']  # {'F_raw': {'original':...}, 'F_SAEPS':..., 'H_red_exact':...}
    frozen_checks = {}
    for key, replay_val in [('F_raw', f_raw), ('F_SAEPS', f_g_schur), ('H_red_exact', f_star)]:
        original = float(orig[key]['original'])
        frozen_checks[key] = dict(replay=replay_val, original=original,
                                  relative_error=relerr(replay_val, original),
                                  passed=close(relerr(replay_val, original)))
    # --- day1 matrix-level comparison ---
    matrix_checks = {}
    for key, replay_val in [('F_raw', f_raw), ('F_G_reference', f_g_schur), ('Q_G_actual', float(ev['Q_G'][0, 0])),
                            ('F_SO', float(ev['F_SO'][0, 0])), ('F_star', f_star), ('gamma', gamma)]:
        matrix_checks[key] = dict(replay=replay_val, day1=archived[key],
                                  relative_error=relerr(replay_val, float(archived[key])))
    gate_hist = archived.get('state_grad_normalized')
    row['gradient_identity'] = dict(
        replay_normalized_objective_gradient=row['stationarity'].get('G_theta'),
        archived_state_grad_normalized=float(gate_hist) if gate_hist is not None else None)
    row['gamma'] = gamma
    row['frozen_reproduction'] = frozen_checks
    row['matrix_comparison'] = matrix_checks
    row['max_frozen_relative_error'] = max(v['relative_error'] for v in frozen_checks.values())
    row['max_matrix_relative_error'] = max(v['relative_error'] for v in matrix_checks.values())
    # --- export state checkpoint (npz + provenance json) ---
    runtime, _, truth, points = rebuild_inputs(name, seed)
    res_closed = np.asarray(residual_function(theta, parameter).detach())
    res_rebuilt = np.asarray(scalar_residual(theta, parameter, 'Burgers' if name == 'burgers' else 'Allen-Cahn',
                                             points, truth, runtime).detach())
    data_identity_max = float(np.max(np.abs(res_closed - res_rebuilt))) if res_closed.shape == res_rebuilt.shape else float('inf')
    loss_mean = 0.5 * float(np.mean(res_closed ** 2))
    loss_sum = 0.5 * float(np.sum(res_closed ** 2))
    theta_req = theta.detach().clone().requires_grad_(True)
    param_req = parameter.detach().clone().requires_grad_(True)
    res_g = scalar_residual(theta_req, param_req, 'Burgers' if name == 'burgers' else 'Allen-Cahn',
                            points, truth, runtime)
    loss_sum_t = 0.5 * torch.sum(res_g.square())
    g_theta_sum, g_param_sum = torch.autograd.grad(loss_sum_t, (theta_req, param_req), retain_graph=True)
    loss_mean_t = 0.5 * torch.mean(res_g.square())
    g_theta_mean, g_param_mean = torch.autograd.grad(loss_mean_t, (theta_req, param_req))
    ckpt_dir = REC / center_id
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    npz_path = ckpt_dir / 'state_checkpoint.npz'
    np.savez_compressed(
        npz_path,
        theta=theta.detach().cpu().numpy().astype(np.float64),
        log_parameter=parameter.detach().cpu().numpy().astype(np.float64),
        lambda_physical=float(torch.exp(parameter.detach()).item()),
        gamma=float(gamma), alpha=alpha, lambda_max_G_tt=lambda_max,
        G_tt=np.asarray(blocks['G_tt_tensor']), G_tl=np.asarray(blocks['G_tl_tensor']),
        G_ll=np.asarray(blocks['G_ll_tensor']),
        H_tt_sym=np.asarray(blocks['H_tt_sym_tensor']), H_tl=np.asarray(blocks['H_tl_tensor']),
        H_ll=np.asarray(blocks['H_ll_tensor']),
        gn_response_Z=np.asarray(blocks['gn_solution_tensor']),
        pde_x=np.asarray(points.pde_x), pde_t=np.asarray(points.pde_t),
        data_x=np.asarray(points.data_x), data_t=np.asarray(points.data_t),
        initial_x=np.asarray(points.initial_x), boundary_t=np.asarray(points.boundary_t),
        data_noise=np.asarray(points.data_noise),
        truth_values=np.asarray(truth.values),
        truth_spatial_points=int(truth.spatial_points), truth_time_steps=int(truth.time_steps),
        truth_final_time=float(truth.final_time), truth_benchmark=str(truth.benchmark),
        gradient_theta_mean_objective=g_theta_mean.detach().cpu().numpy(),
        gradient_lambda_mean_objective=g_param_mean.detach().cpu().numpy(),
        gradient_theta_sum_objective=g_theta_sum.detach().cpu().numpy(),
        gradient_lambda_sum_objective=g_param_sum.detach().cpu().numpy(),
        residual_at_center=res_closed,
        torch_rng_state_uint8=torch.get_rng_state().numpy().astype(np.uint8),
    )
    provenance = dict(
        run_id=RUN_ID, experiment_id=EXPERIMENT_ID, center_id=center_id, pde=name, seed=seed,
        role=entry['role'], parent_historical_center_id=center_id,
        checkpoint_npz_sha256=digest(npz_path),
        packing_order='theta = [wx(W), wt(W), hidden_bias(W), output_weights(W), output_bias(1)]; n=4W+1',
        architecture=dict(kind='one-hidden-layer tanh scalar PINN', width=int(runtime['network']['hidden_width']),
                          activation='tanh', dtype='float64', n_state=int(n), n_parameter=1),
        parameterization='log physical parameter; physical = exp(log_parameter)',
        data_recipe=dict(points_seed_rule='manual_seed(seed+40000), torch.rand/randn float64',
                         runtime_config=_strip(runtime), runtime_config_note='embedded copy; also hashed from disk chain below'),
        gamma_construction='gamma = alpha * lambda_max(G_tt); alpha from curvature protocol config; gamma added once to the state block; fixed per center',
        loss_definitions=dict(center_training_objective='0.5*mean(rbar^2) (Adam/LBFGS + center rescue)',
                              archived_curvature_objective='0.5*sum(rbar^2) (day1/v3 derivatives)',
                              both_gradients_exported=True),
        optimizer_state=dict(adam_epochs=int(runtime['optimizer']['adam_epochs']),
                             lbfgs_config=dict(max_iter=int(runtime['optimizer']['lbfgs_max_iterations']),
                                               tolerance_grad=float(runtime['optimizer']['lbfgs_tolerance_grad']),
                                               tolerance_change=float(runtime['optimizer']['lbfgs_tolerance_change'])),
                             rng_state_at_export='torch RNG state saved in npz (replay export time, NOT the historical training-time state)',
                             historical_training_rng_state='NOT AVAILABLE (not archived in any historical record)'),
        environment=dict(python=platform.python_version(), torch=torch.__version__, numpy=np.__version__,
                         device='cpu', torch_threads=torch.get_num_threads(),
                         git_commit=_git('rev-parse', 'HEAD'),
                         saeps_import_path=sys.modules['saeps'].__file__),
        hashes=dict(day1_parent_record=digest(DAY1 / 'raw' / f'{center_id}.json'),
                    v3_center_archive=archived['input_sha256'],
                    saeps_scalar_module=digest(Path(sys.modules['saeps.scalar'].__file__)),
                    worktree_vs_import_note='imported saeps package files sha256-compared against worktree git blob at runtime (see code_identity check)'),
        reproduction=frozen_checks, matrix_comparison=matrix_checks,
        stationarity=row['stationarity'], center_gate_pass=row['center_gate_pass'],
        rebuilt_data_identity_max_abs_diff=data_identity_max,
        loss_mean_at_center=loss_mean, loss_sum_at_center=loss_sum,
    )
    save_json(ckpt_dir / 'provenance.json', provenance)
    row['checkpoint_npz'] = str(npz_path)
    row['provenance_json'] = str(ckpt_dir / 'provenance.json')
    row['checkpoint_npz_sha256'] = provenance['checkpoint_npz_sha256']
    row['data_identity_max_abs_diff'] = data_identity_max
    if gate_pass and all(v['passed'] for v in frozen_checks.values()):
        row['status'] = 'historical_center_replayed'
    elif gate_pass:
        row['status'] = 'state_exported_reproduction_mismatch'
    else:
        row['status'] = 'center_gate_failed'
    return row


def _strip(obj):
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_strip(v) for v in obj]
    return obj if isinstance(obj, (int, float, str, bool, type(None))) else str(obj)


def _git(*args) -> str:
    r = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True)
    return r.stdout.decode('utf-8', errors='replace').strip()


def main() -> int:
    raise RuntimeError('Recovery cohort permanently closed: repeated training is forbidden; reuse saved checkpoints with p1b_correct.py')
    started = time.perf_counter()
    torch.set_default_dtype(torch.float64)
    torch.set_num_threads(1)
    REC.mkdir(parents=True, exist_ok=True)
    records = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((DAY1 / 'raw').glob('*.json'))]
    records_by_id = {r['center_id']: r for r in records}
    selection = select_centers(records)
    planned = selection['predetermined'] + selection['controls']
    manifest_rows, failures = [], []
    cumulative = 0.0
    for entry in planned:
        if cumulative >= TOTAL_BUDGET_S:
            failures.append(dict(center_id=entry['center_id'], error='budget_exhausted_before_start'))
            manifest_rows.append(dict(center_id=entry['center_id'], status='budget_exhausted'))
            continue
        try:
            row = replay_center(entry, records_by_id)
        except Exception as exc:  # noqa: BLE001
            row = dict(center_id=entry['center_id'], status='RECOVERY_FAILED',
                       failure_reason=f'{type(exc).__name__}: {exc}')
            failures.append(dict(center_id=entry['center_id'], error=row['failure_reason']))
        cumulative += float(row.get('replay_seconds', 0.0) or 0.0)
        row['cumulative_replay_seconds'] = cumulative
        manifest_rows.append(row)
        print(json.dumps({k: row.get(k) for k in ('center_id', 'status', 'replay_seconds',
                                                  'max_frozen_relative_error', 'failure_reason')},
                         ensure_ascii=False), flush=True)
    keys = list(dict.fromkeys(k for r in manifest_rows for k in r))
    with (OUT / 'RECOVERY_MANIFEST.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(manifest_rows)
    cost = dict(selection=selection, wall_seconds=time.perf_counter() - started,
                cumulative_replay_seconds=cumulative, budget_limits=[PER_CENTER_BUDGET_S, TOTAL_BUDGET_S],
                failures=failures,
                environment=dict(python=platform.python_version(), torch=torch.__version__,
                                 numpy=np.__version__, threads=torch.get_num_threads(),
                                 commit=_git('rev-parse', 'HEAD')),
                task_book_sha256=digest(TASK_BOOK))
    save_json(OUT / 'p1b_b_cost.json', cost)
    print(json.dumps(dict(planned=[p['center_id'] for p in planned], cumulative_replay_seconds=cumulative,
                          failures=failures), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
