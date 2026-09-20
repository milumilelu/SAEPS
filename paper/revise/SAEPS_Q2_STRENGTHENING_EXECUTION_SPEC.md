# SAEPS Q2 稿件补强执行说明与细则

**版本:** `Q2-STRENGTHENING-v1.0`
**日期:** 2026-09-20
**状态:** `PROPOSAL_ONLY / NOT_STARTED`
**适用对象:** `paper/revise/SAEPS_manuscript_integrated.tex` 及其机器可读证据
**执行类型:** 独立的论文补强与新证据提案，不修改历史 confirmation 结果

## 1. 目标与边界

本补强计划的目标是把稿件从“经典消元结构的严格数值演示”提升为“有独立验证、边界清楚、可以接受同行质询的局部曲率诊断论文”。目标不是通过新增实验强行获得阳性结论。

本计划必须遵守以下边界：

1. `docs/EXECUTION_CONTRACT.md`、`docs/LOCKED_PROTOCOL.md` 和 `configs/locked/` 具有更高优先级；
2. 历史 P0–P9 结果、失败运行、confirmation seeds 和锁定配置均为只读；
3. 新代码、配置、seed、raw results 和 aggregation 必须使用独立 namespace，例如 `paper_strengthening_v1`；
4. 本文件不授权新的 confirmation。需要运行新的 PINN 训练、profile 或独立数据实验时，必须先取得单独的执行授权，并在运行前完成 development、阈值冻结和 hash 记录；
5. 新结果只能支持 `SUPPORTED`、`PARTIALLY_SUPPORTED` 或 `NOT_SUPPORTED` 中真实对应的结论，不得以修改阈值、seed、gamma 或 benchmark 的方式改善结果。

## 2. 需要解决的核心审稿风险

补强任务只围绕以下三个可证伪问题展开：

1. **非线性 profile 问题：** SAEPS 是否能预测同一有限阻尼目标下，神经状态重新优化后形成的局部 profile curvature？
2. **经典基线问题：** SAEPS 除了重写 Schur/variable-projection 结构之外，是否提供了可复现的诊断价值？
3. **外推问题：** 结论是否只适用于一维、合成、紧凑网络和特殊参数结构？

如果其中一个问题无法通过合规实验回答，论文必须收缩相应主张，而不是把未完成的结果写成方法优势。

## 3. 优先级和阶段依赖

| 阶段 | 内容 | 依赖 | 主要产物 | 通过条件 |
|---|---|---|---|---|
| S0 | 主张和证据冻结 | 无 | claim ledger、reviewer risk matrix | 每个主张都有证据、范围和允许措辞 |
| S1 | Profile 工程复核 | S0 | profile dry-run、测试日志、schema | 失败点可追踪，禁止静默插值 |
| S2 | Profile development 与阈值冻结 | S1 | development raw、profile config hash | stationarity、步长和拟合规则在 confirmation 前冻结 |
| S3 | 独立 profile/基线验证 | S2、单独授权 | raw manifests、paired summary | 同 checkpoint、同 gamma、同权重、同坐标成对比较 |
| S4 | 泛化与敏感性补强 | S3 | multi-parameter/2D 或非合成证据 | 不根据结果事后挑选 benchmark；失败保留 |
| S5 | 论文重写与发布审计 | S3/S4 或明确收缩主张 | strengthened tex/pdf、tables、figures、audit | 所有 paper-facing 数值由 raw 自动生成 |

若 S3 的 profile scientific gate 失败，S4 不得通过增加网络宽度或调整 gamma 来“修复”；应进入 `LIMITED_CLAIMS` 路线。

## 4. S0：主张冻结与风险台账

### 4.1 主标题主张

在任何新实验前，先把论文主张冻结为以下候选版本之一：

- **完整版本：** SAEPS 是一种有限阻尼、checkpoint-dependent 的局部曲率诊断，并且在独立 nonlinear profile 上比 raw fixed-state sensitivity 更接近目标几何；
- **收缩版本：** SAEPS 是一种有限阻尼的局部 Gauss–Newton state-elimination 诊断，其相对 fixed-state baseline 的 exact-Hessian 误差在声明的合成 inverse-PINN 条件下下降；
- **失败版本：** SAEPS 的代数和工程实现可复现，但对 nonlinear profile 的预测价值尚未得到支持。

只有 S3 scientific gate 通过，才可以使用完整版本。否则默认使用收缩版本。

### 4.2 Claim ledger 必须包含

`docs/paper_strengthening/CLAIM_LEDGER.md` 的每行至少包含：

```text
claim_id, exact_claim, evidence_paths, statistical_unit,
planned/valid/failed denominator, allowed wording,
forbidden wording, limitation, status
```

以下措辞默认禁止：`global identifiability`、`posterior uncertainty`、`certified reliability`、`universally valid`、`causal effect`、`nonlinear profile equivalence`（除非 S3 明确通过）。

## 5. S1–S3：Nonlinear profile 补强

### 5.1 目标定义

对每个合格 checkpoint \((\theta_0,\lambda_0)\)，固定记录中的 residual weights、parameter coordinate 和

\[
\gamma=\alpha\lambda_{\max}(J_\theta^T J_\theta).
\]

定义与论文 Proposition 1 一致的有限阻尼 profile：

\[
\Phi_\gamma(\lambda)=\min_\theta
\left[L(\theta,\lambda)+\frac{\gamma}{2}\|\theta-\theta_0\|^2\right].
\]

比较对象必须同时包含：

1. `F_raw`；
2. fixed-state Gauss–Newton；
3. SAEPS finite-\(\gamma\) Gauss–Newton；
4. exact finite-\(\gamma\) Hessian Schur reference；
5. nonlinear reoptimized profile curvature；
6. 可计算时的 undamped VP/SVD 或 physical-FIM reference。

### 5.2 profile 运行规则

每个 profile point 必须：

- 从同一个 \(\theta_0\) 初始化；
- 禁止 previous-point continuation；
- 使用同一 optimizer、loss scale、residual weights 和 stopping rule；
- 同时检查 optimizer termination、loss plateau、normalized state gradient 和局部 Hessian/PSD 条件；
- 保存初始状态、最终状态、参数位移、profile loss、gradient、迭代数和失败原因；
- 缺失点必须保留为 `PROFILE_FAILURE` 或其他合法终止状态，禁止插值或静默删除。

步长网格、profile fit window、stationarity threshold、missing-point rule 必须先在 development 中确定，再写入独立 locked config。不能在看到 held-out 结果后缩小步长、放宽梯度阈值或更换 fit window。

### 5.3 建议的 development 设计

development 只用于回答“是否能稳定测量”，不能用于报告主结果：

- 使用现有允许的 development seeds 做小规模可行性检查；
- 至少覆盖三个对数步长尺度，并包含正负对称位移；
- 比较独立初始化、point-order invariance 和相同 checkpoint 的重复性；
- 单独记录 `profile curvature error` 与 `stationarity failure`，不能把两者合并成一个成功率；
- 用 development 结果冻结 profile 规则和确认阶段所需的最小有效分母。

### 5.4 S3 scientific gate

确认阶段开始前，必须在 config 中写入以下 gate：

- 核心 checkpoint 有预先声明的有效性分母；
- 每个有效 checkpoint 的 profile point 有预先声明的最小覆盖率；
- SAEPS、raw 和 profile 使用同一 checkpoint、同一 gamma 和同一 residual information；
- 主要比较使用 checkpoint 内成对差值 (D_i=E_{raw}^{(i)}-E_{SAEPS}^{(i)})；
- 所有失败点和失败原因进入 denominator 与 summary。

建议的默认审查门槛是“核心 cohort 至少 9/10 个有效 checkpoint，且每个有效 checkpoint 至少 80% profile points 通过 stationarity 与 fit-quality gate”；但该数值只有在 development 后正式写入新协议才生效。若未达到，科学状态只能是 `PARTIALLY_SUPPORTED` 或 `NOT_SUPPORTED`。

## 6. S3：强基线与敏感性审计

新增结果必须采用统一表格，至少包括：

| 方法 | 状态是否重优化 | 是否包含 residual 二阶项 | 是否有限阻尼 | 主要用途 |
|---|---:|---:|---:|---|
| Raw fixed-state GN | 否 | 否 | 否 | 原始 baseline |
| Fixed-state exact Hessian | 否 | 是 | 否 | 参数二阶项基线 |
| SAEPS finite-\(\gamma\) GN | 局部线性消元 | 否 | 是 | 待验证方法 |
| Exact finite-\(\gamma\) Schur | 隐式局部参考 | 是 | 是 | gold-standard local reference |
| Nonlinear reoptimized profile | 是 | 由优化产生 | 是 | 关键独立验证 |
| VP0/SVD 或 physical FIM | 依实现 | 依实现 | 依实现 | 经典替代解释 |

必须审计：

1. gamma sweep 的 retained fraction、effective rank、condition number 和排序稳定性；
2. physical/log parameter coordinate 变化；
3. residual block weights 变化；
4. network width/depth 与 initialization；
5. profile cost、SAEPS cost、exact-Hessian cost 的同口径计时。

所有敏感性结果必须标注为 `pre-specified`、`development` 或 `post-hoc`; post-hoc 结果不能升级为 confirmation evidence。

## 7. S4：泛化补强路线

### 路线 A：完成现有两参数协议

优先复核历史 8/10 availability-limited 结果。如果补充运行被单独授权，必须使用新的 run namespace，并提前声明是否属于 confirmation、replication 或 descriptive extension。不得覆盖历史 8/10 结果。

### 路线 B：增加独立问题

如果不补两参数队列，应增加一个与现有一维合成问题不同的 benchmark，例如二维 PDE、非合成观测或具有真正参数耦合的 inverse problem。benchmark 的选择必须在 development 阶段确定，不能根据 SAEPS 优势大小选择。

### 最低可接受表述

若 S4 未完成，正文必须写明：

> Evidence is restricted to local, checkpoint-dependent diagnostics on the declared synthetic inverse-PINN benchmarks. The result does not establish global identifiability, parameter uncertainty, or broad transfer across PDE classes.

## 8. S5：论文重写要求

### 8.1 标题与摘要

标题必须突出 `local`、`finite-damping` 和 `diagnostic`。摘要必须同时报告：

- valid/planned denominator；
- exact-Hessian reference 与 nonlinear profile 的区别；
- two-parameter availability limitation；
- profile stationarity 是否通过；
- 大规模实验只是 operator feasibility，不是大网络 accuracy 证明。

### 8.2 正文结构

建议正文顺序：

1. 问题与 scope；
2. 有限阻尼局部定义及 proposition；
3. baseline registry；
4. primary scalar paired results；
5. independent nonlinear profile test；
6. non-affine/architecture/generalization；
7. cost and failure audit；
8. limitations and claim ledger。

profile 失败必须紧邻相关正面结果呈现，不能只放在补充材料中。

### 8.3 贡献段模板

正文贡献应明确写为：

1. 给出一个有限阻尼 residual-space state-elimination curvature，并说明它与经典 Schur/variable-projection 结构的关系；
2. 用 exact-Hessian decomposition 区分 state-freezing error 与 fixed-state Gauss–Newton truncation；
3. 提供保留失败运行、成对比较、非仿射检查、架构审计和成本审计的可复现验证流程。

不要把“提出 Schur 补”或“证明参数可靠”列为贡献。

## 9. 工程产物与目录约定

若获得新实验授权，建议建立：

```text
docs/paper_strengthening/
  CLAIM_LEDGER.md
  REVIEWER_RISK_MATRIX.md
  DEVELOPMENT_DECISION.md
  FINAL_AUDIT.md
configs/paper_strengthening/
  development.yaml
  locked.yaml
outputs/runs/paper_strengthening_v1/
outputs/aggregates/paper_strengthening_v1/
paper/revise/
  SAEPS_manuscript_strengthened.tex
  SAEPS_manuscript_strengthened.pdf
```

每个 run manifest 至少包含：

```text
run_id, schema_version, timestamp, git_commit, config_path, config_hash,
seed, split, benchmark, architecture, dtype, hardware,
parameter_coordinates, residual_weights, gamma_alpha, gamma,
theta_stationarity, lambda_stationarity, profile_fit_quality,
CG_iterations, JVP_count, VJP_count, timing,
status, failure_reason, raw_result_paths
```

最终表格、图和摘要数字只能由同一份 aggregate JSON/CSV 生成。禁止手工回填数字。

## 10. 停止条件与科学决策

出现以下任一情况，应保存现有产物并在 `docs/ISSUES.md` 分类记录：

- explicit、matrix-free 和 profile reference 持续不一致；
- profile stationarity 长期失败，无法在不改变协议的情况下解决；
- SAEPS 不优于 raw 或 physical-FIM/profile baseline；
- 结果随普通 coordinate、weight 或 gamma 变化而翻转；
- 新 benchmark 只在 development seeds 上成立；
- 新证据要求修改已锁定配置；
- 为得到阳性结果而需要删除失败 seed、扩大容差或选择性报告。

科学失败不等于工程失败。正确的交付可以是“实现正确，但 nonlinear-profile 主张不支持”，而不是继续调参。

## 11. 最终验收清单

只有以下项目全部完成，才可把稿件标记为 `SUBMISSION_READY`：

- [ ] claim ledger 与 reviewer risk matrix 已审阅；
- [ ] 新实验 namespace、seed split、config hash 和 git commit 可追踪；
- [ ] profile point 无静默缺失，所有失败有原因；
- [ ] raw fixed-state、SAEPS、exact local reference、nonlinear profile 和经典 baseline 成对可比；
- [ ] planned/valid/failed denominator 在正文和 supplement 一致；
- [ ] profile scientific result 与 exact-Hessian result 分开表述；
- [ ] P6 的 8/10、历史 profile 1/5 以及其他负面结果没有被隐藏；
- [ ] 所有 paper-facing 数值由自动聚合生成；
- [ ] `python scripts/validate_repository.py` 通过，或已记录与本补强无关的既有失败；
- [ ] PDF 经渲染检查，图、表、公式和引用无截断；
- [ ] 目标期刊的 scope、分区类别和投稿模板已在投稿日期重新核验；
- [ ] 最终结论只使用 `SUPPORTED`、`PARTIALLY_SUPPORTED` 或 `NOT_SUPPORTED`。

## 12. 执行顺序建议

先完成 S0 和 S1，再决定是否值得运行新 profile confirmation。若 S1 显示 profile 工程仍无法稳定达到 stationarity，应立即采用收缩版本重写，不再扩大实验规模。若 S3 通过，再投入 S4 泛化补强；最后才进行正文、补充材料、cover letter 和投稿模板整合。
