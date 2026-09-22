# 后续补强实验执行细则

## 0. 总则

本细则用于 SAEPS 论文的 development-only 补强，不修改 `configs/locked/`、历史 confirmation 数据或既有科学判据。所有新结果写入独立 namespace：

```text
outputs/posthoc/paper_strengthening/followup_v1/
configs/paper_strengthening/followup_*.yaml
```

所有 replicate 必须保留最终状态和失败原因。不得根据结果删除高偏差、非收敛或不利 replicate。每个实验必须记录 config hash、git commit、seed、dtype、硬件、训练预算、stationarity、曲率、区间和运行时间。

最终结果必须区分：

- `PASS`：拟合、曲率和区间均可计算；
- `SOLVER_FAILURE`：优化器未产生可用拟合；
- `CHECKPOINT_INVALID`：状态梯度或 Hessian 条件不满足预先规定的有效性；
- `NUMERICAL_FAILURE`：Jacobian、Hessian、PSD 或线性代数失败；
- `SCIENTIFIC_FAILURE`：流程正确但 coverage 或 profile gate 未达到目标。

## 1. 实验 A：高偏差 refit 的 bootstrap bias correction

### 1.1 目标

判断 SAEPS 的剩余漏覆盖是否主要由高偏差 refit 的估计中心偏移造成，并测试 bootstrap bias correction 是否能在不使用 synthetic truth 的情况下改善 coverage。

### 1.2 样本选择规则

使用已完成的 MC100 cohort 作为筛选框架，但不得根据真实参数值事后删除数据。按预先锁定的 development 规则选择：

```text
high-bias candidate: |kappa_hat - kappa_truth| > 0.05
```

MC100 中所有满足规则的 replicate 都必须纳入；另从低/中偏差组各抽取相同数量的对照 replicate。最终目标为 20 个 outer refit（高偏差 10 个、对照 10 个）。

### 1.3 Bootstrap 配置

每个 outer refit：

- 固定 fitted network、fitted parameter 和 collocation/data locations；
- 从 fitted observation model 生成 `B=100` 个 parametric bootstrap data sets；
- 每个 bootstrap data set 重新执行 joint Adam + L-BFGS + fixed-parameter state polish；
- 不改变 network、loss weights、gamma、profile 区间或 stopping rule；
- bootstrap initialization 使用预先固定的 deterministic seed stream；
- 记录每个 bootstrap replicate 的 parameter estimate、state gradient、objective、failure state。

### 1.4 Bias estimate 与区间

对每个 outer refit 计算：

\[
\widehat b_{boot}=B^{-1}\sum_b\hat\kappa_b-\hat\kappa_{obs}.
\]

使用两种区间并列报告：

1. bias-corrected Wald：\(\hat\kappa_{obs}-\widehat b_{boot}\) 加上 SAEPS/raw 的 sandwich half-width；
2. bootstrap percentile 或 BCa interval，前提是 bootstrap 有效 replicate 数不少于 80/100。

不允许使用真实参数计算可部署 bias estimate。真实参数只可用于 development audit，对照报告必须明确标记为 oracle analysis。

### 1.5 验收指标

- 每个 outer refit 至少 80/100 个 bootstrap replicate 有效；
- 报告 bias estimate、bootstrap standard deviation、skewness、failure rate；
- 报告 correction 前后 coverage、区间宽度和参数偏差；
- 若高偏差组 coverage 提高而对照组不恶化超过 5 个百分点，记为 `PARTIALLY_SUPPORTED`；
- 若 bootstrap failure rate 高于 20%，记为 `NUMERICAL_FAILURE`，不得把失败 bootstrap 当作 coverage 证据；
- 若 correction 对 coverage 没有改善，记录 `SCIENTIFIC_FAILURE`，保留原始 SAEPS 结果。

### 1.6 预期产物

```text
followup_v1/bootstrap_bias_correction/
  bootstrap_manifest.jsonl
  outer_refit_summary.json
  bootstrap_coverage_table.csv
  BOOTSTRAP_BIAS_CORRECTION_REPORT.md
```

## 2. 实验 B：Burgers 或 Allen–Cahn 跨问题 Monte Carlo

### 2.1 目标

检验“固定状态曲率欠覆盖 + 参数偏差分层”是否只存在于 E3 饱和反应扩散，还是在另一类 scalar inverse PDE 中也出现。

### 2.2 benchmark 选择

优先选择已有 exact-block 和 curvature 输出最完整的 Allen–Cahn；若其 forward solver 或 observation interface 不满足相同噪声定义，则选择 Burgers。选择在运行前写入配置，不得由 coverage 结果反向决定。

### 2.3 固定设计

- development pilot：30 个 data seeds；
- 若 engineering gate 通过，再扩展到 100 个 data seeds；
- nominal level：95%；
- 固定 observation noise level，并记录 noise standard deviation；
- 固定 network architecture、collocation layout、loss weights 和 optimizer；
- 每个 replicate 同时计算 raw、SAEPS、parameter-block；
- 使用与 E3 相同的 joint sandwich construction；
- 记录完整 denominator 和所有失败状态。

### 2.4 跨问题 gate

进入 100-replicate 扩展前必须满足：

- 至少 25/30 replicate 完成可用 refit；
- raw 与 SAEPS 的 Jacobian 实现无 numerical mismatch；
- noise stream、truth parameter 和 data point layout 可复现；
- 至少一个 benchmark checkpoint 的 state Hessian 能完成 PSD/conditioning audit。

科学结果按以下方式报告：

- 不要求第二个 PDE 达到 E3 的相同 coverage 数值；
- 若 raw 欠覆盖而 SAEPS 改善，支持跨问题一致性；
- 若方向相反或改善消失，报告为边界条件或问题依赖性，不得选择性删除。

## 3. 实验 C：compact network direct profile likelihood

### 3.1 目标

提供不依赖 gamma 的独立曲率参照，直接计算 state-reoptimized profile objective，检验 SAEPS 是否确实接近有限位移局部 profile，而不仅是接近同一局部 Hessian 近似。

### 3.2 compact setup

- architecture：优先 `[2, 4, 1]` 或 `[2, 8, 1]`；
- benchmark：先用 E3，确保与 MC100 使用同一 truth、noise 和 data layout；
- outer data seeds：10 个 development seeds；
- profile offsets：预先固定 symmetric grid，例如 `[-0.05,-0.03,-0.02,-0.01,0.01,0.02,0.03,0.05]` in log-parameter coordinate；
- 每个 offset 固定 parameter，重新优化 state；
- 至少两个 independent state starts；
- 每个 point 记录 objective、state gradient、Hessian definiteness、iterations 和 stop reason。

### 3.3 profile curvature

使用 symmetric quadratic fit 和 direct finite-difference curvature 两种计算：

\[
H_{profile}^{FD} \approx [Q(h)+Q(-h)-2Q(0)]/h^2.
\]

profile point 只有在 state stationarity 达到预设阈值且 objective non-increase 保护通过时才进入 fit；失败 point 必须保留并计入 profile denominator。

### 3.4 验收指标

- 至少 8/10 outer seeds 有完整 profile point set；
- 每个通过 seed 至少 6 个 symmetric offsets 有效；
- direct profile curvature 与 exact reduced Hessian 的相对误差、SAEPS 误差和 raw 误差并列报告；
- 不把 direct profile failure 解释为 SAEPS failure，先分类为 solver、numerical 或 scientific failure；
- 如果 SAEPS 与 direct profile 同向而 raw 系统偏离，支持“曲率修正是几何现象”的解释；
- 如果 SAEPS 仍不能接近 direct profile，降低曲率校正主张并记录 profile nonlinearity。

## 4. 实验 D：parameter-block PSD、方差和 coverage 审计

### 4.1 PSD 审计

对每个 MC100 和跨问题 replicate 记录：

- exact parameter block 最小特征值；
- state block 最小特征值和 condition number；
- Schur complement 最小特征值；
- 对称化前后相对差异；
- gamma regularization magnitude。

PSD 分类规则：

- 非对称误差超过 `1e-8`：`NUMERICAL_FAILURE`；
- state block 非正定：不得把 parameter-block 标成有效 correction；
- parameter block 与 raw 比值接近 1 且 PSD 通过：记录为 structural no-effect，而非 numerical failure。

### 4.2 方差审计

分别报告：

1. model-based \(F^{-1}\)；
2. joint sandwich \(A^{-1}BA^{-1}\)；
3. bootstrap empirical variance；
4. 区间半宽和参数估计偏差。

若 sandwich 与 bootstrap variance 相差超过 2 倍，标记为 variance-model mismatch；不得用其中较宽者选择性报告。

### 4.3 Coverage 审计

parameter-block 必须与 raw 使用同一 noise stream、同一 variance construction 和同一 nominal level。报告：

- overall coverage；
- bias-stratified coverage；
- interval width；
- valid denominator；
- PSD/conditioning failure denominator。

若 parameter-block/raw 曲率比值中位数位于 `[0.95, 1.05]`，且 coverage 与 raw 相同，则结论写为：

> The parameter-block correction is a valid negative control but does not remove state-adaptation curvature.

## 5. 执行顺序与停止规则

严格按以下顺序：

```text
A1 bootstrap engineering dry-run (1 outer × 10 bootstrap)
 -> A2 bootstrap high-bias cohort (20 outer × 100 bootstrap)
 -> B1 second-PDE engineering pilot (30 replicates)
 -> C1 compact direct-profile dry-run (2 seeds)
 -> C2 compact direct-profile cohort (10 seeds)
 -> D1 consolidated PSD/variance/coverage audit
```

停止规则：

- A1 失败：先修复 bootstrap data injection，不得启动 A2；
- B1 有效 refit 少于 25/30：停止扩展，记录 benchmark/solver failure；
- C1 任一 seed 无法形成两个 symmetric profile points：先修复 profile engine；
- D1 发现 locked 配置需要修改：停止所有 confirmation 相关工作，写入 `docs/ISSUES.md`；
- 任一科学 gate 失败：保留结果并降级主张，不通过调参迫使其通过。

## 6. 最终汇总输出

四项实验完成后生成：

```text
docs/paper_strengthening/FOLLOWUP_EXPERIMENT_FINAL_REPORT.md
outputs/posthoc/paper_strengthening/followup_v1/final_summary.json
```

最终报告必须回答四个问题：

1. bias correction 是否改善高偏差 refit 的 coverage；
2. 两来源分解是否跨 PDE 重现；
3. SAEPS 是否接近独立 direct profile curvature；
4. parameter-block coverage 失败究竟来自 PSD、方差还是 structural no-effect。

在四个问题均有机器可读证据前，不得把路线 A 写成已完成的通用 coverage calibration 方法。
