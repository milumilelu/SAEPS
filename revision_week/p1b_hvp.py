"""P1B-C: verify a REAL autodiff HVP on the recovered historical centers.

The production path builds the HVP from the actual residual/objective and the
replayed state tensors (torch.func forward-over-reverse on the un-anchored
ell = 0.5*sum(rbar^2)); it never loads the archived H matrices or wraps H@v.
Explicit-dense and block-quadratic quantities are verification-side references
only, costed separately. Fixed gamma; H excludes the state anchor; gamma is
added once: F_SO = V^T(HV) + gamma*Z^T Z, D = (HV)_theta - gamma*Z.
Parity target (well-conditioned operator, original task book): 1e-8 normalized.
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
from saeps.config import load_config  # noqa: E402
from saeps.p5_confirmation import _runtime_config  # noqa: E402
from saeps.scalar import make_scalar_points, solve_truth, scalar_residual  # noqa: E402

DAY1 = ROOT / 'revision_week/outputs/day1'
OUT = ROOT / 'revision_week/outputs/day2'
REC = OUT / 'recovery'
RUN_ID, EXPERIMENT_ID = 'day2', 'P1B_C'
TASK_BOOK = Path(r'C:/Users/RZF/Desktop/博士课题资料/SAEPS/任务说明/CODEX_SAEPS_PHASE1B_FOLLOWUP.md')
PARITY_TARGET = 1e-8


def digest(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save_json(p: Path, obj) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    tmp.replace(p)


def rel_norm(diff: float, scale: float, floor: float = 1e-12) -> float:
    return float(diff) / max(float(scale), floor)


def load_center_state(center_id: str) -> dict:
    ckpt = np.load(REC / center_id / 'state_checkpoint.npz')
    prov = json.loads((REC / center_id / 'provenance.json').read_text(encoding='utf-8'))
    return dict(ckpt=ckpt, prov=prov)


def rebuild_residual(benchmark: str, seed: int, runtime: dict, points, truth):
    def residual(theta: torch.Tensor, log_parameter: torch.Tensor) -> torch.Tensor:
        return scalar_residual(theta, log_parameter, benchmark, points, truth, runtime)
    return residual


def main() -> int:
    started = time.perf_counter()
    torch.set_default_dtype(torch.float64)
    torch.set_num_threads(1)
    np.random.seed(0)

    manifest_rows = list(csv.DictReader((OUT / 'RECOVERY_MANIFEST.csv').open(encoding='utf-8')))
    done = [r for r in manifest_rows if r.get('status') == 'historical_center_replayed']
    if not done:
        print(json.dumps(dict(status='NO_RECOVERED_CENTERS', rows=len(manifest_rows))))
        return 1

    parity_rows, cost_rows = [], []
    for entry in done:
        center_id, name = entry['center_id'], entry['center_id'].rsplit('_', 1)[0]
        seed = int(entry['seed'])
        state = load_center_state(center_id)
        ckpt, prov = state['ckpt'], state['prov']
        t_load0 = time.perf_counter()
        runtime, _, truth, points = (None, None, None, None)
        if name == 'burgers':
            v42 = load_config(ROOT / 'configs/v4_2/locked_corrected_confirmation.yaml')
            v36 = load_config(ROOT / v42['source_v3_6_scientific_protocol']['path'])
            scalar = load_config(ROOT / v36['source_files']['scalar_config']['path'])
            runtime = _runtime_config(scalar)
            truth = solve_truth(runtime, 'Burgers')
        else:
            spec = load_config(ROOT / 'configs/v4_4/locked_allen_cahn_confirmation.yaml')
            runtime = load_config(ROOT / spec['protected_sources']['scalar_runtime']['path'])
            runtime['network']['hidden_width'] = 8
            truth = solve_truth(runtime, 'Allen-Cahn')
        points = make_scalar_points(runtime, seed)
        t_load = time.perf_counter() - t_load0
        residual = rebuild_residual('Burgers' if name == 'burgers' else 'Allen-Cahn', seed, runtime, points, truth)

        theta = torch.tensor(ckpt['theta'], dtype=torch.float64)
        log_parameter = torch.tensor(ckpt['log_parameter'], dtype=torch.float64)
        gamma = float(ckpt['gamma'])
        n = theta.numel()
        joint = torch.cat([theta, log_parameter])
        g_np, h_np = None, None
        g_tt, g_tl, g_ll = ckpt['G_tt'], ckpt['G_tl'], ckpt['G_ll']
        h_tt, h_tl, h_ll = ckpt['H_tt_sym'], ckpt['H_tl'], ckpt['H_ll']
        g = np.block([[g_tt, g_tl], [g_tl.T, g_ll]])
        h = np.block([[h_tt, h_tl], [h_tl.T, h_ll]])
        z = np.asarray(ckpt['gn_response_Z'])
        eye_n = np.eye(n)

        # ---------- production HVP from the real residual (no archived H) ----
        def ell(unjoint: torch.Tensor) -> torch.Tensor:
            r = residual(unjoint[:n], unjoint[n:])
            return 0.5 * torch.sum(r.square())

        v_dir = np.vstack((-z, np.ones((1, z.shape[1]))))  # [n+p, p] here p=1
        v_t = torch.tensor(v_dir[:, 0], dtype=torch.float64)

        t0 = time.perf_counter()  # cold start
        _, hv_cold = torch.autograd.functional.hvp(ell, joint, v=v_t)
        t_cold = time.perf_counter() - t0
        hv = hv_cold.detach().cpu().numpy().reshape(-1)

        warm_times, hvp_count, jvp_count = [], 1, 0
        for _ in range(3):
            t1 = time.perf_counter()
            _, hv_w = torch.autograd.functional.hvp(ell, joint, v=v_t)
            warm_times.append(time.perf_counter() - t1)
            assert torch.allclose(hv_w, hv_cold)

        # directional operators via caller-side JVP (core.py convention)
        t2 = time.perf_counter()
        jvp_fn = lambda vec: torch.func.jvp(
            lambda u: residual(u[:n], u[n:]), (joint,), (vec,))[1]
        jv = np.asarray(jvp_fn(v_t).detach()).reshape(-1, 1)
        jvp_count += 1
        q_dir = float(jv.T @ jv + gamma * z.T @ z)
        f_so_dir = float(v_dir.T @ hv.reshape(-1, 1) + gamma * z.T @ z)
        d_prod = hv[:n] - gamma * z[:, 0]
        t_dir = time.perf_counter() - t2

        # ---------- verification references (costed separately) --------------
        t3 = time.perf_counter()
        H_full = torch.func.hessian(ell)(joint)  # explicit dense, verification only
        t_hess = time.perf_counter() - t3
        H_ref = H_full.detach().cpu().numpy()
        hv_explicit = H_ref @ v_dir[:, 0]
        hvp_abs = float(np.max(np.abs(hv - hv_explicit)))
        hvp_scale = float(np.max(np.abs(hv_explicit))) or 1.0
        hvp_rel = hvp_abs / hvp_scale

        # block-quadratic form consistency (day1 convention)
        f_so_quad = float(quadratic_blocks(h_tl, h_ll, h_tt, z, gamma))
        q_quad = float(quadratic_blocks(g_tl, g_ll, g_tt, z, gamma))
        quad_rel = abs(f_so_dir - f_so_quad) / max(abs(f_so_quad), 1e-12)
        q_rel = abs(q_dir - q_quad) / max(abs(q_quad), 1e-12)

        # JVP/VJP adjoint identity with a fixed pseudo-random test vector
        u_test = torch.randn(len(np.asarray(residual(theta, log_parameter))), generator=torch.Generator().manual_seed(7), dtype=torch.float64)

        def r_fn(vec: torch.Tensor) -> torch.Tensor:
            return residual(vec[:n], vec[n:])

        _, jv_test = torch.func.jvp(r_fn, (joint,), (v_t,))
        r0, vjp_back = torch.func.vjp(r_fn, joint)
        jt_u = vjp_back(u_test)[0]
        adjoint_lhs = float(u_test @ jv_test)
        adjoint_rhs = float(jt_u @ v_t)
        adjoint_rel = abs(adjoint_lhs - adjoint_rhs) / max(abs(adjoint_lhs), 1e-12)

        # GN solve residual + gradient identity H_ll - G_ll == grad_lambda ell
        m_np = g[:n, :n] + gamma * eye_n
        rg = g[:n, n:] - m_np @ z
        gn_res = float(np.linalg.norm(rg) / max(np.linalg.norm(g[:n, n:]), 1e-30))
        grad_lam_sum = float(ckpt['gradient_lambda_sum_objective'][0])
        ident_grad = abs(float(h_ll[0, 0]) - float(g_ll[0, 0]) - grad_lam_sum)
        ident_grad_rel = ident_grad / max(abs(grad_lam_sum), 1e-12)

        # archived D consistency: D = H_tl - A z (day1) vs (HV)_theta - gamma z
        d_arch = h_tl - (h_tt + gamma * eye_n) @ z
        d_rel = float(np.max(np.abs(d_prod - d_arch[:, 0]))) / max(float(np.linalg.norm(d_arch)), 1e-30)

        parity_rows.append(dict(
            run_id=RUN_ID, center_id=center_id, pde=name, seed=seed,
            gamma=gamma, n_state=n,
            hvp_vs_explicit_max_abs=hvp_abs, hvp_vs_explicit_relative=hvp_rel,
            parity_target=PARITY_TARGET, parity_pass_well_conditioned=bool(hvp_rel <= PARITY_TARGET),
            f_so_directional=f_so_dir, f_so_block_quadratic=f_so_quad, f_so_quadratic_rel=quad_rel,
            q_g_directional=q_dir, q_g_block_quadratic=q_quad, q_g_quadratic_rel=q_rel,
            jvp_vjp_adjoint_relative=adjoint_rel,
            gn_normal_residual=gn_res,
            hll_minus_gll_vs_grad_lambda_abs=ident_grad,
            hll_minus_gll_vs_grad_lambda_relative=ident_grad_rel,
            d_prod_vs_archived_relative=d_rel,
            cond_H_joint=float(np.linalg.cond(h)),
            jvp_count=2, hvp_count=hvp_count + 3, vjp_count=1,
        ))
        cost_rows.append(dict(
            run_id=RUN_ID, center_id=center_id,
            checkpoint_restore_seconds=t_load,
            hvp_cold_start_seconds=t_cold,
            hvp_warm_seconds_1=warm_times[0], hvp_warm_seconds_2=warm_times[1], hvp_warm_seconds_3=warm_times[2],
            hvp_warm_median_seconds=float(np.median(warm_times)),
            directional_jvp_plus_hvp_seconds=t_dir,
            explicit_dense_hessian_seconds=t_hess,
            note=('explicit dense Hessian and block quadratics are verification-side only; '
                  'GN solve residual here is computed from archived blocks (dense, verification); '
                  'production HVP used only JVP+HVP on the real residual.'),
            torch_threads=torch.get_num_threads(), device='cpu',
            timing_sync='time.perf_counter (wall); CPU-bound single-thread float64',
        ))
        print(json.dumps(dict(center_id=center_id, hvp_rel=hvp_rel, quad_rel=quad_rel,
                              adjoint_rel=adjoint_rel, gn_res=gn_res, ident_grad_rel=ident_grad_rel)), flush=True)

    keys = list(dict.fromkeys(k for r in parity_rows for k in r))
    with (OUT / 'HVP_PARITY.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(parity_rows)
    keys = list(dict.fromkeys(k for r in cost_rows for k in r))
    with (OUT / 'HVP_COST.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(cost_rows)
    save_json(OUT / 'p1b_c_summary.json', dict(
        run_id=RUN_ID, experiment_id=EXPERIMENT_ID,
        parent_commit=_git('rev-parse', 'HEAD'),
        task_book_sha256=digest(TASK_BOOK),
        n_centers=len(parity_rows),
        all_parity_pass=all(r['parity_pass_well_conditioned'] for r in parity_rows),
        max_hvp_relative=max(r['hvp_vs_explicit_relative'] for r in parity_rows),
        wall_seconds=time.perf_counter() - started,
        environment=dict(python=platform.python_version(), torch=torch.__version__,
                         numpy=np.__version__, threads=1, device='cpu'),
    ))
    return 0


def quadratic_blocks(tl, ll, tt, z, gamma):
    """C - B^T Z - Z^T B + Z^T (T + gamma I) Z for scalar p=1 blocks."""
    n = tt.shape[0]
    c = float(ll[0, 0])
    b = tl  # (n,1)
    t = tt + gamma * np.eye(n)
    zz = z
    return c - float(b.T @ zz) - float(zz.T @ b) + float(zz.T @ t @ zz)


def _git(*args) -> str:
    r = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True)
    return r.stdout.decode('utf-8', errors='replace').strip()


if __name__ == '__main__':
    sys.exit(main())
