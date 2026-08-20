# TASKS.md — SAEPS v2.0

> 最高执行协议：`docs/EXECUTION_CONTRACT.md`（`SAEPS-JCP-EXEC-v2.0`）。

## 状态规则

阶段状态：`NOT_STARTED`、`IN_PROGRESS`、`BLOCKED`、`PASSED`、`FAILED`。任一时刻最多一个阶段为 `IN_PROGRESS`；前一阶段 engineering gate 未 `PASSED`，不得进入下一阶段。P7 可按契约记录 `PASSED / completion_mode: PROTOCOL_STOP`。

## 总览

| Phase | 名称 | 状态 | Engineering gate | Scientific result |
|---|---|---|---|---|
| P0 | Repository Bootstrap | PASSED | PASSED | N/A |
| P1 | SAEPS Core Verification | PASSED | PASSED | N/A |
| P2 | Controlled Tangent Geometry | PASSED | PASSED | FAIL |
| P3 | Nonlinear Profile Engine | PASSED | PASSED | N/A |
| P4 | Scalar PDE Screening & LOCK | PASSED | PASSED | N/A |
| P5 | Scalar Confirmation | PASSED | PASSED | PARTIALLY_SUPPORTED |
| P6 | Multi-parameter Confirmation | PASSED | PASSED | FAIL |
| P7 | Robustness & Architecture | PASSED | PASSED | DESCRIPTIVE_ONLY |
| P8 | Computational Cost | PASSED | PASSED | DESCRIPTIVE_ONLY |
| P9 | Final Audit | PASSED | PASSED | PARTIALLY_SUPPORTED / INVESTIGATE_NUMERICS |

## P0 — Repository Bootstrap

**状态:** `PASSED` — evidence: `docs/evidence/P0_ACCEPTANCE.md`

- [x] 创建 Python package、`pyproject.toml`、README、LICENSE、`.gitignore`；
- [x] 创建 `src/ tests/ configs/ scripts/ outputs/ paper_artifacts/`；
- [x] 固定 Python 与完整 dependency closure；
- [x] 实现 deterministic seed、config、structured logging、run ID/hash；
- [x] 记录 hardware、dtype、timestamp、git commit；
- [x] 配置 CI；
- [x] 实现 tiny PINN smoke test：train → save → reload → recompute residual → consistency；
- [x] 运行 `pytest -q`：9 passed；
- [x] 运行 `python scripts/00_smoke_test.py`：PASS；
- [x] 保存机器可读与人类可读验收证据；
- [x] 提交 P0 implementation 与 acceptance commits。

## P1 — SAEPS Core Verification

**依赖:** P0 `PASSED`  
**状态:** `PASSED` — evidence: `docs/evidence/P1_ACCEPTANCE.md`

- [x] 实现 residual-first API 和 parameter coordinate transform；
- [x] 实现 explicit \(J_\theta,J_\lambda\)、JVP、VJP；
- [x] 实现 SVD exact reference、explicit Tikhonov、matrix-free CG/Krylov；
- [x] 实现唯一共享的 `Fraw/Fse/gse/eta`；
- [x] 至少 10 个随机 \(y\) 验证 operator relative error `<1e-6`；
- [x] 验证 curvature relative error `<1e-6`；
- [x] 验证 symmetry `<1e-8`；
- [x] 验证 PSD、Loewner relation、scalar eta bound；
- [x] 验证每个正式 CG relative residual `<=1e-8`；
- [x] 验证 finite-difference/autodiff derivatives；
- [x] 验证相同 config+seed 重复运行一致性；
- [x] 保存真实数值测试证据并提交 P1 commit。

## P2 — Controlled Tangent Geometry

**依赖:** P1 `PASSED`  
**状态:** `PASSED` — engineering evidence: `docs/evidence/P2_ACCEPTANCE.md`; scientific SG-1: `FAIL`

### Development

- [x] 仅用 seeds `[0,1,2]` 建立 manufactured parabolic PDE；
- [x] 固定 \(D,c,\lambda^*,u^*\) 和 Fourier library；
- [x] 实现 tangent overlap \(\omega(q)\)；
- [x] 选择、归一化并锁定 \(q_\parallel,q_\perp\)；
- [x] 记录 development evidence、配置 hash 和 decision。

### Confirmation

- [x] 使用 `[10,11,12,13,14,15,16,17,18,19]`；
- [x] 每 seed 运行 5 个 \(\alpha\)，共 50 evaluations；
- [x] 每个 run 有合法最终状态；
- [x] 报告 all seed values、每 seed Spearman、median、IQR 和 monotonicity；
- [x] 自动生成 Figure 2；
- [x] 计算 SG-1：`FAIL`（5/10 valid 且 5/10 单调；valid seeds 的 median Spearman≈1）；
- [x] 保存验收证据并提交 P2 commit。

## P3 — Nonlinear State-Reoptimization Engine

**依赖:** P2 engineering `PASSED`  
**状态:** `PASSED` — evidence: `docs/evidence/P3_ACCEPTANCE.md`

- [x] 实现 `profile_frozen()`、`profile_reoptimized()`；
- [x] 实现 `fit_local_quadratic()`、`estimate_curvature()`；
- [x] 实现 `estimate_profile_minimum()`、`compare_curvature()`；
- [x] 每点从同一 \(\theta_0\) 初始化，禁止 previous-point continuation；
- [x] stopping rule 同时包含 optimizer termination、loss plateau、normalized theta-gradient；
- [x] 实现 synthetic known-curvature test；
- [x] 验证 point-order invariance 与 independent initialization reproducibility；
- [x] failed point 明确标记，禁止静默插值；
- [x] 锁定 fit quality 与 profile failure rules；
- [x] 保存验收证据并提交 P3 commit。

## P4 — Scalar PDE Screening & LOCK

**依赖:** P3 `PASSED`  
**状态:** `PASSED` — evidence: `docs/evidence/P4_SCREENING.md`; lock commit: `ad794ca2908c8935d0e21702fab7914ff944cce7`

- [x] 仅用 seeds `[0,1,2]` 筛选 `Allen-Cahn` 与 `Burgers`；
- [x] 运行 forward/PINN/profile feasibility；
- [x] 验证 conventional profile 的明确局部 minimum；
- [x] 统计 joint stationarity passing count；
- [x] 验证 CG/Jacobian stability；
- [x] 按预注册顺序选择，禁止依据 eta/优势/图形；
- [x] 未入选结果保留用于 Supplementary；
- [x] 创建 `configs/locked/scalar.yaml`；
- [x] 锁定 architecture、sensors、weights、optimizer/stopping、thresholds；
- [x] 锁定 profile interval/fit、gamma algorithm、bootstrap、robustness seeds；
- [x] 更新 `docs/DECISIONS.md`；
- [x] 生成 `docs/LOCKED_PROTOCOL.md` 的 SHA256、commit、date、reason；
- [x] 提交 LOCK commit。

## P5 — Scalar Confirmation

**依赖:** LOCK `PASSED`  
**状态:** `PASSED` — evidence: `docs/evidence/P5_ACCEPTANCE.md`; SG-2: `PARTIALLY_SUPPORTED`

- [x] 运行全部 10 个 confirmation seeds；
- [x] 每 seed 执行 training、stationarity、SAEPS；
- [x] 执行 frozen、independent reoptimized、classical profiles；
- [x] 执行 curvature fitting 与 fit-quality gate；
- [x] 计算有效 seed 的 \(Fraw,Fse,Hprofile,Eraw,Esaeps,D_i\)；
- [x] 计算有效 seed 的 \(\eta^{se}\) 与 \(\eta_{profile}\)；
- [x] 计算 paired wins、median(D)、locked bootstrap 95% CI；
- [x] 报告 planned/valid/invalid/failed denominator；
- [x] 自动生成 curvature-error Figure、Table 2 与完整 profile raw data；
- [x] 分类 SG-2：`PARTIALLY_SUPPORTED`（仅 1/10 valid）；
- [x] SG-2 非 NOT_SUPPORTED，因此 P7 不触发 `PROTOCOL_STOP`；
- [x] 保存验收证据并提交 P5 commit。

## P6 — Multi-parameter Confirmation

**依赖:** P5 engineering `PASSED`  
**状态:** `PASSED` — evidence: `docs/evidence/P6_ACCEPTANCE.md`; SG-3: `FAIL`

- [x] 使用 CRD joint target \((\log a,\log b)\)；
- [x] 运行全部 10 个 confirmation seeds；
- [x] 对通过 solver 的 seeds 计算 full \(Fraw,Fse\)，禁止逐坐标标签；
- [x] 输出可计算 seeds 的 eigenvalues/eigenvectors、condition number、trace、determinant、coupling；
- [x] 对有效 checkpoint 沿 \(v_{max},v_{min}\) 运行 nonlinear profiles；
- [x] 有效方向对为 0，directional ratio error 不可计算；
- [x] first-valid 选择返回空，\(5\times5\) grid 合规标记 `NOT_APPLICABLE_NO_VALID_SEED`；
- [x] 自动生成 Figure 5 和 Table 3；
- [x] 计算 SG-3：`FAIL`（0/10）；
- [x] 保存验收证据并提交 P6 commit。

## P7 — Robustness & Architecture Transfer

**依赖:** P5/P6 engineering 完成  
**状态:** `PASSED` — evidence: `docs/evidence/P7_ACCEPTANCE.md`

- [x] P5 为 PARTIALLY_SUPPORTED，未触发 `PROTOCOL_STOP`；
- [x] 执行 scalar 的 3 noise × 3 observation fractions；
- [x] 9 conditions 每个使用 5 个预注册 seeds，共 45 runs；
- [x] nominal architecture 引用封存的核心 10 seeds，未重复 confirmation；
- [x] narrow 与 wide 各使用 5 个锁定 seeds；
- [x] 报告 effect、stationarity、SAEPS/raw 趋势和失效条件；
- [x] 不设置强阳性 scientific gate；
- [x] 55/55 新 runs 均有最终状态并保存验收证据。

## P8 — Computational Cost

**依赖:** 核心 confirmation 完成  
**状态:** `PASSED` — evidence: `docs/evidence/P8_ACCEPTANCE.md`

- [x] 聚合 training、SAEPS、frozen profile、reoptimized profile times；
- [x] 聚合 CG iterations、JVP/VJP counts；
- [x] peak memory 因 CPU backend 无可靠 native tensor peak 而明确记录 `null` 和原因；
- [x] 全部 timing 关联 hardware、dtype、config 与 commit；
- [x] 计算 \(T_{reoptimized\ profile}/T_{SAEPS}=2.0483\)（paired median）；
- [x] 自动生成 Figure 6 和成本 CSV；
- [x] 不事后发明成本 PASS threshold；
- [x] 保存验收证据。

## P9 — Paper Artifacts & Final Audit

**依赖:** P0–P8 engineering 完成，P7 可为合规 `PROTOCOL_STOP`  
**状态:** `PASSED` — evidence: `docs/evidence/P9_ACCEPTANCE.md`

- [x] 自动生成 Figures 1–6；
- [x] 自动生成 Tables 1–3；
- [x] 自动生成 11 个 Supplementary artifacts；
- [x] 验证 raw→aggregate→artifact 数值一致；
- [x] 验证 seed completeness、locked hashes、failed-run reporting；
- [x] 验证 bootstrap 与 cost lineage；
- [x] 运行 `python scripts/09_build_paper_artifacts.py`，exit 0；
- [x] 运行 `python scripts/validate_repository.py`，exit 0；
- [x] 自动生成 `FINAL_VALIDATION_REPORT.md`；
- [x] 唯一结论 `PARTIALLY_SUPPORTED`；唯一建议 `INVESTIGATE_NUMERICS`；
- [x] scientific FAIL/PARTIAL 不导致 validator 工程失败；
- [x] 最终测试 30/30 通过；最终 commit 后再次验证干净工作树。

## V3 Foundation Corrections — Development Only

**状态:** `PASSED`
**隔离:** v2 `PASSED` 结果与 `configs/locked/*` 不变；v3 confirmation 未授权。

- [x] 将完整 v2 raw runs 与 paper artifacts 纳入版本控制并生成 SHA-256 snapshot；
- [x] 建立 `docs/v3/`、`configs/v3/` 与独立 seed/split policy；
- [x] 实现共同 state-profiled base checkpoint 与 base drift 指标；
- [x] 实现 unregularized 和 gamma-matched 双 nonlinear profile；
- [x] 实现 exact full-Hessian reduced reference 与正定性/solve 审计；
- [x] 实现多尺度 symmetric-curvature convergence 主 gate；
- [x] 使用真实 Burgers seed 20 完成 foundation end-to-end validation；工程 `PASSED`，exact-Hessian/profile 科学诊断失败并完整保留；
- [x] 在 commit `0b82d08` 的 fresh clone 中重建 artifacts，并通过 v2/v3 validators；重建后工作树干净；
- [x] 提交全部 raw/evidence；GitHub 推送由本任务最终发布步骤完成。

## V3.1 State Local Minimum — Development Only

**状态:** `PASSED` — engineering; seed-20 full-chain gate `FAIL`
**隔离:** 仅 seed 20 激活；21–24、30–44 均禁止运行；`confirmation_authorized: false`。

- [x] 建立 v3.1 可执行契约与独立配置；
- [x] 实现 center/profile 统一 `1e-4` objective-gradient gate；
- [x] 实现 exact state-Hessian local-minimum gate 与双向负曲率 probe；
- [x] 实现 exact-Hessian trust-region / saddle escape；
- [x] 实现 standard CG + Jacobi-PCG development gate；
- [x] 完成 seed 20 严格串行运行；在 unregularized multiscale convergence gate 合规停止；
- [x] 生成机器可读证据；seeds 21–24 不允许激活。

## V3.2 Gamma-Matched Primary — Development Only

**状态:** `PASSED` — engineering; gamma-primary chain `FAIL`
**隔离:** 仅 seed 20；21–24、30–44 均禁止；`confirmation_authorized: false`。

- [x] 建立 v3.2 gamma-primary 可执行契约与独立配置；
- [x] 实现正负独立 local-continuation branches；
- [x] 实现 nominal/strict optimization-accuracy convergence；
- [x] 将 gamma-matched profile 设为主 gate、unregularized 设为非阻断诊断；
- [x] 无条件执行 standard CG + Jacobi-PCG seed-20 gate；
- [x] 执行 exact gamma-matched Hessian reduction 与四量比较；
- [x] 运行真实 seed 20并生成证据；gamma profile 与 solver gate 失败，不可请求激活 21–24；
- [x] 自动提交并推送 GitHub private `main`。

## V3.3 Numerical Decomposition — Development Only

**状态:** `PASSED` — engineering; registered all-gates chain `FAIL`
**隔离:** 仅 seed 20；21–24、30–44 均禁止；`confirmation_authorized: false`。

- [x] 预注册 explicit → matrix-free → exact → profile 四节点契约；
- [x] 实现 explicit augmented direct GN reference；
- [x] 实现保留失败数值的 standard CG / Jacobi-PCG 诊断；
- [x] 实现 matrix-free augmented LSQR 交叉验证；
- [x] development decomposition 强制标记 `NONBINDING_DIAGNOSTIC_ONLY`；
- [x] 运行真实 seed 20 并生成机器可读验收证据；
- [x] 运行全仓库验证；
- [x] 自动提交并推送 GitHub private `main`。

## V3.4 Curvature Validation — Development Only

**状态:** `PASSED` — engineering; development generalization `NOT_ESTABLISHED`
**隔离:** protocol seed 20；仅在固定 readiness gate 通过后运行 21–24；30–44 禁止；confirmation 未授权。

- [x] 冻结 curvature / score / preconditioner 三类 solver gate；
- [x] 将 exact gamma Schur reduction 定义为 small-network local gold standard；
- [x] 实现 profile optimization-error resolution certificate；
- [x] 实现 weight-space 与 fixed-grid function-space branch audit；
- [x] 冻结 seeds 21–24 前的 v3.4 配置与 5% local-validation thresholds；
- [x] 运行 seed20 protocol verification；readiness `PASS`，配置 hash `89374e21...`；
- [x] readiness 通过后运行 seeds 21–24，不修改规则；evaluation full readiness `0/4`；
- [x] 聚合五个 development seeds 并生成验收证据；
- [x] 运行全仓库验证；41 tests 与 v2–v3.4 validators 全部通过；
- [x] 自动提交并使用本地代理推送 GitHub private `main`。

## V3.5 Second-Order Diagnostic and Engineering — Development Only

**状态:** `PASSED` — engineering; future confirmation lock candidate only
**隔离:** retrospective 20/22/23/24；engineering 25–27；held-out development 28–29；confirmation 30–44 禁止。

- [x] 预注册 residual-Hessian 三块、Shapley decomposition 与 indicator candidates；
- [x] 预注册新 development seed split 和两阶段 freeze；
- [x] 预注册未来 paired comparative estimand `D=Eraw-Esaeps`；
- [x] 运行 retrospective second-order decomposition；发现跨块抵消，尚无稳定单指标；
- [x] 在 seeds 25–27 比较并冻结：baseline→rescue center；two-pass scaled-LSQR refinement；
- [x] 在 held-out seeds 28–29 验证冻结选择；center 2/2，selected solver 2/2；
- [x] 聚合 v3.5 evidence；first-order indicator promising，paired D positive 8/8；
- [x] 全仓库验收：42 tests 与 v2–v3.5 validators 全部通过；
- [ ] 提交并代理推送 GitHub。
