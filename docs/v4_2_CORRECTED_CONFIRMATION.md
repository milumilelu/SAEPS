# v4.2 — Corrected Untouched Confirmation

**状态:** `NOT_STARTED`（依赖 v4.1 在冻结代码下通过全链稳定性）
**隔离:** 全新 confirmation seeds `55–69`；不复用 v3.6 的 30–44；不改科学规则
**目标:** 在修复后的 execution semantics 下，对 SAEPS-vs-raw 比较假设做干净的 untouched 检验

---

## 1. 进入前提（gate to start）

v4.1 必须先在**冻结代码**下证明以下全链稳定（用 held-out dev seeds `50–54`）：

- gate semantics（parameter RHS 与 score RHS 分离，score failure 不否决 curvature）；
- center availability（冻结二阶条件，不放宽 Hessian tolerance）；
- exact finite-`gamma` reduced-Hessian gold standard；
- frozen two-pass scaled-LSQR solver；
- regression test（item 4）通过且纳入 test suite commit。

任一未满足 → 不得授权 v4.2；回到 v4.1 修复，仍用新 seeds，不重跑 v3.6。

---

## 2. 科学设计（保留 v3.6 规则，不修改数学）

以下全部沿用 v3.6 冻结定义，仅换 execution code 与 seeds：

- benchmark：Burgers（scalar curvature only）；
- 15 个 untouched seeds：`55–69`；
- primary estimand：`D = E_raw - E_SAEPS`，paired 同 checkpoint；
- planned denominator：15；
- 联合主判据（四项全成立 = `SUPPORTED`）：
  - `n_valid >= 12`；
  - `n_planned_win >= 12/15`；
  - `median(D) > 0`；
  - `p_sign <= 0.05`（单侧 exact sign test）；
- secondary（全部从 valid pairs 自动聚合）：
  - `E_SAEPS` 全部值 / median / IQR / range / `E_SAEPS <= 5%` count；
  - `E_raw`；
  - planned / valid / invalid counts；
  - GN indicator confusion matrix / accuracy / Spearman / calibration error；
- 冻结项（与 v3.6 相同，**禁止在 v4.2 改动**）：center、gamma 算法、solver、gold standard、primary `D` 定义。

---

## 3. 锁要求（protocol + runner-code + semantic integration-test）

v4.2 lock record 必须包含（见 v4.1 §5）：

```text
locked_config_sha256
runner_commit
runner_file_sha256
aggregator_file_sha256
test_suite_commit
semantic_gate_graph_sha256
```

授权前 execution runner 代码冻结，不得再改。预授权需通过 preflight：
- lock config SHA256 校验；
- lock commit 校验；
- seeds 精确为 `55–69`；
- 不存在已有 v4_2 run；
- source config 与 v4.1 frozen engineering choice hash 校验；
- pytest + v4.2 lock validator 全过；
- 保存 `PRE_CONFIRMATION_AUDIT.json`。

---

## 4. 一次性执行与永久关闭

- 每个 seed 只一个正式结果；invalid seed 不补、不重跑、不删。
- 结果出来后立即生成：
  - `docs/evidence/V4_2_CONFIRMATION_REPORT.md`
  - `docs/evidence/v4_2_confirmation.json`
  - `docs/evidence/V4_2_FAILED_SEEDS.md`
  - `configs/v4_2/CONFIRMATION_RESULT_RECORD.json`
- 记录 result commit / config hash / raw manifests hash / scientific status。
- 然后 **v4.2 永久关闭**：不因为结果不好重跑 55–69。

---

## 5. 结果分支（授权后）

- `SUPPORTED` → 进入外部有效性 + 多参数 + scalability（见 `SAEPS Master Research Program v4.0.md` Phase D/E/F）。
- `NOT_SUPPORTED` → 若仍是 implementation failure，按 B−1 再开新 POST_CONFIRMATION_DEVELOPMENT 版本（新 seeds）；若是 comparative scientific failure（`D <= 0` 过多），按 B−2 处理，**不重跑 v4.2**。

---

## 6. 与 v3.6 的关系

v3.6 的 `NOT_SUPPORTED` 保持永久有效、不可改写。v4.2 是独立的新确认队列，其结果**不修正** v3.6；两者在报告中分别陈述（v3.6 = implementation failure / hypothesis not tested；v4.2 = corrected confirmation result）。
