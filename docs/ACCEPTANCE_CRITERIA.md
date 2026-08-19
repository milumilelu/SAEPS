# ACCEPTANCE_CRITERIA.md — SAEPS v2.0

> 详细执行接口以 `docs/EXECUTION_CONTRACT.md` 为准。本文件给出可自动判定的阶段验收标准。

## 1. 通用验收规则

- 阶段必须按 P0→P9 推进；前序 engineering gate 未通过不得继续；
- scientific failure 是有效结果，不等于 engineering failure；
- P7 可因 P5 NOT_SUPPORTED 合规记录 `PROTOCOL_STOP`；
- 验收必须使用实际数值或端到端流程，mock 仅限小范围单元测试；
- 所有预注册 run 必须有 `PASS`、`CHECKPOINT_INVALID`、`PROFILE_FAILURE`、`SOLVER_FAILURE` 或 `NUMERICAL_FAILURE`；
- failed/invalid runs 不删除，报告 planned/valid/invalid/failed denominator；
- confirmation 只读取 hash 匹配的 locked configs；
- 所有 paper-facing 数值从 raw machine-readable outputs 自动生成。

## 2. P0 — Repository

必须存在 Python package、README、pyproject、CI、seed/config/logging/provenance infrastructure 和基础目录。必须实际成功：

```bash
pytest -q
python scripts/00_smoke_test.py
```

Smoke test 必须 train tiny PINN、save、reload、recompute residual，并在预注册 tolerance 内与保存前一致。记录 Python/package versions、hardware、dtype、timestamp、config hash、git commit。

**PASS:** 两命令退出码 0、产物可重载、provenance 完整。

## 3. P1 — Numerical Core

使用实际 tiny network 和双精度数值：

1. 至少 10 个随机 \(y\)：
   \[
   \|A_{MF}y-A_{explicit}y\|/(\|A_{explicit}y\|+\epsilon)<10^{-6};
   \]
2. \(\|F^{se}_{MF}-F^{se}_{explicit}\|_F/(\|F^{se}_{explicit}\|_F+\epsilon)<10^{-6}\)；
3. symmetry relative error \(<10^{-8}\)；
4. \(\lambda_{min}(F^{se})\ge-10^{-8}\lambda_{max}(F^{se})\)；
5. \(F^{raw}-F^{se}\succeq0\) 至 numerical tolerance；
6. 每个正式 CG relative residual \(\le10^{-8}\)；
7. scalar \(-10^{-8}\le\eta^{se}\le1+10^{-8}\)；
8. finite-difference/autodiff derivative comparison 通过锁定 tolerance；
9. 相同 config+seed 重复运行通过锁定 tolerance。

**PASS:** 全部成立；否则禁止开始科学实验。

## 4. P2 — Controlled Geometry

### Engineering

- development seeds 精确为 `[0,1,2]`；
- confirmation seeds 精确为 `[10,11,12,13,14,15,16,17,18,19]`；
- \(q_\parallel,q_\perp\) 只用 development overlap 选择并锁定；
- 10 seeds × 5 alpha = 50 evaluations 全部有最终状态；
- all seed values、median、IQR、monotonicity 和 Figure 2 自动生成；
- 无隐藏排除。

### Scientific SG-1

\[
median_i\rho_{Spearman}(\alpha,\eta_i^{se})\ge0.9,
\]

且至少 8/10 seeds 满足 LOCK 前定义的正确单调趋势。满足记 PASS，否则 FAIL；FAIL 后禁止重选 source。

## 5. P3 — Profile Engine

- 实现 frozen/reoptimized/quadratic fit/curvature/minimum/comparison API；
- 每点相同 \(\theta_0\)，禁止 previous-point continuation；
- stopping 同时检查 optimizer termination、loss plateau、normalized theta-gradient；
- known-curvature synthetic test 通过；
- point-order invariance 和 independent initialization reproducibility 通过；
- failed point 明确标记，missing point 不插值；
- fit-quality rule 在 confirmation 前锁定。

**PASS:** 全部成立。

## 6. P4 — Screening & LOCK

- 候选仅 Allen-Cahn、Burgers；development seeds 仅 `[0,1,2]`；
- 只按 numerical feasibility、classical minimum、stationarity count、SAEPS numerics 筛选；
- 禁止按 eta、SAEPS 优势、图形或 regime 选择；
- 未入选数据保留；
- `configs/locked/scalar.yaml` 存在；
- `docs/LOCKED_PROTOCOL.md` 记录 SHA256、git commit、date、reason；
- architecture、sensor、weights、optimizer/stopping、thresholds、profile、gamma、bootstrap、robustness seeds 和 artifact code 均锁定。

**PASS:** hash 可验证且 LOCK 后配置不可变。

## 7. Checkpoint/Profile Gate

正式 checkpoint 报告 \(S_\theta,S_\lambda\)、PDE/observation/BC/IC residual；synthetic state error 和 validation parameter error 标记 validation-only。阈值来自 locked protocol。

Reoptimization point 必须通过 locked optimizer termination、loss plateau、theta-gradient 和 fit-quality rules。失败分别标记 `CHECKPOINT_INVALID` 或 `PROFILE_FAILURE`，不得静默纳入有效聚合。

## 8. P5 — Scalar Confirmation

### Engineering

- 10/10 seeds 有最终状态；
- 每 seed 完成 training、stationarity、SAEPS、frozen/reoptimized/classical profiles、fit、comparison；
- 完整保存 \(Fraw,Fse,Hprofile,Eraw,Esaeps,D_i,\eta^{se},\eta_{profile}\)；
- 报告 scatter、correlation、absolute error 和 per-seed values；
- paired bootstrap 以 seed-level \(D_i\) 为单位，并使用 locked CI method/resample count/RNG；
- Figures 3–4、Table 2 自动生成；
- denominator 完整，不得把 9/10 改成 9/N。

### Scientific SG-2

- `STRONGLY_SUPPORTED`: 至少 9/10 valid paired wins，\(median(D)>0\)，bootstrap 95% CI lower \(>0\)；
- `SUPPORTED_WITH_UNCERTAINTY`: 9/10 与 median positive，但 CI 跨 0；
- `PARTIALLY_SUPPORTED`: 轻微或不稳定优势；
- `NOT_SUPPORTED`: \(median(D)\le0\) 或 profiles 系统性反驳 SAEPS。

P5 NOT_SUPPORTED 触发 P7 `PROTOCOL_STOP`，禁止换 PDE 重跑。

Independent classical profile 必须报告 minimum、curvature、truth；若其本身平坦，不得把弱信号仅解释为 PINN absorption。

## 9. P6 — Multi-parameter Confirmation

### Engineering

- CRD joint target \((\log a,\log b)\)，10/10 seeds 有最终状态；
- 输出 full \(Fraw,Fse\)、eigensystem、condition number、trace、meaningful determinant、coupling；
- 每 seed 沿 \(v_{max},v_{min}\) 有 independent nonlinear profiles；
- 报告 directional curvature ratio error；
- representative seed 自动为升序第一个 valid seed；
- 该 seed 的 \(5\times5\) grid、Figure 5、Table 3 可重建。

### Scientific SG-3

至少 9/10 valid confirmation seeds 满足：

\[
H_{prof}(v_{max})>H_{prof}(v_{min}),
\]

与 SAEPS ordering 一致。否则 FAIL；不得制造 coupling 或挑 representative seed。

## 10. P7 — Robustness & Architecture

若 P5 NOT_SUPPORTED：正确记录 `PROTOCOL_STOP` 即满足执行协议。

否则：

- scalar 运行 \(3\times3=9\) noise × observation-fraction conditions；
- 每 condition 5 个锁定 seeds，最大 45 runs；
- nominal architecture 10 seeds，narrow 5，wide 5；
- 所有 runs 有最终状态；
- 报告 effect、stationarity、SAEPS/raw trend 和 failure boundary。

不设强阳性门槛，不得用失败 robustness 修改方法。

## 11. P8 — Computational Cost

记录并聚合 training、SAEPS、frozen profile、reoptimized profile time、CG iterations、JVP/VJP counts；可可靠获得时记录 peak memory。全部关联 hardware、dtype、config、commit。

必须报告：

\[
T_{reoptimized\ profile}/T_{SAEPS}.
\]

**PASS:** 口径可审计，成本 artifact 可重建。无预注册数值阈值，因此成本结论为描述性，不得事后发明 PASS 线。

## 12. Gamma

\[
\gamma_\alpha\in\{10^{-12},10^{-10},10^{-8},10^{-6},10^{-4},10^{-2}\}.
\]

完整 sweep 必须报告。Nominal 值仅由 locked algorithm 根据 CG stability、plateau、adjacent-scale change 选择，禁止人工查看 confirmation 结果后选择。

## 13. P9 — Final Audit

必须实际成功：

```bash
python scripts/09_build_paper_artifacts.py
python scripts/validate_repository.py
```

自动检查 tests、seed completeness、locked hashes/config mutation、raw/aggregate equality、Figures 1–6、Tables 1–3、failed runs、scientific gates、bootstrap、cost 和 provenance。

Validator exit code：`0 = protocol complete`；`1 = engineering incomplete`。Scientific FAIL 或合规 P7 protocol stop 不得返回 1。

## 14. Final Report

`FINAL_VALIDATION_REPORT.md` 包含 P0–P9 gates、confirmation completeness、scientific results、bootstrap、failed runs、deviations、cost、conclusion、recommendation。

结论只能为 `SUPPORTED`、`PARTIALLY_SUPPORTED`、`NOT_SUPPORTED`。建议只能为 `PROCEED_TO_PAPER`、`PROCEED_WITH_LIMITED_CLAIMS`、`REVISE_METHOD`、`INVESTIGATE_NUMERICS`、`STOP`。

## 15. 最终完成

P0–P9 mandatory engineering 完成，P7 可为授权 protocol stop；全部 runs 有合法状态；配置和结果可追溯；artifact 与 validator 通过；最终报告生成；工作树干净且阶段 commits/最终 commit 可追溯。阴性科学结论不构成执行失败。

