# TASKS.md — SAEPS v2.0

> 最高执行协议：`docs/EXECUTION_CONTRACT.md`（`SAEPS-JCP-EXEC-v2.0`）。

## 状态规则

阶段状态：`NOT_STARTED`、`IN_PROGRESS`、`BLOCKED`、`PASSED`、`FAILED`。任一时刻最多一个阶段为 `IN_PROGRESS`；前一阶段 engineering gate 未 `PASSED`，不得进入下一阶段。P7 可按契约记录 `PASSED / completion_mode: PROTOCOL_STOP`。

## 总览

| Phase | 名称 | 状态 | Engineering gate | Scientific result |
|---|---|---|---|---|
| P0 | Repository Bootstrap | PASSED | PASSED | N/A |
| P1 | SAEPS Core Verification | NOT_STARTED | NOT_RUN | N/A |
| P2 | Controlled Tangent Geometry | NOT_STARTED | NOT_RUN | NOT_RUN |
| P3 | Nonlinear Profile Engine | NOT_STARTED | NOT_RUN | N/A |
| P4 | Scalar PDE Screening & LOCK | NOT_STARTED | NOT_RUN | N/A |
| P5 | Scalar Confirmation | NOT_STARTED | NOT_RUN | NOT_RUN |
| P6 | Multi-parameter Confirmation | NOT_STARTED | NOT_RUN | NOT_RUN |
| P7 | Robustness & Architecture | NOT_STARTED | NOT_RUN | DESCRIPTIVE |
| P8 | Computational Cost | NOT_STARTED | NOT_RUN | DESCRIPTIVE |
| P9 | Final Audit | NOT_STARTED | NOT_RUN | NOT_RUN |

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
**状态:** `NOT_STARTED`

- [ ] 实现 residual-first API 和 parameter coordinate transform；
- [ ] 实现 explicit \(J_\theta,J_\lambda\)、JVP、VJP；
- [ ] 实现 SVD exact reference、explicit Tikhonov、matrix-free CG/Krylov；
- [ ] 实现唯一共享的 `Fraw/Fse/gse/eta`；
- [ ] 至少 10 个随机 \(y\) 验证 operator relative error `<1e-6`；
- [ ] 验证 curvature relative error `<1e-6`；
- [ ] 验证 symmetry `<1e-8`；
- [ ] 验证 PSD、Loewner relation、scalar eta bound；
- [ ] 验证每个正式 CG relative residual `<=1e-8`；
- [ ] 验证 finite-difference/autodiff derivatives；
- [ ] 验证相同 config+seed 重复运行一致性；
- [ ] 保存真实数值测试证据并提交 P1 commit。

## P2 — Controlled Tangent Geometry

**依赖:** P1 `PASSED`  
**状态:** `NOT_STARTED`

### Development

- [ ] 仅用 seeds `[0,1,2]` 建立 manufactured parabolic PDE；
- [ ] 固定 \(D,c,\lambda^*,u^*\) 和 Fourier library；
- [ ] 实现 tangent overlap \(\omega(q)\)；
- [ ] 选择、归一化并锁定 \(q_\parallel,q_\perp\)；
- [ ] 记录 development evidence、配置 hash 和 decision。

### Confirmation

- [ ] 使用 `[10,11,12,13,14,15,16,17,18,19]`；
- [ ] 每 seed 运行 5 个 \(\alpha\)，共 50 evaluations；
- [ ] 每个 run 有合法最终状态；
- [ ] 报告 all seed values、每 seed Spearman、median、IQR 和 monotonicity；
- [ ] 自动生成 Figure 2；
- [ ] 计算 SG-1：median Spearman `>=0.9` 且至少 `8/10` 单调；
- [ ] 保存验收证据并提交 P2 commit。

## P3 — Nonlinear State-Reoptimization Engine

**依赖:** P2 engineering `PASSED`  
**状态:** `NOT_STARTED`

- [ ] 实现 `profile_frozen()`、`profile_reoptimized()`；
- [ ] 实现 `fit_local_quadratic()`、`estimate_curvature()`；
- [ ] 实现 `estimate_profile_minimum()`、`compare_curvature()`；
- [ ] 每点从同一 \(\theta_0\) 初始化，禁止 previous-point continuation；
- [ ] stopping rule 同时包含 optimizer termination、loss plateau、normalized theta-gradient；
- [ ] 实现 synthetic known-curvature test；
- [ ] 验证 point-order invariance 与 independent initialization reproducibility；
- [ ] failed point 明确标记，禁止静默插值；
- [ ] 锁定 fit quality 与 profile failure rules；
- [ ] 保存验收证据并提交 P3 commit。

## P4 — Scalar PDE Screening & LOCK

**依赖:** P3 `PASSED`  
**状态:** `NOT_STARTED`

- [ ] 仅用 seeds `[0,1,2]` 筛选 `Allen-Cahn` 与 `Burgers`；
- [ ] 运行 forward/PINN/profile feasibility；
- [ ] 验证 conventional profile 的明确局部 minimum；
- [ ] 统计 joint stationarity passing count；
- [ ] 验证 CG/Jacobian stability；
- [ ] 按预注册顺序选择，禁止依据 eta/优势/图形；
- [ ] 未入选结果保留用于 Supplementary；
- [ ] 创建 `configs/locked/scalar.yaml`；
- [ ] 锁定 architecture、sensors、weights、optimizer/stopping、thresholds；
- [ ] 锁定 profile interval/fit、gamma algorithm、bootstrap、robustness seeds；
- [ ] 更新 `docs/DECISIONS.md`；
- [ ] 生成 `docs/LOCKED_PROTOCOL.md` 的 SHA256、commit、date、reason；
- [ ] 提交 LOCK commit。

## P5 — Scalar Confirmation

**依赖:** LOCK `PASSED`  
**状态:** `NOT_STARTED`

- [ ] 运行全部 10 个 confirmation seeds；
- [ ] 每 seed 执行 training、stationarity、SAEPS；
- [ ] 执行 frozen、independent reoptimized、classical profiles；
- [ ] 执行 curvature fitting 与 fit-quality gate；
- [ ] 计算 \(Fraw,Fse,Hprofile,Eraw,Esaeps,D_i\)；
- [ ] 计算 \(\eta^{se}\) 与 \(\eta_{profile}\) 的 scatter/correlation/error；
- [ ] 计算 paired wins、median(D)、locked bootstrap 95% CI；
- [ ] 报告 planned/valid/invalid/failed denominator；
- [ ] 自动生成 Figures 3–4 和 Table 2；
- [ ] 分类 SG-2：STRONGLY / WITH_UNCERTAINTY / PARTIAL / NOT；
- [ ] 若 NOT_SUPPORTED，登记 P7 `PROTOCOL_STOP`；
- [ ] 保存验收证据并提交 P5 commit。

## P6 — Multi-parameter Confirmation

**依赖:** P5 engineering `PASSED`  
**状态:** `NOT_STARTED`

- [ ] 使用 CRD joint target \((\log a,\log b)\)；
- [ ] 运行全部 10 个 confirmation seeds；
- [ ] 计算 full \(Fraw,Fse\)，禁止逐坐标标签；
- [ ] 输出 eigenvalues/eigenvectors、condition number、trace、determinant、coupling；
- [ ] 每 seed 沿 \(v_{max},v_{min}\) 运行 nonlinear profiles；
- [ ] 计算 directional curvature ratio error；
- [ ] 按升序自动选择 first valid seed，运行 \(5\times5\) 2D grid；
- [ ] 自动生成 Figure 5 和 Table 3；
- [ ] 计算 SG-3：至少 9/10 valid seeds ordering 一致；
- [ ] 保存验收证据并提交 P6 commit。

## P7 — Robustness & Architecture Transfer

**依赖:** P5/P6 engineering 完成  
**状态:** `NOT_STARTED`

- [ ] 若 P5 NOT_SUPPORTED，记录 `completion_mode: PROTOCOL_STOP` 并停止大规模 runs；
- [ ] 否则执行 scalar 的 3 noise × 3 observation fractions；
- [ ] 9 conditions 每个使用 5 个预注册 seeds，最多 45 runs；
- [ ] nominal architecture 使用核心 10 seeds；
- [ ] narrow 与 wide 各使用 5 个锁定 seeds；
- [ ] 报告 effect、stationarity、SAEPS/raw 趋势和失效条件；
- [ ] 不设置强阳性 scientific gate；
- [ ] 保存失败并提交 P7 commit。

## P8 — Computational Cost

**依赖:** 核心 confirmation 完成  
**状态:** `NOT_STARTED`

- [ ] 聚合 training、SAEPS、frozen profile、reoptimized profile times；
- [ ] 聚合 CG iterations、JVP/VJP counts；
- [ ] 能可靠取得时报告 peak memory；
- [ ] 全部 timing 关联 hardware、dtype、config 与 commit；
- [ ] 计算 \(T_{reoptimized\ profile}/T_{SAEPS}\)；
- [ ] 自动生成 Figure 6 或等价成本表；
- [ ] 不事后发明成本 PASS threshold；
- [ ] 保存验收证据并提交 P8 commit。

## P9 — Paper Artifacts & Final Audit

**依赖:** P0–P8 engineering 完成，P7 可为合规 `PROTOCOL_STOP`  
**状态:** `NOT_STARTED`

- [ ] 自动生成 Figures 1–6；
- [ ] 自动生成 Tables 1–3；
- [ ] 自动生成全部 Supplementary artifacts；
- [ ] 验证 raw→aggregate→artifact 数值一致；
- [ ] 验证 seed completeness、locked hashes、failed-run reporting；
- [ ] 验证 bootstrap 与 cost lineage；
- [ ] 运行 `python scripts/09_build_paper_artifacts.py`；
- [ ] 运行 `python scripts/validate_repository.py`；
- [ ] 自动生成 `FINAL_VALIDATION_REPORT.md`；
- [ ] 给出唯一 scientific conclusion 与 recommendation；
- [ ] 确认 scientific FAIL / P7 protocol stop 不导致 validator 失败；
- [ ] 运行最终测试，确认工作树干净并提交最终 commit。
