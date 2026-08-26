# SAEPS JCP 级可执行实验契约 v2.0

> **HISTORICAL v2 PROTOCOL — not the current paper-facing evidence state.** See [`../V5_FINAL_JCP_AUDIT_REPORT.md`](../V5_FINAL_JCP_AUDIT_REPORT.md) for the V5 final audit. The protocol below remains preserved as executed history.

**Contract ID:** `SAEPS-JCP-EXEC-v2.0`  
**状态:** `ACTIVE / PRE-IMPLEMENTATION`  
**最新来源:** `SAEPS 新仓库实验任务书 v2.0.md`  
**来源 SHA256:** `FD7F2675719F98997236D735CED8181D631A939835DF6A08A9192FBE6266B07C`

## 1. 权威性与版本链

本契约是 v2.0 任务书的可执行化版本。历史来源和修订保存在 `docs/protocol_amendments/`。

解释顺序：

1. v2.0 决定当前科学范围、阶段、工作量和论文交付；
2. 旧协议中不冲突且更严格的数值正确性、审计和 provenance 要求继续有效；
3. `docs/LOCKED_PROTOCOL.md` 一旦进入 `LOCKED` 状态，其 confirmation 配置不可变；
4. 任务书中的“例如”“建议”不自动变成未声明的数值；需要 development 证据的项目必须在 LOCK 前确定；
5. confirmation 后不得用结果反向修改科学设计。

## 2. 唯一科学问题

> SAEPS 的局部 neural-state elimination，能否比 raw fixed-network sensitivity 更准确地预测物理参数扰动且 PINN 神经状态重新优化后形成的 nonlinear reduced objective 局部几何？

比较：

\[
F_\lambda^{raw}=J_\lambda^\top J_\lambda,
\qquad
F_\lambda^{se}=J_\lambda^\top A_\theta^{(\gamma)}J_\lambda,
\]

与 gold standard：

\[
H_{prof}=\nabla_\lambda^2\left[\min_\theta L(\theta,\lambda)\right].
\]

## 3. 允许主张与禁止外推

只有数据支持时，才允许主张：

1. explicit/SVD/matrix-free 实现在 numerical tolerance 内一致；
2. tangent overlap 越高，retained sensitivity 越低；
3. scalar inverse PDE 中 \(F^{se}\) 比 \(F^{raw}\) 更接近 \(H_{prof}\)；
4. two-parameter 问题中 \(F^{se}\) eigendirections 能预测 nonlinear strong/weak directions。

禁止声称 global identifiability、posterior uncertainty、固有参数可靠度、通用可靠性阈值、PDE 固有 score-misalignment 或对所有 inverse PINNs 普遍成立。全部表述必须限定为 `local, checkpoint-dependent, residual-space diagnostic`。

10 个 confirmation seeds 支持 across-seed reproducibility；controlled、scalar、multi-parameter 三类实验提供有限 across-problem evidence，但不构成普适性证明。

## 4. 种子、数据划分与锁定

### 4.1 固定核心 seeds

```yaml
development_seeds: [0, 1, 2]
confirmation_seeds: [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
```

Development 仅用于 debugging、optimizer tuning、benchmark feasibility、profile interval、stationarity threshold、damping rule 和 architecture selection，不进入主论文 confirmation statistics。

### 4.2 LOCK 前必须确定

- controlled PDE、truth、Fourier library、source normalization 与 \(q_\parallel,q_\perp\)；
- scalar benchmark、parameter coordinate 和 conventional solver；
- network architecture、dtype、point layouts、sensor layout 和 loss weights；
- optimizer、deterministic stopping rule 和统一追加训练规则；
- residual 与 stationarity thresholds；
- profile interval、fit window、fit-quality threshold 和 missing-point rule；
- gamma grid、nominal gamma algorithm 和 plateau tolerance；
- paired bootstrap CI 方法、resample count、RNG seed、invalid-pair rule；
- robustness 5-seed 列表、narrow/wide 定义；
- aggregation、scientific-gate、figure 和 table code。

LOCK 时生成 `docs/LOCKED_PROTOCOL.md`、`configs/locked/`、SHA256、git commit、日期和 decision reason。首次 confirmation run 后不可覆盖。

## 5. 阶段与推进规则

```text
P0 Repository
  -> P1 Numerical core validation
  -> P2 Controlled geometry
  -> P3 Nonlinear profile engine
  -> P4 Scalar PDE screening
  -> LOCK
  -> P5 Scalar confirmation
  -> P6 Multi-parameter confirmation
  -> P7 Robustness
  -> P8 Computational cost
  -> P9 Final audit
```

- 每一阶段 engineering gate 通过后才能进入下一阶段；
- 每个完成阶段必须有可追溯 commit；
- engineering failure 必须修复；locked scientific failure 必须报告，不得调参消除；
- P5 若不支持核心 scalar 命题，停止大规模 P7 robustness，记录 `completion_mode: PROTOCOL_STOP`，该停止不构成工程失败；
- P8 成本数据从所有阶段持续采集，最终分析在 P8 完成；
- scientific FAIL 不使 repository validator 返回工程失败。

## 6. 通用运行状态与 provenance

每个预注册 run 必须且只能有一个最终状态：

```text
PASS
CHECKPOINT_INVALID
PROFILE_FAILURE
SOLVER_FAILURE
NUMERICAL_FAILURE
```

不得缺失。论文必须报告完整 denominator，例如 `8/10 checkpoints passed`，不能只写 `n=8`。

每个 run 至少保存：

```text
schema_version, run_id, timestamp, git_commit, config_path, config_hash,
seed, split, benchmark, architecture, dtype, hardware,
parameter_coordinates, training_points, diagnostic_points, sensor_layout,
loss_weights, optimizer, learning_rate, training_stop_reason,
checkpoint_epoch, theta_stationarity, lambda_stationarity,
residuals, state_error, parameter_error,
gamma_alpha, gamma, CG_iterations, CG_relative_residual,
JVP_count, VJP_count, Fraw, Fse, gse, eta,
profile_points, profile_curvature, profile_fit_quality,
E_saeps, E_raw, D_paired,
training_time, saeps_time, frozen_profile_time, reoptimized_profile_time,
peak_memory, status, failure_reason
```

Truth-dependent state/parameter error 必须标记 `validation_only`。矩阵、profile 和 timing 必须为机器可读数值。

## 7. Checkpoint 与 profile 有效性

正式 checkpoint 必须报告：

\[
S_\theta=\frac{\|J_\theta^\top\bar r\|}{\|J_\theta\|\|\bar r\|+\epsilon},
\qquad
S_\lambda=\frac{\|J_\lambda^\top\bar r\|}{\|J_\lambda\|\|\bar r\|+\epsilon},
\]

以及 PDE、observation、BC/IC residual；synthetic only 的 state error 和 validation-only parameter error。阈值在 development 确定并 LOCK。

每个 reoptimized profile point 必须：

- 从相同 \(\theta_0\) 初始化；
- 禁止 previous-point continuation；
- 使用相同 optimizer/stopping rule；
- 同时检查 deterministic optimizer termination、loss-change plateau 和 normalized \(\theta\)-gradient threshold；
- 不以固定 N epochs 作为唯一完成标准；
- missing/failed point 明确标记，禁止静默插值。

## 8. Gamma 协议

\[
\gamma=\gamma_\alpha\lambda_{max}(J_\theta^\top J_\theta),
\qquad
\gamma_\alpha\in\{10^{-12},10^{-10},10^{-8},10^{-6},10^{-4},10^{-2}\}.
\]

完整 sweep 必须报告。Nominal gamma 只能按 LOCK 前写入代码的算法选择，同时考虑 CG stability、local plateau 和 adjacent log-scale change tolerance；禁止查看 confirmation Figure 后人工选择。

## 9. P0 — Repository Bootstrap

**前置:** 无。Git 已初始化于 `main`，当前尚无 commit。  
**任务:** Python package、固定 Python/dependencies、CI、seed/config/logging/provenance、README、license、`.gitignore`、`src/ tests/ configs/ scripts/ outputs/ paper_artifacts/`。  
**必须记录:** Python/package versions、seed、git commit、config hash、hardware、dtype、timestamp。  
**命令:**

```bash
pytest -q
python scripts/00_smoke_test.py
```

**PASS:** tiny PINN 实际训练、checkpoint 保存/reload、residual 重算与保存前在锁定 tolerance 内一致；两命令退出码 0。

## 10. P1 — SAEPS Core Verification

**前置:** P0 PASS。  
**实现:** residual-first API、parameter transform、JVP/VJP、explicit \(J_\theta,J_\lambda\)、SVD exact reference、explicit Tikhonov、matrix-free CG/Krylov、共享 `Fraw/Fse/gse/eta` 实现。Core 不得包含具体 PDE，也不得为 benchmark 复制实现。  
**硬验收:** 

1. 至少 10 个记录 seed 的随机 \(y\)：
   \[
   \frac{\|A_{MF}y-A_{explicit}y\|}{\|A_{explicit}y\|+\epsilon}<10^{-6};
   \]
2. Curvature relative Frobenius error \(<10^{-6}\)；
3. Symmetry relative error \(<10^{-8}\)；
4. \(\lambda_{min}(F^{se})\ge-10^{-8}\lambda_{max}(F^{se})\)；
5. \(F^{raw}-F^{se}\succeq0\) 至 numerical tolerance；
6. 所有正式 CG relative residual \(\le10^{-8}\)；
7. scalar \(-10^{-8}\le\eta^{se}\le1+10^{-8}\)；
8. 相同 config+seed 重复运行在预注册 tolerance 内一致；
9. finite difference 与 autodiff derivative 在预注册 tolerance 内一致。

**PASS:** 全部通过，否则不得开始科学实验。

## 11. P2 — Controlled Tangent Geometry

**前置:** P1 PASS。  
**PDE:** manufactured parabolic PDE；固定 \(D,c,\lambda^*,u^*\)，forcing 保证 source family 共用 truth。  
**Development:** seeds `[0,1,2]`；以
\[
\omega(q)=q^\top P_\theta q/(q^\top q)
\]
从固定 Fourier library 选择并锁定归一化 \(q_\parallel,q_\perp\)。  
**Confirmation:** 10 seeds ×
\[
q_\alpha=\sqrt{1-\alpha}q_\parallel+\sqrt\alpha q_\perp,
\quad\alpha\in\{0,0.25,0.5,0.75,1\},
\]
共 50 evaluations。  
**输出:** all seed values、每 seed \(\rho_i=Spearman(\alpha,\eta^{se})\)、median、IQR、monotonicity status、Figure 2。  
**Engineering PASS:** 50/50 有最终状态、无隐藏排除、自动聚合与图可重建。  
**Scientific SG-1 PASS:** \(median_i\rho_i\ge0.9\)，且至少 8/10 seeds 显示 LOCK 前定义的正确单调趋势。

## 12. P3 — Nonlinear State-Reoptimization Engine

**前置:** P2 engineering PASS。  
**API:** `profile_frozen()`、`profile_reoptimized()`、`fit_local_quadratic()`、`estimate_curvature()`、`estimate_profile_minimum()`、`compare_curvature()`。  
**默认点:** `[-0.15,-0.10,-0.05,0,0.05,0.10,0.15]`，仅可在 development 证明超出 local quadratic regime 时统一修改并 LOCK。  
**PASS:** synthetic known-curvature test、point-order invariance、independent-initialization reproducibility、fit-quality tests 通过；failed optimization 有状态；missing point 无静默插值。

## 13. P4 — Scalar Physical PDE Screening & LOCK

**前置:** P3 PASS。  
**候选:** 仅 `Allen-Cahn`、`Burgers`；development seeds `[0,1,2]`。  
**允许依据:** forward/PINN/profile numerical feasibility、classical forward profile 明确局部 minimum、joint stationarity passing count、CG/Jacobian stability。  
**禁止依据:** 更低 \(\eta^{se}\)、SAEPS 优势更大、Figure 更漂亮或更像预期 regime。  
**固定选择顺序:** hard numerical gates → stationarity passing count → classical curvature clarity → reoptimization failure rate → alphabetical name。  
**输出:** 全部 screening raw results、未入选结果进入 Supplementary、`configs/locked/scalar.yaml`、`docs/DECISIONS.md`。  
**LOCK PASS:** `docs/LOCKED_PROTOCOL.md` 记录 SHA256、git commit、date、decision reason，且第 4.2 节项目全部冻结。

## 14. P5 — Scalar Confirmation

**前置:** LOCK PASS。  
**工作量:** 全部 10 confirmation seeds。  
**每 seed:** training → stationarity → SAEPS → frozen profile → independent nonlinear reoptimized profile → independent classical forward profile → local curvature fit → automatic comparison。  
**指标:**

\[
E_{SAEPS}=\frac{|F^{se}-H_{profile}|}{|H_{profile}|+\epsilon},
\quad
E_{raw}=\frac{|F^{raw}-H_{profile}|}{|H_{profile}|+\epsilon},
\quad
D_i=E_{raw,i}-E_{SAEPS,i},
\]

\[
\eta_{profile}=H_{profile}/(H_{frozen}+\epsilon).
\]

必须报告 \(\eta^{se}\) vs \(\eta_{profile}\) scatter、correlation、absolute error、per-seed values，以及 paired wins、\(median(D)\)、paired bootstrap 95% CI。

**Engineering PASS:** 10/10 有最终状态；planned/valid/invalid/failed denominator 完整；profile raw data、fit quality、classical control、Figures 3–4、Table 2 自动生成。  
**Scientific SG-2 分类:** 

- `STRONGLY_SUPPORTED`: 至少 9/10 预注册 seeds 为有效 paired wins，\(median(D)>0\)，paired bootstrap 95% CI lower \(>0\)；
- `SUPPORTED_WITH_UNCERTAINTY`: 9/10 与 \(median(D)>0\) 成立，但 CI 跨 0；
- `PARTIALLY_SUPPORTED`: 存在轻微/不稳定优势，但不满足上述两级；
- `NOT_SUPPORTED`: \(median(D)\le0\) 或 nonlinear profiles 系统性不支持 SAEPS。

不得把 9/10 改成 9/N。若 P5 为 `NOT_SUPPORTED`，P7 大规模 robustness 触发 `PROTOCOL_STOP`。

Classical profile 若本身平坦，不得把低 retained signal 单独解释为 PINN-specific state absorption。

## 15. P6 — Two-Parameter Confirmation

**前置:** P5 engineering PASS。  
**Benchmark:** coupled reaction-diffusion joint target \((\log a,\log b)\)，禁止逐坐标标签。  
**Seeds:** 全部 10 confirmation seeds。  
**输出:** full \(F^{raw},F^{se}\)、eigenvalues/eigenvectors、condition number、trace、numerically meaningful determinant、normalized off-diagonal coupling；每 seed 沿 \(v_{max},v_{min}\) 的 nonlinear profiles；directional curvature ratio error；Table 3。  
**Representative 2D:** 按固定规则选择升序第一个 valid confirmation seed，运行 \(5\times5\) reoptimized grid，生成 contour、SAEPS ellipse 和 eigendirection visualization；不得挑最好看的 seed。  
**Engineering PASS:** 10/10 有最终状态，full matrices、directional profiles 和代表二维 grid 可自动重建。  
**Scientific SG-3 PASS:** 至少 9/10 valid confirmation seeds 满足
\[
H_{prof}(v_{max})>H_{prof}(v_{min}),
\]
与 SAEPS strong/weak ordering 一致，并完整报告 ratio error。

## 16. P7 — Robustness & Architecture Transfer

**前置:** P5、P6 engineering 完成；若 P5 `NOT_SUPPORTED`，按协议停止并记录 `completion_mode: PROTOCOL_STOP`。  
**Scalar robustness:** 
\[
\sigma\in\{0,10^{-3},10^{-2}\},\qquad f\in\{0.25,0.5,1.0\},
\]
共 9 conditions，每 condition 5 个预注册 seeds，最大 45 runs。  
**Architecture:** scalar-only；nominal 使用核心 10 seeds，narrow 5，wide 5。  
**Scientific定位:** stress test，不设强阳性门槛；报告 effect 是否崩溃、stationarity、SAEPS/raw 趋势和失效条件。不得用失败 cell 修改方法。  
**Engineering PASS:** 执行全部预注册 runs 并保留失败；或 P5 失败时正确执行并记录 protocol stop。

## 17. P8 — Computational Cost

**前置:** 核心确认完成；timing instrumentation 从 P0 起启用。  
**必须记录:** training、SAEPS、frozen profile、reoptimized profile time；CG iterations；JVP/VJP count；容易获得时的 peak memory。  
**核心报告:**
\[
T_{reoptimized\ profile}/T_{SAEPS}.
\]
**PASS:** 计时口径、hardware、dtype 和 aggregation 可审计；Figure 6 或等价成本表自动生成。任务书未规定硬性成本比阈值，因此不得事后发明 PASS threshold，但最终建议必须讨论实用价值。

## 18. P9 — Paper Artifacts & Final Audit

**前置:** P0–P8 engineering 完成，P7 可为合规 `PROTOCOL_STOP`。  
**命令:**

```bash
python scripts/09_build_paper_artifacts.py
python scripts/validate_repository.py
```

**Figures:** 1 geometry schematic；2 controlled calibration；3 scalar frozen/SAEPS/reoptimized/classical；4 across-seed curvature + paired errors；5 multi-parameter eigendirections/profiles/2D contour；6 robustness or cost。  
**Tables:** 1 benchmark/protocol；2 scalar seed-level confirmation；3 multi-parameter seed-level summary。  
**Supplementary:** development screening、all seeds、failed runs、gamma、CG、stationarity、noise/sparsity、architecture、fit sensitivity、exact/MF、cost detail。  
**PASS:** raw→aggregate→artifacts 全自动；reported aggregates 与 raw seed data 一致；Figures/Tables 可重建；provenance 完整；validator 返回 0。

## 19. 自动聚合与 validator

唯一数据流：

```text
raw run files
  -> aggregation
  -> paper_artifacts/data
  -> figures / tables / report
```

禁止 Excel 手工复制、脚本写死 paper values、LaTeX/Markdown 手填结果。Validator 必须检查 unit tests、seed completeness、locked hashes/config mutation、raw/aggregate consistency、Figure/Table regeneration、failed-run reporting、scientific gates、bootstrap lineage、cost lineage 和 provenance completeness。

退出码：`0 = protocol execution complete`；`1 = engineering execution incomplete`。Scientific FAIL 或 P7 合规 protocol stop 不得返回 1。

## 20. 最终报告与结论映射

`FINAL_VALIDATION_REPORT.md` 必须包含：Repository status、P0–P9 engineering gates、confirmation completeness、scientific results、bootstrap uncertainty、failed runs、protocol deviations、computational cost、scientific conclusion、recommendation。

最终科学结论只能为：

```text
SUPPORTED
PARTIALLY_SUPPORTED
NOT_SUPPORTED
```

推荐只能为：

```text
PROCEED_TO_PAPER
PROCEED_WITH_LIMITED_CLAIMS
REVISE_METHOD
INVESTIGATE_NUMERICS
STOP
```

映射：

- `SUPPORTED / PROCEED_TO_PAPER`: numerical core、controlled gate、scalar strong evidence 和 multi 9/10 成立；robustness 不显示仅限极窄条件；成本体现实际价值；无重大违规；
- `PARTIALLY_SUPPORTED / PROCEED_WITH_LIMITED_CLAIMS`: controlled 强，scalar 有平均优势但 uncertainty 较大，或 multi 仅部分支持；
- `PARTIALLY_SUPPORTED / REVISE_METHOD`: 数学实现正确但核心经验主张不足；
- `NOT_SUPPORTED / REVISE_METHOD|STOP`: \(median(D)\le0\)、profiles 系统性反驳 SAEPS、或无稳定 gamma 区间；
- `INVESTIGATE_NUMERICS`: 证据受未解决 stationarity/profile/numerical 问题限制。

## 21. 变更与失败处理

Confirmation 前，development 决策写入 `docs/DECISIONS.md`。Confirmation 后任何科学设计变更必须：停止受影响 runs、保留原结果、写入 `docs/ISSUES.md`、不覆盖 locked config；如需新协议则新建版本和 split，不与原 confirmation 混合。

不得删除不利 seeds、静默排除失败、按 SAEPS 结果选 benchmark、修改 locked architecture/weights/sensors/profile/gamma/threshold、挑代表 seed、硬编码 paper 数值或将局部结论扩展为普适结论。

## 22. 完成定义

项目完成要求：

- P0–P9 mandatory engineering work 完成；P7 可为契约授权的 `PROTOCOL_STOP`；
- 所有预注册 runs 有合法最终状态；
- locked protocol 与 hashes 可审计；
- tests、smoke、artifact build、validator 实际通过；
- raw data、figures、tables、statistics、bootstrap 和 cost 完全可追溯；
- 自动生成最终报告并给出唯一结论与建议；
- `git status` 干净，阶段 commits 和最终 commit 可追溯。

科学结果为负不构成 Codex Goal 失败。
