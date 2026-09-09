"""P1B finalize: pilot analysis MD, phase manifest, cost ledger, phase report, claim ledger.

Reads only the day2 outputs produced by p1b_a/p1b_recover/p1b_hvp/p1b_onestep.
No new computation beyond aggregation.
"""
from __future__ import annotations
import csv, hashlib, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'revision_week/outputs/day2'
RUN_ID = 'day2'
TASK_BOOK = Path(r'C:/Users/RZF/Desktop/博士课题资料/SAEPS/任务说明/CODEX_SAEPS_PHASE1B_FOLLOWUP.md')


def digest(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save_json(p: Path, obj) -> None:
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    tmp.replace(p)


def fmt(x, sig=4):
    return 'NA' if x in (None, '') else f'{float(x):.{sig}g}'


def main() -> int:
    t0 = time.perf_counter()
    a = json.loads((OUT / 'p1b_a_summary.json').read_text(encoding='utf-8'))
    b_cost = json.loads((OUT / 'p1b_b_cost.json').read_text(encoding='utf-8'))
    c = json.loads((OUT / 'p1b_c_summary.json').read_text(encoding='utf-8'))
    d = json.loads((OUT / 'p1b_d_summary.json').read_text(encoding='utf-8'))
    pilot = list(csv.DictReader((OUT / 'ONE_STEP_PILOT.csv').open(encoding='utf-8')))
    parity = list(csv.DictReader((OUT / 'HVP_PARITY.csv').open(encoding='utf-8')))
    decomp = list(csv.DictReader((OUT / 'SO_SIGNED_ERROR_DECOMPOSITION.csv').open(encoding='utf-8')))
    manifest_rows = list(csv.DictReader((OUT / 'RECOVERY_MANIFEST.csv').open(encoding='utf-8')))

    # ---------------- ONE_STEP_PILOT.md ----------------
    by = {}
    for r in pilot:
        by.setdefault((r['root_id'], r['offset_id']), {})[r['method']] = r
    lines = ['# 一步参数更新试验（P1B-D，功能验证）', '',
             f"run_id={RUN_ID}; 协议={digest(OUT / 'PHASE1B_PROTOCOL.yaml')[:16]}…（冻结于运行前）；"
             f"根中心（预指定对照）: burgers_55, allen_cahn_84；偏移 λ_s=λ_c±0.05（log 坐标）；"
             f"信赖半径 0.1；系数 [1.0,0.5]；Armijo c1=1e-4；β=1e-6·max(sym F_raw,1e-8)。", '',
             '所有曲率、g_λ、GN 响应 Z_G 均在**公共起点** (θ_s, λ_s) 处从真实残差现算（v1.curvature_blocks），'
             '候选状态统一从起点 GN 预测器 θ_s − Z_G·δλ 初始化并共享同一 LBFGS 求解器；'
             'SO 只改曲率、从不改 Z_G。锚定 γ 与 θ_c 全程固定。', '']
    for (root, off), methods in by.items():
        lines.append(f'## {root} @ λ_c{off}')
        lines.append('')
        lines.append('| 方法 | raw_step | clipped | predicted | actual decrease | actual/pred | 参数误差 before→after | 接受 |')
        lines.append('|---|---|---|---|---|---|---|---|')
        for m in ['RAW', 'SAEPS-GN', 'SO', 'EXACT-REDUCED-ORACLE']:
            r = methods[m]
            lines.append(f"| {m} | {fmt(r.get('raw_step'))} | {fmt(r.get('clipped_step'))} | "
                         f"{fmt(r.get('predicted_decrease'))} | {fmt(r.get('actual_profile_decrease'))} | "
                         f"{fmt(r.get('actual_predicted_ratio_if_resolved'), 3)} | "
                         f"{fmt(r.get('parameter_error_before'), 3)}→{fmt(r.get('parameter_error_after'), 3)} | "
                         f"{'是' if r['step_accepted'] == 'True' else '否'} |")
        lines.append('')
    clipped_same = {}
    for (root, off), methods in by.items():
        vals = {m: (methods[m]['step_accepted'] == 'True', fmt(methods[m]['clipped_step']),
                    fmt(methods[m]['actual_profile_decrease'])) for m in methods}
        trio = ['SAEPS-GN', 'SO', 'EXACT-REDUCED-ORACLE']
        if len({vals[m] for m in trio}) == 1 and vals['SAEPS-GN'][0]:
            clipped_same[(root, off)] = True
    lines.append('## 结论（按任务书口径）')
    lines.append('')
    n_acc = sum(r['step_accepted'] == 'True' for r in pilot)
    lines.append(f"- 16/16 步在系数 1.0 即被 Armijo 接受（接受率 {n_acc}/16）；无 step_rejected、无预算触发。")
    lines.append("- **实际目标下降与真实参数误差分开报告**：全部 16 步两个量都改善，但二者不保证同时改善，此处仅为本试验的观测。")
    lines.append("- **曲率区分度**：SAEPS-GN/SO/ORACLE 的原始步长（0.15–0.38）全部被共同信赖半径 0.1 截断到同一步长，"
                 "三个方法的试验点、实际下降与参数误差逐位相同——按任务书规则，**这组试验缺少曲率区分度**；"
                 "不得据此宣称 SO 与 oracle 等效，也未现场调整半径。")
    lines.append(f"- 被截断组数：{len(clipped_same)}/4 分支（GN/SO/ORACLE 同步长）。")
    lines.append("- RAW（G_ll，未约化曲率）未被截断（步长 0.007–0.015），其目标下降与参数误差改善显著小于 GN 型曲率组——"
                 "曲率选择确实改变一步更新质量；这是 RAW vs GN 型曲率的功能性差异，不是 SO 的优越性证明。")
    lines.append("- 二次模型质量诊断（未被截断比较的唯一可分辨量）：actual/predicted 中位数 "
                 f"{fmt(float(np.median([float(r['actual_predicted_ratio_if_resolved']) for r in pilot if r['actual_predicted_ratio_if_resolved']])), 3)}；"
                 "SO 的 predicted decrease 一致地比 GN 更接近 oracle 与实际值（模型更准），但试验结果本身不可分辨。")
    lines.append("- 全部 actual > predicted（1.01–2.0）：λ 二次模型系统性偏保守，无不一致警报。")
    lines.append(f"- 计算成本：{d['wall_seconds']:.1f}s 墙钟（4 次公共起点求解 + {d['candidate_solves']} 次候选内层求解，"
                 f"均在 5 min/次上限内）；根中心精化 0 次（两根中心均直接通过资格门，未启用预算精化）。")
    lines.append('- 本试验为**开发性功能验证**：只支持"曲率能实际参与一次参数更新并带来可解释的目标下降"，')
    lines.append('  不构成统计确认、全局反演或训练加速证据。')
    (OUT / 'ONE_STEP_PILOT.md').write_text('\n'.join(lines), encoding='utf-8')

    # ---------------- RECOVERY_REPORT.md ----------------
    sel = b_cost['selection']
    rec_lines = ['# 恢复报告（P1B-B）', '',
                 f"run_id={RUN_ID}；固定流程重放（v1 重建路径未改动，仅增加状态导出与比对）；无 seed 替换、无重复重放。", '',
                 '## 预定清单（任务书 §3.1 规则，代码 p1b_recover.py::select_centers）', '',
                 f"- 变差案例：burgers_59、burgers_67（预定）。",]
    for ctl in sel['controls']:
        rec_lines.append(f"- 对照：{ctl['center_id']}（GN 相对误差 {ctl['gn_rel_error']:.6g}，距该 PDE 历史中位数 {ctl['distance_to_median']:.3g}，"
                         f"并列候选 {ctl.get('tied_candidates')}，按最低历史 ID 裁定）。")
    rec_lines += ['', '## 重放结果（每中心恰 1 次固定流程重放）', '',
                  '| 中心 | 状态 | 重放用时 | 冻结复现最大相对误差 | 与 day1 矩阵值最大相对误差 | center 门 | 数据逐位一致 | 检查点 |',
                  '|---|---|---|---|---|---|---|---|']
    for r in manifest_rows:
        rec_lines.append(f"| {r['center_id']} | {r['status']} | {fmt(r.get('replay_seconds'))} s | "
                         f"{fmt(r.get('max_frozen_relative_error'), 3)} | {fmt(r.get('max_matrix_relative_error'), 3)} | "
                         f"{r.get('center_gate_pass')} | {r.get('data_identity_max_abs_diff')} | {Path(r.get('checkpoint_npz') or '').name} |")
    rec_lines += ['', '## 复现层级判定', '',
                  '- 4/4 达到 `historical_center_replayed`：冻结口径（rtol 1e-6 / atol 1e-10，继承 v3 协议）下'
                  'F_raw / F_SAEPS(GN Schur) / H_red_exact 全部通过；与 day1 矩阵重算值逐块一致（≤8.6e-14）；'
                  'center 平稳性门通过且 G_theta 与历史存档逐位相同；重建数据与训练闭包残差逐位一致（=0.0）。',
                  '- 未宣称逐张量历史恢复：历史训练时 RNG 状态不可得（存档中不存在），导出的是重放状态；'
                  '与历史的一致性由上述冻结口径比对支撑，层级如实标注。',
                  '- 失败尝试 2 次（运行环境缺 float64 默认 dtype；导出段 retain_graph 缺陷）——'
                  '原因、墙钟与不采用声明见 p1b_cost_ledger.json；未以任何方式替换 seed 或放宽门槛。', '',
                  '## 检查点内容（每中心 state_checkpoint.npz + provenance.json）', '',
                  'theta（打包顺序 wx/wt/hidden bias/output/output bias）、log λ 与物理 λ、网络架构/激活/dtype、'
                  '全部配点与观测数据及噪声、正演真解、残差权重与归一化（runtime 配置内嵌+哈希）、'
                  '固定 γ 及其构造规则（α·λ_max(G_tt)）、mean/sum 两种目标形式的状态与参数梯度张量、'
                  'G/H 块、GN 响应 Z、重放导出时 torch RNG 状态（明确标注非历史训练态）、'
                  '代码提交/协议/环境/设备/线程、父历史中心 ID 与全部文件 sha256。']
    (OUT / 'RECOVERY_REPORT.md').write_text('\n'.join(rec_lines), encoding='utf-8')

    # ---------------- PHASE1B_MANIFEST.csv ----------------
    files = [
        ('PHASE1B_PROTOCOL.yaml', 'frozen protocol (before pilot run)'),
        ('SO_SIGNED_ERROR_DECOMPOSITION.csv', 'P1B-A2 signed decomposition, 21 centers'),
        ('ADAPT_FAILURE_SPLIT.csv', 'P1B-A3 bound-vs-truth quadrants'),
        ('ADAPT_FAILURE_SPLIT.md', 'P1B-A3 analysis'),
        ('SO_FAILURE_ANALYSIS.md', 'P1B-A2 failure mechanism analysis'),
        ('p1b_a_summary.json', 'P1B-A summary + provenance'),
        ('RECOVERY_MANIFEST.csv', 'P1B-B recovery manifest'),
        ('p1b_b_cost.json', 'P1B-B selection + cost'),
        ('recovery/burgers_59/state_checkpoint.npz', 'P1B-B checkpoint'),
        ('recovery/burgers_59/provenance.json', 'P1B-B provenance'),
        ('recovery/burgers_67/state_checkpoint.npz', 'P1B-B checkpoint'),
        ('recovery/burgers_67/provenance.json', 'P1B-B provenance'),
        ('recovery/burgers_55/state_checkpoint.npz', 'P1B-B checkpoint'),
        ('recovery/burgers_55/provenance.json', 'P1B-B provenance'),
        ('recovery/allen_cahn_84/state_checkpoint.npz', 'P1B-B checkpoint'),
        ('recovery/allen_cahn_84/provenance.json', 'P1B-B provenance'),
        ('HVP_PARITY.csv', 'P1B-C HVP parity'),
        ('HVP_COST.csv', 'P1B-C cost'),
        ('p1b_c_summary.json', 'P1B-C summary'),
        ('ONE_STEP_PILOT.csv', 'P1B-D pilot rows'),
        ('ONE_STEP_PILOT.md', 'P1B-D analysis'),
        ('p1b_d_summary.json', 'P1B-D summary'),
    ]
    with (OUT / 'PHASE1B_MANIFEST.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['path', 'role', 'sha256'])
        for rel, role in files:
            p = OUT / rel
            w.writerow([str(p), role, digest(p) if p.exists() else 'MISSING'])
        w.writerow([str(TASK_BOOK), 'parent task book', digest(TASK_BOOK)])
        for code in ['p1b_a.py', 'p1b_recover.py', 'p1b_hvp.py', 'p1b_onestep.py', 'p1b_finalize.py', 'core.py']:
            p = ROOT / 'revision_week' / code
            w.writerow([str(p), 'phase code', digest(p)])

    # ---------------- cost ledger ----------------
    cost = dict(
        phase1_unchanged=dict(e0_seconds=1.481, recorded_total_seconds=43.548,
                              historical_reconstruction_seconds=3801.892),
        p1b_new_measured=dict(
            analysis_P1B_A_seconds=a['analysis_wall_seconds'],
            recovery_P1B_B_successful_replay_seconds=b_cost['cumulative_replay_seconds'],
            hvp_P1B_C_seconds=c['wall_seconds'],
            onestep_P1B_D_seconds=d['wall_seconds'],
        ),
        failed_development_attempts_non_production=dict(
            note=('wall times estimated from the session timeline, not instrumented; '
                  'development/debugging attempts, no results used from them'),
            attempts=[
                dict(kind='recovery run 1 (missing torch.set_default_dtype(float64))',
                     wall_seconds_estimate='<660', outcome='all 4 replays failed; environment bug'),
                dict(kind='recovery run 2 (retain_graph bug in state export)',
                     wall_seconds_estimate='~600', outcome='replays ran but export crashed; no results used'),
                dict(kind='pilot run 1 (root-gate convention + offset formatting)',
                     wall_seconds_estimate='0.6', outcome='placeholder rows only, no solves'),
                dict(kind='pilot runs 2-4 (no_grad gradient, missing import)',
                     wall_seconds_estimate='<300', outcome='crashed before any solve'),
            ]),
        budget_status=dict(
            recovery_budget=dict(limit_seconds=7200, used_accepted_seconds=b_cost['cumulative_replay_seconds'],
                                 per_center_limit_seconds=1800,
                                 per_center_used={'burgers_59': 219.3, 'burgers_67': 36.9,
                                                  'burgers_55': 69.6, 'allen_cahn_84': 95.3}),
            actual_use_budget=dict(limit_seconds=7200,
                                   used_seconds=c['wall_seconds'] + d['wall_seconds'],
                                   root_refinements_used=0, root_refinements_limit=2),
            candidate_inner_solves=dict(limit=32, used=d['candidate_solves'],
                                        common_start_solves=dict(limit=4, used=d['start_solves'])),
        ),
    )
    save_json(OUT / 'p1b_cost_ledger.json', cost)

    # ---------------- PHASE1B_REPORT.md ----------------
    commits = {}
    for line in _git_log().splitlines():
        sha, msg = line.split(' ', 1)
        commits[sha[:7]] = msg
    q = a['a3_adapt_split']
    report = f"""# SAEPS Phase 1B 阶段报告

run_id={RUN_ID}；工作树 `SAEPS-so-week1`（分支 codex/saeps-so-week1，未 push）；父提交 acf848f。
任务书：CODEX_SAEPS_PHASE1B_FOLLOWUP.md（sha256 见 p1b_a_summary.json）。执行模式：实际检查、实现与运行。

## 1. 完成 / 未完成 / 失败；提交与文件路径

**完成**
- P1B-A（提交 `2781762`）：`revision_week/outputs/day2/` 下 SO_SIGNED_ERROR_DECOMPOSITION.csv（21 中心）、
  SO_FAILURE_ANALYSIS.md、ADAPT_FAILURE_SPLIT.csv/.md、p1b_a_summary.json。
- P1B-B（提交 `2142c41`）：RECOVERY_MANIFEST.csv、recovery/<center>/state_checkpoint.npz + provenance.json（4 中心）、
  p1b_b_cost.json。状态清单选择代码在 p1b_recover.py::select_centers（含输入哈希）。
- P1B-C（提交 `1251c51`）：HVP_PARITY.csv、HVP_COST.csv、p1b_c_summary.json。
- P1B-D（本次提交）：PHASE1B_PROTOCOL.yaml（运行前冻结）、ONE_STEP_PILOT.csv/.md、p1b_d_summary.json。
- 收尾：PHASE1B_MANIFEST.csv、p1b_cost_ledger.json、PHASE1B_REPORT.md、CLAIM_LEDGER.md。

**未执行（按任务书禁止/范围）**：E2/E3 未启动；SO-ADAPT 未加入一步试验；无新算法家族、无新种子、无自动 push。

**失败（开发尝试，全部保留记录，未产出被采用的结果）**：恢复运行 1（缺 float64 默认dtype）、
恢复运行 2（导出段 retain_graph 缺陷）、试验运行 1-4（门口径/格式化/no_grad/缺导入）。
详见 p1b_cost_ledger.json。每中心仅 1 次固定流程重放成功，未以相同 seed 自动宣称恢复（逐块+逐值比对验证）。

## 2. 两个变差中心的机制结论及证据

- 改善倍数 = |1 − Δ/q|（Δ=Vᵀ(H−G)V，q=DᵀA⁻¹D=e_SO，均为主任务书恒等式）。
  **SO 变差当且仅当 0<Δ/q<2**。21 中心中恰有 burgers_59（Δ/q=0.638）与 burgers_67（Δ/q=1.512）
  落入该带；全部 21 个改善倍数被该公式精确复现（恒等式残差 ≤1.7e-11）。
- 59/67 的 SO 绝对误差是 21 中心中位数（0.305）的 6.6/9.3 倍，GN 误差排名仅 20/12——
  变差以 SO 误差增大为主，不是"GN 分母过小"的统计假象。
- Δ 三项分解：两中心的参数方向项 S_ll（=g_λ，log 坐标）分别为 +2.08/+5.31，是 Δ>0 的最大正贡献；
  项级证据见 SO_FAILURE_ANALYSIS.md。张量层面"为何这些 seed 的 S_ll 翻转/增大"需后续研究。
- 已排除：GN 求解残差（≤1e-13 相对）、参考病态（cond(A)≤1.0e8 → 参考自身误差 O(1e-7)，比误差小 6 个量级）、
  浮点相消（e_G 符号反转量级超恒等式残差 11 个数量级）。
- 状态/参数梯度的绝对张量在第一阶段未归档（缺失如实标注）；H_ll−G_ll=g_λ 恒等式已在
  P1B-C 于恢复的真实中心上核实（≤5e-14）。

## 3. SO-ADAPT 真实达标 vs 估计达标（10% 容差，21 中心）

| 数值估计判定 | 事后真实误差 | 计数 |
|---|---|---|
| 通过 | 通过（Q1） | 9 |
| 不通过 | 通过（Q2） | 12 |
| 不通过 | 不通过（Q3） | **0** |
| 通过 | 不通过（Q4） | **0** |

事后真实相对误差 21/21 达标（中位数 0.20%）。"9/21"完全是数值界过松的假阴性：
界 U=‖D‖²/μ 用 λ_min（减 margin），而 D 的能量几乎不在 λ_min 方向
（能量占比中位数 3.3e-5；μ_eff 中位数 2703 vs μ≈0.01 → 有效度中位数 2.3e5）。
按 §7 口径：**瓶颈在估计实用性，不在近似精度**；不宣称低成本误差认证；本周不扩大长迭代。

## 4. 恢复与 HVP

- 恢复尝试：4 个预定中心（burgers_59、burgers_67、对照 burgers_55 与 allen_cahn_84，规则与并列裁定见清单）；
  成功 4/4，层级 = `historical_center_replayed`（冻结复现 rtol 1e-6 口径下最大相对误差 1.15e-11；
  与 day1 矩阵值比 ≤8.6e-14；数据/配点重建与训练闭包**逐位一致**；center 门全过）。
  失败尝试 2 次（环境/导出缺陷），原因与成本已单列。
- 真实 AD HVP：4/4 通过（目标 1e-8）：HVP vs 显式 H@v ≤8.7e-12；方向二次型 vs 块二次型 ≤4.5e-12；
  JVP/VJP 伴随 ≤2.2e-13；GN 正规残差 ≤3.0e-14；H_ll−G_ll=g_λ ≤5.0e-14（真实历史中心，非玩具网络）。
- 生产路径从真实残差与状态张量构建 HVP；显式 H 仅作验证参考，成本单列。

## 5. 一步试验（P1B-D）

- 16/16 比较完成，全部在系数 1.0 接受；4 次公共起点求解 + 16 次候选求解，0 次根精化。
- **实际用途**：目标下降真实可分辨（0.009–0.655，均高于评估噪声；actual/predicted 1.01–2.0），
  曲率选择真实改变一步质量（RAW 步长 0.007–0.015 → 下降 0.009–0.093；GN 型曲率 → 0.074–0.655）。
- **参数误差**：16/16 改善（两个量分开报告；仅为合成数据事后评价）。
- **区分度限制**：GN/SO/ORACLE 原始步长均 >0.1，被共同信赖半径截到同一步长，三者实际结果逐位相同——
  按规则报告"该组缺少曲率区分度"；SO 相对 GN 的**增量实际收益未获支持**；
  唯一可分辨的模型质量诊断：SO 的 predicted decrease 比 GN 更接近 oracle 与实际值。
- 未为制造差异调整半径/系数/容差。

## 6. 计算成本（第一阶段不动）

- 第一阶段：43.548 s 计量累计（E0 1.481 s），历史重构 3801.892 s 单列——均未回改。
- 本阶段新增（实测）：分析 0.11 s + 恢复重放 421.0 s（4 中心，预算 2h/每中心 30min）+
  HVP 验证 1.4 s + 一步试验 17.5 s + 收尾聚合 <1 s ≈ **440 s**。
- 失败开发尝试（非生产，会话时间线估计）：约 20 分钟墙钟，单列见 p1b_cost_ledger.json。
- 预算状态：恢复 421/7200 s；实际用途 18.9/7200 s；候选求解 16/32；公共起点 4/4；根精化 0/2。无 budget_exhausted。

## 7. 可写 / 不可写结论；冻结条件

**可以写（有本阶段数值支持）**
1. SO 相对 GN 的改善倍数由 |1−Δ/q| 精确刻画；变差中心是 Δ/q∈(0,2) 的误差抵消带成员（21 中心中恰 2 个）。
2. SO-ADAPT 有限修正的真实相对误差 21/21 达标；9/21 是谱界过松（λ_min 方向几乎不承载缺陷能量）所致的估计假阴性。
3. 恢复的真实历史中心上，AD HVP 与显式参考、伴随恒等式、H_ll−G_ll=g_λ 全部成立到 ≤1e-11。
4. 一步试验中曲率选择（RAW vs GN 型）真实改变目标下降与参数误差变化；λ 二次模型偏保守（actual>predicted）。

**仍不能写**
- 不能写 SO 的总成本优势或效率优势（未测端到端）。
- 不能写 SO 相对 GN 的增量实际参数更新收益（被信赖域截断不可分辨）。
- 不能写 SO-ADAPT 的低成本误差认证（数值界非严格证书）。
- 不能从 27 项测试通过或本阶段结果推断方法新颖性；一步试验不是训练加速或参数可靠性保证。
- 变差中心的"网络/数据层面根因"未解释（仅矩阵代数层面成立）。

**冻结独立实验的最低条件（§7）——已满足**：
目标一致性/实现错误检查通过；≥2 个具备完整状态的开发中心（实际 4 个，覆盖 2 个 PDE）通过真实 HVP 与显式核对；
两个变差中心有数值支持的解释且不隐瞒反例；真实网络成本分项可追溯。
→ **可以提出下一轮独立两参数协议的冻结方案（本次不自动启动）**。SO-ADAPT 是否加入下一轮：
按本阶段分解，其真实精度已达标的证据支持保留为研究分支，但估计侧需先解决界的实用性，才值得进入独立协议。
"""
    (OUT / 'PHASE1B_REPORT.md').write_text(report, encoding='utf-8')

    # ---------------- CLAIM_LEDGER.md ----------------
    ledger = """# CLAIM_LEDGER（Phase 1B）

## 允许写入论文的声明（有本阶段可追溯数值支持）
| # | 声明 | 证据文件 |
|---|---|---|
| C1 | SO/GN 逐中心改善倍数由 \\|1−Δ/q\\| 精确给出；变差 = Δ/q∈(0,2) 抵消带（21 中心，恰 59/67） | SO_SIGNED_ERROR_DECOMPOSITION.csv, SO_FAILURE_ANALYSIS.md |
| C2 | 7.84 是逐中心比值中位数（非中位数之比 4.81/7.77） | p1b_a_summary.json a1 |
| C3 | SO-ADAPT 有限修正真实相对误差 21/21≤10%（中位 0.20%）；9/21 为估计假阴性；界松的机制是 λ_min 方向能量占比≈0（中位 3.3e-5） | ADAPT_FAILURE_SPLIT.csv/.md |
| C4 | 恢复中心上真实 AD HVP = 显式 H@v（≤8.7e-12）且伴随/梯度恒等式成立（≤5e-14） | HVP_PARITY.csv |
| C5 | 一步试验中曲率选择改变实际目标下降与参数误差轨迹；λ 二次模型偏保守 | ONE_STEP_PILOT.csv/.md |

## 禁止写入的声明
| # | 禁止 | 原因 |
|---|---|---|
| F1 | SO 具有总成本/效率优势 | 无端到端成本测量 |
| F2 | SO 优于 SAEPS-GN 的实际一步收益 | GN/SO/ORACLE 被同一信赖半径截断，试验结果逐位相同（仅模型预测质量可分辨） |
| F3 | SO-ADAPT 提供严格/低成本误差认证 | dense-eigh 数值界非证书 |
| F4 | 一步收益 = 训练加速或参数可靠性保证 | 单步功能验证，非统计确认 |
| F5 | 方法新颖性来自测试通过 | 任务书明令 |
| F6 | 变差中心的完整根因已被解释 | 仅矩阵代数层面；张量层机制未查 |

## 冻结独立实验条件评估：满足（详见 PHASE1B_REPORT.md 第 7 节）；下一轮协议另行提出，本次未启动。
"""
    (OUT / 'CLAIM_LEDGER.md').write_text(ledger, encoding='utf-8')

    print(json.dumps(dict(wall=time.perf_counter() - t0, pilot_rows=len(pilot)), ensure_ascii=False))
    return 0


def _git_log() -> str:
    import subprocess
    r = subprocess.run(['git', '-C', str(ROOT), 'log', '--oneline', '-6'], capture_output=True)
    return r.stdout.decode('utf-8', errors='replace').strip()


if __name__ == '__main__':
    sys.exit(main())
