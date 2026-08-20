# v4.1 — POST_CONFIRMATION_DEVELOPMENT (Execution-Semantic Repair)

**状态:** `NOT_STARTED`（待建）
**隔离:** 全新 seeds；不读取 v3.6 选择科学阈值；不重跑 30–44；不生成 "corrected v3.6"
**触发分支:** v3.6 = `NOT_SUPPORTED` → **B−1 implementation / numerical-availability failure**
**目标:** 修复 confirmation execution semantics，**不改变 SAEPS 科学方法**

---

## 1. 形式锁定结论（不可更改）

- 科学状态：`NOT_SUPPORTED` —— 预注册四项 primary conditions 全部不成立（0/15 valid pair）。
- 科学解释（必须同时写明）：**the SAEPS-versus-raw comparative hypothesis was not tested in v3.6.**
- v3.6 已永久关闭；raw manifest 已固化（hash `3c7061a9...`）；rerun / 改 raw / corrected v3.6 aggregation 均禁止。

> 不能写 "v3.6 confirms SAEPS fails." 正确写法是：formal `NOT_SUPPORTED` because no valid primary pairs were produced; a post-run audit identified a scope-violating implementation defect that bound an excluded score RHS into the curvature gate.

---

## 2. 根因（代码级，已对照真实代码验证）

- `src/saeps/v33/pipeline.py::_direct_augmented_reference`（第 59–61 行）同时构造两类 RHS：
  `right_hand_sides = cat([J_lambda, residual])`，即参数曲率 RHS 与被排除的 score/residual RHS 拼成两列。
- 第 78–80 行 `relative_normal` 是按 RHS 列分别计算的向量；第 91 行 `max_normal = torch.max(relative_normal)` 取**所有 RHS 中的最大值**。
- 第 92–98 行 `explicit["status"] = PASS` 要求 `max_normal <= 1e-10` 且 identity error 达标 —— 因此**被排除的 score RHS 是否超 1e-10 被纳入了统一 status**。
- `src/saeps/v36/pipeline.py`（第 259–265 行）`solver_pass = (explicit["status"] == "PASS" and ...)` 把这个含 score RHS 的统一 status **直接绑回 curvature solver gate**。
- v3.6 锁定的却是 `scalar curvature only`，confirmation runner 却用统一 status 否决 curvature confirmation。

**对照先例（证明这是回归，不是新数学问题）：**
`src/saeps/v34/validation.py` 第 111–114 行把 `CURVATURE_SOLVER_GATE`（parameter RHS）与 `SCORE_SOLVER_GATE`（binding=False）**分列为两个独立 gate**，并断言 score gate 应为 `SOLVER_FAILURE` 且被保留（非绑定）。v3.6 复用了 v3.3 的合并实现，丢失了这一分离。

---

## 3. Postmortem 工程发现（来自现有 raw audit，不可重算为 v3.6 结果）

对 15 条 v3.6 raw records 的实测（见 `outputs/runs/v3_6_scalar_confirmation/records/seed_*.json`）：

- center availability = **14/15**（仅 seed 37 `CHECKPOINT_INVALID`）。
- 14/14 center-valid seeds：parameter explicit reference **PASS**（param RHS ≈ 1e-13–1e-14）。
- 14/14：selected two-pass scaled-LSQR curvature solve **PASS**（verified residual ≈ 1e-15–1e-11）。
- 14/14：selected `F_se` 与 explicit reference 的 relative difference ≈ 1e-15–1e-14。
- 唯一超 1e-10 的是被排除的 score RHS（≈ 3.1e-10–1.3e-9）。

> **结论：v3.5 选出的 curvature solver 在 14/14 center-valid confirmation seeds 上实际工作良好。**
> 这不能被重新算作 v3.6 scientific result，但是一个高价值的 postmortem engineering finding，且说明**当前完全没有理由继续调 center 或 solver**。

seed 37 是真正的 center failure（未找到满足冻结二阶条件的 common center，`selected_method=null`），与 development 阶段的偶发 center failure 一致 —— 以后仍保留 "invalid planned seeds count as planned non-wins" 规则，不为 seed 37 放宽 Hessian tolerance。

---

## 4. 修复任务（写入 Codex 大任务的 7 项）

1. **永久保护 v3.6。** 不读取它选择新的 scientific threshold；不重跑 30–44；不生成 "corrected v3.6"。
2. **修复 gate dependency。** 新建明确的 `explicit_curvature_reference`，只接受 `J_lambda` RHS；score/residual RHS 必须是独立 diagnostic，任何 score failure 不得进入 curvature validity。
3. **禁止复用含混的统一 `status`。** 每个 numerical object 有独立状态（如 `parameter_reference_status`、`curvature_solver_status`、`score_solver_status`）；primary aggregator 只读取协议声明的 binding nodes。
4. **加入专门 regression test。** 人工构造 `parameter RHS PASS` + `score RHS FAIL`，必须断言 `CURVATURE_GATE = PASS`。此测试专门防止本次 bug 复现。
5. **改为 fail-soft / record-all-computable。** 即使后续某 gate FAIL，也保存此前已合法算出的 `F_raw`、explicit `F_se`、exact Hessian、solver diagnostics 等，仅标记 `binding_valid=false`，避免 postmortem 因早退丢失科学量。
6. **不改 center、`gamma`、solver、gold standard 和 primary `D` 定义。** 当前 read-only evidence 已显示 center 14/15、curvature solver 在 14/14 center-valid seeds 上满足 curvature-specific 阈值。
7. **种子与冻结节奏：**
   - 全新 development seeds `45–49` 做 engineering integration；
   - 冻结 code + config + tests 后，用 `50–54` 做 held-out development；
   - 若 50–54 在**冻结代码**下证明 gate semantics / center / exact gold / solver 全链稳定，再创建全新 confirmation `55–69`（15 个 untouched seeds），保留原 paired `D`、planned denominator、12/15 等科学规则，不再修改。

---

## 5. 锁升级要求（未来 confirmation lock 必须多锁一项）

未来 lock record 至少应包含：

```text
locked_config_sha256
runner_commit
runner_file_sha256
aggregator_file_sha256
test_suite_commit
semantic_gate_graph_sha256
```

授权 confirmation 之前，execution runner **不得再发生任何代码修改**。最理想流程：

```text
implement → test on development → held-out development → freeze config + executable code → authorize confirmation
```

这补上 v3.6 暴露的最后一个 reproducibility 漏洞：当时冻结的是 scientific config，但 one-shot execution pipeline 在后续 commit 才实现，未同时冻结 **executable implementation**，static config validator 看不出 "YAML 写 curvature-only，Python 偷偷绑定 score gate"。

---

## 6. 科学状态重归类（论文/报告用语）

- 不能写："v3.6 confirms SAEPS fails."
- 必须写："The preregistered v3.6 confirmation was formally `NOT_SUPPORTED` because no valid primary pairs were produced; a post-run audit identified a scope-violating implementation defect that bound an excluded score RHS into the curvature gate. Therefore, the SAEPS-versus-raw comparative hypothesis was not tested in v3.6."
- 可写（engineering audit finding，由 raw audit 直接支持）："On all 14 center-valid runs, the curvature-specific parameter reference and the frozen two-pass scaled-LSQR solver satisfied their intended curvature criteria."

---

## 7. 范围边界

本项目**没有回到原点**：0/15 valid 已被 postmortem 缩窄为 "confirmation runner 错把 score-RHS status 绑定到 curvature gate"，而非 center 大面积失败 / curvature solver 失败 / exact Hessian 链失败。因此：

- 不应重新设计 SAEPS；
- 不应重做 v3.0–v3.5 研究；
- 应做极克制的 **execution-semantic repair → fresh development → new untouched confirmation**；
- 只有新的 corrected confirmation 真正得到 `D_i` 后，才决定是否进入：second scalar PDE replication、two-parameter generalized eigengeometry、directional-HVP adequacy indicator、scalability、noise/sparsity robustness。
