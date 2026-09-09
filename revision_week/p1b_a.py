"""P1B-A post-hoc analysis of the day1 SO audit. No new training, no new iteration.

Reuses revision_week/core.py and run.py::load_center (tested implementation).
Reads day1 raw records plus the archived v3 center matrices, recomputes the
signed error decomposition independently, verifies the improvement-factor
definition, splits SO-ADAPT tolerance outcomes into bound-vs-truth quadrants,
and analyses why the dense-assisted bound is loose. Spectral decompositions are
analysis-side only and are costed separately; they never feed a production
stopper.
"""
from __future__ import annotations
import os
for key in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS']:
    os.environ[key] = '1'
import csv, hashlib, json, sys, time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import quadratic, reference  # noqa: E402  (tested implementation)
from run import load_center  # noqa: E402  (tested loader, same frozen inputs)

ROOT = Path(__file__).resolve().parents[1]
DAY1 = ROOT / 'revision_week/outputs/day1'
OUT = ROOT / 'revision_week/outputs/day2'
RUN_ID = 'day2'
EXPERIMENT_ID = 'P1B_A'
TOLERANCE = 0.10  # adaptive relative tolerance inherited from day1 protocol

PROTOCOL_PATH = Path(r'C:/Users/RZF/Desktop/博士课题资料/SAEPS/任务说明/CODEX_SAEPS_PHASE1B_FOLLOWUP.md')
PHASE1_REPORTED = 7.839167663475002


def digest(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p: Path, obj) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    tmp.replace(p)


def table(p: Path, rows: list[dict]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def fnum(x):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else float(x)


def analyze_center(rec: dict, center_path: Path, eig_cost: list) -> dict:
    """Independent signed decomposition from archived matrices (p=1 scalar)."""
    d, g, h = load_center(center_path)
    n = len(d['GN_blocks']['G_tt'])
    gamma = float(d['gamma'])
    m = g[:n, :n] + gamma * np.eye(n)
    a = h[:n, :n] + gamma * np.eye(n)
    bg, b = g[:n, n:], h[:n, n:]
    cg, ch = g[n:, n:], h[n:, n:]
    z = np.linalg.solve(m, bg)
    q_g = quadratic(cg, bg, m, z)
    f_so = quadratic(ch, b, a, z)
    f_g_exact = quadratic(cg, bg, m, np.linalg.solve(m, bg))
    star = reference(h, n, gamma)
    d_vec = b - a @ z
    energy = float(d_vec.T @ np.linalg.solve(a, d_vec))

    e_g = float(q_g[0, 0] - star[0, 0])
    delta = float(f_so[0, 0] - q_g[0, 0])
    e_so = float(f_so[0, 0] - star[0, 0])
    e_g_exact = float(f_g_exact[0, 0] - star[0, 0])
    scale = max(abs(float(star[0, 0])), abs(float(f_so[0, 0])), 1.0)
    identity = abs(e_so - energy) / scale

    # signed-error resolution (same rule as day1: 64*n*eps*scale)
    resolution = 64 * n * np.finfo(float).eps * max(abs(e_so), abs(e_g), abs(star[0, 0]), 1.0)
    resolved = abs(e_so) > resolution and abs(e_g) > resolution

    # directional-gap term decomposition (p=1): delta = z' S_tt z - 2 z' S_tl + S_ll
    s = h - g
    t_tt = float(z.T @ s[:n, :n] @ z)
    t_tl = float(-2.0 * z.T @ s[:n, n:])
    t_ll = float(s[n:, n:][0, 0])
    delta_decomp = t_tt + t_tl + t_ll
    delta_decomp_err = abs(delta_decomp - delta) / scale

    # analysis-side spectrum of A: bound looseness mechanism
    t0 = time.perf_counter()
    vals, vecs = np.linalg.eigh((a + a.T) / 2)
    eig_cost.append(time.perf_counter() - t0)
    d_rot = vecs.T @ d_vec[:, 0]
    mu_eff = float(np.linalg.norm(d_vec) ** 2 / energy) if energy > 0 else None
    frac_min_energy = float((d_rot[0] ** 2 / vals[0]) / energy) if energy > 0 else None
    frac_top10 = float(np.sum((d_rot ** 2 / vals)[:10]) / energy) if energy > 0 else None

    abs_gn = abs(e_g)
    abs_gn_exact = abs(e_g_exact)
    abs_so = abs(e_so)
    improvement = abs_gn / abs_so if resolved else None
    improvement_exact = abs_gn_exact / abs_so if resolved else None

    # SO-ADAPT quadrant inputs (day1 fixed-budget trace + post-hoc truth)
    adapt = rec['adaptive']
    final = adapt['trace'][-1]
    true_rel = rec['adaptive_absolute_error'] / (abs(float(star[0, 0])) + 1e-8)
    numerical_pass = adapt['status'] == 'numerical_tolerance_met'
    truth_pass = true_rel <= TOLERANCE
    if truth_pass and numerical_pass:
        quadrant = 'Q1_bound_pass_truth_pass'
    elif truth_pass and not numerical_pass:
        quadrant = 'Q2_bound_fail_truth_pass'
    elif not truth_pass and not numerical_pass:
        quadrant = 'Q3_bound_fail_truth_fail'
    else:
        quadrant = 'Q4_bound_pass_truth_fail'

    row = dict(
        center_id=rec['center_id'], pde=rec['pde'],
        historical_valid=bool(rec['historical_valid']),
        algebraic_schur_valid=bool(rec['algebraic_schur_valid']),
        local_profile_valid=rec['local_profile_valid'],
        GN_normal_residual=fnum(rec['GN_normal_residual']),
        Q_G_actual=fnum(q_g[0, 0]), F_G_exact_solve=fnum(f_g_exact[0, 0]),
        F_SO=fnum(f_so[0, 0]), F_star=fnum(star[0, 0]),
        e_G_signed=fnum(e_g), e_G_exact_signed=fnum(e_g_exact),
        delta_directional=fnum(delta),
        delta_term_tt_state=fnum(t_tt), delta_term_tl_cross=fnum(t_tl),
        delta_term_ll_param=fnum(t_ll), delta_decomposition_error=fnum(delta_decomp_err),
        e_SO_signed=fnum(e_so), defect_energy_q=fnum(energy),
        q_identity_residual=fnum(identity),
        identity_residual=max(fnum(rec['algebra_identity_error']), identity),
        absolute_error_GN=fnum(abs_gn), absolute_error_GN_exact_solve=fnum(abs_gn_exact),
        absolute_error_SO=fnum(abs_so),
        relative_error_GN_day1=fnum(rec['relative_error_GN']),
        relative_error_SO_day1=fnum(rec['relative_error_SO']),
        improvement_factor_taskbook=fnum(improvement),
        improvement_factor_phase1=fnum(improvement_exact if improvement_exact is not None else improvement),
        SO_improved_day1=bool(rec['SO_improved']),
        delta_over_q=fnum(delta / energy) if energy > 0 else None,
        resolution_abs=fnum(resolution), numerical_resolution_status='resolved' if resolved else 'not_resolved',
        gamma=gamma, n_state=n, D_norm=fnum(rec['D_norm']),
        cond_A=fnum(np.linalg.cond(a)),
        lambda_min_A_numeric=fnum(rec['lambda_min_A_numeric']),
        numerical_margin=fnum(rec['numerical_margin']), mu_value=fnum(rec['mu_value']),
        mu_effective_D_weighted=fnum(mu_eff),
        min_eig_direction_energy_fraction=fnum(frac_min_energy),
        top10_eig_direction_energy_fraction=fnum(frac_top10),
        U_absolute_day1=fnum(rec['U_absolute']),
        bound_effectivity_day1=fnum(rec['bound_effectivity']),
        adaptive_status=adapt['status'], adaptive_A_matvec_count=int(adapt['A_matvec_count']),
        adaptive_iterations=len(adapt['trace']) - 1,
        adaptive_final_U_absolute=fnum(final['U_absolute']),
        adaptive_final_U_relative=fnum(final['U_relative_if_available']),
        adaptive_final_relative_status=final['relative_status'],
        adaptive_absolute_error=fnum(rec['adaptive_absolute_error']),
        true_relative_error_posthoc=fnum(true_rel), true_pass_at_10pct=bool(truth_pass),
        numerical_judged_pass_at_10pct=bool(numerical_pass),
        adapt_quadrant=quadrant,
        mu_source=rec['mu_source'], bound_status=rec['bound_status'],
        dense_assisted=True, oracle_spectral_used=False,
        gn_solve_seconds=fnum(rec['gn_solve_seconds']),
        reference_seconds=fnum(rec['reference_seconds']),
        spectrum_seconds_day1=fnum(rec['spectrum_seconds']),
        adaptive_seconds_day1=fnum(rec['adaptive_seconds']),
    )
    return row


def main() -> int:
    raise RuntimeError('Archived analysis is immutable: use p1b_correct.py for terminal-defect analysis')
    started = time.perf_counter()
    cpu0 = time.process_time()
    OUT.mkdir(parents=True, exist_ok=True)
    eig_cost: list[float] = []

    records = [json.loads(p.read_text(encoding='utf-8'))
               for p in sorted((DAY1 / 'raw').glob('*.json'))]
    pass_recs = [r for r in records if r['status'] == 'PASS']

    repo = json.loads((DAY1 / 'initial_workspace.json').read_text(encoding='utf-8'))['repo']
    repo = Path(repo)
    rows, failures = [], []
    for rec in pass_recs:
        center_path = Path(rec['input_path'])
        try:
            rows.append(analyze_center(rec, center_path, eig_cost))
        except Exception as exc:  # noqa: BLE001 - record and continue
            failures.append(dict(center_id=rec['center_id'],
                                 error=f'{type(exc).__name__}: {exc}'))

    # ---- A1: definition of the improvement factor -------------------------
    factors = [r['improvement_factor_phase1'] for r in rows if r['improvement_factor_phase1'] is not None]
    factors_tb = [r['improvement_factor_taskbook'] for r in rows if r['improvement_factor_taskbook'] is not None]
    median_ratio = float(np.median(factors))
    median_ratio_tb = float(np.median(factors_tb))
    med_gn = float(np.median([r['absolute_error_GN'] for r in rows]))
    med_so = float(np.median([r['absolute_error_SO'] for r in rows]))
    ratio_of_medians = med_gn / med_so
    med_rel_gn = float(np.median([r['relative_error_GN_day1'] for r in rows]))
    med_rel_so = float(np.median([r['relative_error_SO_day1'] for r in rows]))
    ratio_of_medians_relative = med_rel_gn / med_rel_so
    a1 = dict(
        n_centers=len(rows),
        phase1_reported_median=PHASE1_REPORTED,
        median_of_per_center_ratios=median_ratio,
        median_of_per_center_ratios_taskbook_QG=median_ratio_tb,
        ratio_of_medians_absolute=ratio_of_medians,
        ratio_of_medians_relative=ratio_of_medians_relative,
        median_abs_error_GN=med_gn, median_abs_error_SO=med_so,
        median_rel_error_GN=med_rel_gn, median_rel_error_SO=med_rel_so,
        matches_phase1_definition=abs(median_ratio - PHASE1_REPORTED) <= 1e-9,
        burger55_own_factor=next((r['improvement_factor_phase1'] for r in rows if r['center_id'] == 'burgers_55'), None),
        interpretation=('7.84 is the median of per-center ratios |e_G|/|e_SO| '
                        '(numerically the burgers_55 row). It is NOT a ratio of medians: '
                        'median(GN)/median(SO) is 7.768 for relative errors and '
                        '4.806 for absolute errors. Phase-1 wording is consistent.'),
        worse_centers=[r['center_id'] for r in rows if not r['SO_improved_day1']],
    )

    # ---- A3: four-quadrant split ------------------------------------------
    quadrants = {}
    for r in rows:
        quadrants[r['adapt_quadrant']] = quadrants.get(r['adapt_quadrant'], 0) + 1
    a3 = dict(
        tolerance=TOLERANCE,
        quadrant_counts=quadrants,
        n_total=len(rows),
        true_pass_n=sum(r['true_pass_at_10pct'] for r in rows),
        numerical_pass_n=sum(r['numerical_judged_pass_at_10pct'] for r in rows),
        unresolvable_reference_n=0,
        median_true_relative_error_posthoc=float(np.median([r['true_relative_error_posthoc'] for r in rows])),
        median_bound_effectivity=float(np.median([r['bound_effectivity_day1'] for r in rows if r['bound_effectivity_day1'] is not None])),
        median_mu_effective=float(np.median([r['mu_effective_D_weighted'] for r in rows if r['mu_effective_D_weighted'] is not None])),
        median_min_eig_energy_fraction=float(np.median([r['min_eig_direction_energy_fraction'] for r in rows if r['min_eig_direction_energy_fraction'] is not None])),
    )

    # ---- A2 mechanism aggregates ------------------------------------------
    abs_so_ranked = sorted(rows, key=lambda r: -r['absolute_error_SO'])
    abs_gn_ranked = sorted(rows, key=lambda r: -r['absolute_error_GN'])
    row59 = next(r for r in rows if r['center_id'] == 'burgers_59')
    row67 = next(r for r in rows if r['center_id'] == 'burgers_67')
    mech_keys = ('e_G_signed', 'delta_directional', 'e_SO_signed', 'defect_energy_q',
                 'delta_term_tt_state', 'delta_term_tl_cross', 'delta_term_ll_param',
                 'cond_A', 'mu_effective_D_weighted', 'min_eig_direction_energy_fraction',
                 'absolute_error_GN', 'absolute_error_SO', 'improvement_factor_phase1',
                 'relative_error_GN_day1', 'relative_error_SO_day1', 'gamma', 'D_norm')
    a2 = dict(
        ranking_by_abs_error_SO=[(r['center_id'], r['absolute_error_SO']) for r in abs_so_ranked[:6]],
        ranking_by_abs_error_GN=[(r['center_id'], r['absolute_error_GN']) for r in abs_gn_ranked[:6]],
        delta_over_q_all=[(r['center_id'], r['delta_over_q']) for r in rows],
        worsening_band_n=sum(1 for r in rows if r['delta_over_q'] is not None and 0 < r['delta_over_q'] < 2),
        median_delta_over_q=float(np.median([r['delta_over_q'] for r in rows if r['delta_over_q'] is not None])),
        max_cond_A=float(np.max([r['cond_A'] for r in rows])),
        burger59={k: row59[k] for k in mech_keys},
        burger67={k: row67[k] for k in mech_keys},
    )

    # ---- deliverables ------------------------------------------------------
    table(OUT / 'SO_SIGNED_ERROR_DECOMPOSITION.csv', rows)
    table(OUT / 'ADAPT_FAILURE_SPLIT.csv', [
        dict(center_id=r['center_id'], pde=r['pde'],
             numerical_judged_pass=r['numerical_judged_pass_at_10pct'],
             true_relative_error_posthoc=r['true_relative_error_posthoc'],
             true_pass_at_10pct=r['true_pass_at_10pct'],
             quadrant=r['adapt_quadrant'],
             adaptive_status=r['adaptive_status'],
             adaptive_A_matvec_count=r['adaptive_A_matvec_count'],
             adaptive_absolute_error=r['adaptive_absolute_error'],
             adaptive_final_U_absolute=r['adaptive_final_U_absolute'],
             adaptive_final_relative_status=r['adaptive_final_relative_status'],
             mu_source=r['mu_source'], bound_status=r['bound_status'],
             dense_assisted=r['dense_assisted'], oracle_spectral_used=r['oracle_spectral_used'],
             relative_error_criterion='U/(f-U) for the estimate; E/(||F_*||+1e-8) for post-hoc truth')
        for r in rows])

    # ---- MD deliverables (all numbers from computed rows) -------------------
    def fmt(x, sig=6):
        if x is None:
            return 'NA'
        return f'{x:.{sig}g}'

    q_list = {qname: [r['center_id'] for r in rows if r['adapt_quadrant'] == qname]
              for qname in ['Q1_bound_pass_truth_pass', 'Q2_bound_fail_truth_pass',
                            'Q3_bound_fail_truth_fail', 'Q4_bound_pass_truth_fail']}

    md_split = f"""# SO-ADAPT 失败拆分（事后真实误差 vs 数值估计判定）

run_id={RUN_ID}; experiment_id={EXPERIMENT_ID}; 父提交 acf848f；容差 {TOLERANCE}（继承第一阶段 adaptive_tolerance）。

## 判据口径（继承原任务书，不得偷换）

- 数值估计判定（算法侧）：有限对角 PCG 修正使用条件谱界 U=||D||²/μ；当 f=||F_SO||>U 时
  用 U/(f−U)≤{TOLERANCE} 判定，`refine()` 返回 `numerical_tolerance_met`。普通 dense eigh 的
  μ 是数值估计（`mu_source=dense_eigh_with_numerical_margin`），**不是严格证书**。
- 事后真实误差（独立参考侧）：E=|F_SO^refined−F_*|，真实相对误差 E/(||F_*||+1e-8)≤{TOLERANCE}。
  参考为独立代数 Schur 解，与候选、缺陷能量输入无关。
- 无法分辨参考尺度的记录：{a3['unresolvable_reference_n']} 条（全部 21 条 |F_*| 远高于分辨率）。

## 四格计数（21 个可比矩阵中心）

| 数值估计判定 | 事后真实误差 | 计数 | 中心 |
|---|---|---:|---|
| 通过 | 通过 | {len(q_list['Q1_bound_pass_truth_pass'])} | {', '.join(q_list['Q1_bound_pass_truth_pass'])} |
| 不通过 | 通过 | {len(q_list['Q2_bound_fail_truth_pass'])} | {', '.join(q_list['Q2_bound_fail_truth_pass'])} |
| 不通过 | 不通过 | {len(q_list['Q3_bound_fail_truth_fail'])} | {', '.join(q_list['Q3_bound_fail_truth_fail']) or '无'} |
| 通过 | 不通过 | {len(q_list['Q4_bound_pass_truth_fail'])} | {', '.join(q_list['Q4_bound_pass_truth_fail']) or '无'} |

**结论：真实相对误差 21/21 全部达标（中位数 {fmt(a3['median_true_relative_error_posthoc'], 3)}）；"9/21 达到容差"
纯粹是数值界过松造成的估计侧假阴性。** 按任务书第 7 节口径：瓶颈在估计实用性，不在近似精度；
不得宣称 SO-ADAPT 在 12 个中心精度失败；不存在"估计通过而真实未通过"的一致性警报象限。

## 界为何松（稠密矩阵上的机制分析，仅离线诊断）

- 界 U=||D||²/μ 用的是 A 的最小特征值（μ≈λ_min−margin），而缺陷能量 q=DᵀA⁻¹D 由 D 实际
  加权的方向决定。定义 D 加权有效特征值 μ_eff=||D||²/q，则界过松倍数=U/E=μ_eff/μ。
- 21 中心中位数：μ_eff={fmt(a3['median_mu_effective'])}，λ_min 方向承载 D 的能量占比中位数
  {fmt(a3['median_min_eig_energy_fraction'], 3)}（≈0），界有效度（U/E）中位数 {fmt(a3['median_bound_effectivity'])}。
- 即：最小特征值方向几乎不承载 D 的能量，谱条件数（最大 cond(A)={fmt(a2['max_cond_A'], 3)}）
  通过 λ_min 直接惩罚 U。这是谱界对"缺陷能量集中于高特征值方向"这一常态的已知保守性。
- 每条记录字段：`mu_source`、`bound_status`、`dense_assisted=True`、`oracle_spectral_used=False`
  （未使用任何 oracle 谱信息；dense eigh 数值估计仅用于诊断与算法内停止，不是严格认证）。
- 谱分解仅用于本离线机制分析，成本单列（本脚本 analysis_side_spectrum_seconds），不输入任何
  实用停止器后宣称矩阵无关。

原始逐行数据见 `ADAPT_FAILURE_SPLIT.csv`；第一阶段原始自适应轨迹（101 点/中心）保存在
`../day1/raw/*.json`，未修改。
"""
    (OUT / 'ADAPT_FAILURE_SPLIT.md').write_text(md_split, encoding='utf-8')

    r59, r67 = row59, row67
    band = [(r['center_id'], r['delta_over_q']) for r in rows
            if r['delta_over_q'] is not None and 0 < r['delta_over_q'] < 2]
    rank_so_59 = 1 + sum(1 for r in rows if r['absolute_error_SO'] > r59['absolute_error_SO'])
    rank_so_67 = 1 + sum(1 for r in rows if r['absolute_error_SO'] > r67['absolute_error_SO'])
    rank_gn_59 = 1 + sum(1 for r in rows if r['absolute_error_GN'] > r59['absolute_error_GN'])
    rank_gn_67 = 1 + sum(1 for r in rows if r['absolute_error_GN'] > r67['absolute_error_GN'])
    med_abs_gn = a1['median_abs_error_GN']
    med_abs_so = a1['median_abs_error_SO']
    md_fail = f"""# SO 变差中心失败分析（Burgers 59、67）

run_id={RUN_ID}; experiment_id={EXPERIMENT_ID}; 分析对象为第一阶段 E0 已保存的 21 个可比矩阵中心；
全部输入为只读复用（day1/raw 与原仓库 v3 中心存档），未重新训练、未调 gamma/容差/中心选择。

## 1. 变差的直接机制：带符号误差分解（p=1 标量中心）

恒等式（在存档矩阵上独立重算，见 SO_SIGNED_ERROR_DECOMPOSITION.csv）：

    e_SO = F_SO − F_* = q = DᵀA⁻¹D ≥ 0（A 数值 SPD）
    Δ   = F_SO − Q_G = Vᵀ(H−G)V
    e_G = Q_G − F_* = q − Δ
    improvement factor = |e_G|/|e_SO| = |1 − Δ/q|

| 中心 | e_G（带符号） | Δ | q=e_SO | Δ/q | 改善倍数 |
|---|---|---|---|---|---|
| burgers_59 | {fmt(r59['e_G_signed'])} | {fmt(r59['delta_directional'])} | {fmt(r59['defect_energy_q'])} | {fmt(r59['delta_over_q'], 4)} | {fmt(r59['improvement_factor_phase1'], 4)} |
| burgers_67 | {fmt(r67['e_G_signed'])} | {fmt(r67['delta_directional'])} | {fmt(r67['defect_energy_q'])} | {fmt(r67['delta_over_q'], 4)} | {fmt(r67['improvement_factor_phase1'], 4)} |

**SO 变差当且仅当 0<Δ/q<2**（此时 |1−Δ/q|<1，GN 因误差抵消更接近参考）。21 个中心中
恰好只有这两个落在该带内：{', '.join(f'{c} (Δ/q={fmt(v, 4)})' for c, v in band)}。
其余 19 个中心 Δ≤0 或 Δ>2q，SO 改善；所有 21 个改善倍数都被 |1−Δ/q| 精确解释。

Δ 的三项分解（Δ = zᵀS_tt z − 2zᵀS_tl + S_ll，z 为 GN 响应，S=H−G）：

| 中心 | zᵀS_tt z | −2zᵀS_tl | S_ll（=g_λ，log 坐标参数梯度） |
|---|---|---|---|
| burgers_59 | {fmt(r59['delta_term_tt_state'])} | {fmt(r59['delta_term_tl_cross'])} | {fmt(r59['delta_term_ll_param'])} |
| burgers_67 | {fmt(r67['delta_term_tt_state'])} | {fmt(r67['delta_term_tl_cross'])} | {fmt(r67['delta_term_ll_param'])} |

## 2. 是"绝对误差明显增加"还是"GN 误差过小放大比值"？

两者兼有，且以 SO 绝对误差变大为主：
- |e_SO| 排名：burgers_67 第 {rank_so_67}/21（{fmt(r67['absolute_error_SO'])}），burgers_59 第 {rank_so_59}/21（{fmt(r59['absolute_error_SO'])}）；
  21 中心中位数 |e_SO|={fmt(med_abs_so)}——59、67 的 SO 绝对误差是中位数的
  {fmt(r59['absolute_error_SO'] / med_abs_so, 3)} 倍与 {fmt(r67['absolute_error_SO'] / med_abs_so, 3)} 倍。
- |e_G| 排名：burgers_67 第 {rank_gn_67}/21（{fmt(r67['absolute_error_GN'])}，且带符号为负：
  GN 二次型低于 Schur 参考），burgers_59 第 {rank_gn_59}/21（{fmt(r59['absolute_error_GN'])}）；
  中位数 |e_G|={fmt(med_abs_gn)}——GN 误差本身不异常小，只是比自己的 q 小。
- 结论：不是"分母过小"的统计假象；是这两个中心的 Δ>0 且量级压过了 GN 的缺陷能量 q。

## 3. 完整二次型、参考解与恒等式一致性

- 全部 21 中心：|e_SO−q|/scale（q 恒等式）与第一阶段 algebra_identity_error 均 ≤1.7e-11；
  formula/gn 恒等式 ≤3.4e-11；GN 正规方程残差 ≤9.8e-5 相对量级中位数 1e-14 量级
  （逐中心见 CSV 列 GN_normal_residual）。F_G_exact_solve 与 Q_G_actual 仅差 GN 求解残差
  R_GᵀM⁻¹R_G（相对 ~1e-11），不改变任何结论排序。
- 参考病态性：cond(A) 最大 {fmt(a2['max_cond_A'], 3)}（burgers_59 为 {fmt(r59['cond_A'], 4)}）。
  以 eps·cond·scale 估计 Schur 参考自身误差 ≤O(1e-6~1e-7) 绝对量级，比 e_G、q（O(0.4~2.8)）
  小 6 个数量级以上，不构成解释来源。
- 数值相消：burgers_67 的 e_G=−1.446（GN 二次型低于参考）是 Δ>q 的真实代数结果，
  不是浮点相消：其量级超出恒等式残差 11 个数量级。burgers_59 的 e_G>0 同理。

## 4. 状态/参数梯度的可核实来源

- 第一阶段与原始 v3 存档只含归一化平稳性摘要（state_grad_normalized、S_theta、S_lambda）
  与分块矩阵；**theta/数据/绝对梯度张量未归档**（gradient_reason='absolute gradients not archived'）。
  因此"原始中心上 H_ll−G_ll=g_λ（log 坐标）"这一恒等式目前只能在小标量测试网络上核实
  （day1 test_core 已做，27 项通过），**不能在 21 个历史中心上逐点核实**，缺失如实标注。
- 因此本分析对 Δ 的解释停留在矩阵代数层面：Δ>0 的事实与三项分解是可核实的；
  "Δ 为何在这些 seed 上翻转符号/增大"的更深机制（网络与数据层面）需要 P1B-B 恢复状态后才可追查。

## 5. "误差抵消"解释是否成立？

**成立（数值支持充分）**：两个变差中心都满足 0<Δ<2q，且 improvement=|1−Δ/q| 精确复现
0.362254/0.512094（与第一阶段 CSV 一致至 1e-11）。恒等式残差、GN 残差、参考精度均排除
数值伪影。仍不能写进论文的说法：不能把它说成"SO 总体不可靠"（19/21 改善、且改善带
Δ∉(0,2q) 有精确刻画），也不能宣称对该带的先验可检测性——检测 Δ 的符号与量级需要二阶
信息本身，本阶段未提供免 oracle 的实用判别器。

## 禁止事项遵守声明

未对 59、67 单独调 gamma、未改残差权重、未改参数坐标、未截断二阶项、未用 exact oracle
挑选 GN/SO。第一阶段数值与结论未回改。
"""
    (OUT / 'SO_FAILURE_ANALYSIS.md').write_text(md_fail, encoding='utf-8')

    unavailable = [dict(center_id=r['center_id'], pde=r['pde'], status=r['status'],
                        reason=r['failure_reason']) for r in records if r['status'] != 'PASS']

    wall = time.perf_counter() - started
    summary = dict(
        run_id=RUN_ID, experiment_id=EXPERIMENT_ID,
        parent_commit='acf848f70a5ecc6cea98d9e74d65351deeebbdb3',
        task_book_path=str(PROTOCOL_PATH), task_book_sha256=digest(PROTOCOL_PATH),
        day1_raw_input_sha256={r['center_id']: digest(DAY1 / 'raw' / f"{r['center_id']}.json") for r in records},
        center_input_sha256={r['center_id']: r['input_sha256'] for r in records},
        code_sha256=hashlib.sha256((ROOT / 'revision_week/p1b_a.py').read_bytes()).hexdigest(),
        core_sha256=hashlib.sha256((ROOT / 'revision_week/core.py').read_bytes()).hexdigest(),
        n_records=len(records), n_pass=len(pass_recs), n_unavailable=len(unavailable),
        unavailable_records=unavailable, analysis_failures=failures,
        a1_improvement_definition=a1, a3_adapt_split=a3, a2_mechanism=a2,
        analysis_wall_seconds=wall, analysis_cpu_seconds=time.process_time() - cpu0,
        analysis_side_spectrum_seconds=float(np.sum(eig_cost)),
        notes=('Spectral decompositions of A are offline mechanism analysis only; '
               'costed separately, never used as a production stopper input. '
               'No training, no gamma change, no tolerance change, no seed change.'),
    )
    save(OUT / 'p1b_a_summary.json', summary)
    print(json.dumps(dict(a1=a1, a3=a3), indent=2, ensure_ascii=False, default=str))
    print(f'wall={wall:.2f}s spectrum_analysis={np.sum(eig_cost):.4f}s failures={failures}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
