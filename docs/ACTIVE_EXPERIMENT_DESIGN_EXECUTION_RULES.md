# SAEPS 主动实验设计执行细则（AED-v1.0-DRAFT）

## 1. 文件性质

本细则把 `SAEPS_主动实验设计转向方案包.zip` 转成可执行的治理和实验要求。它是**新方向的草案**，不改变 `docs/EXECUTION_CONTRACT.md`、`docs/LOCKED_PROTOCOL.md`、`configs/locked/`、历史 outputs、既有 `PROTOCOL_STOP` 或当前科学结论。所有节点初始为 `NOT_STARTED`；没有单独授权前不得训练 PINN、创建 confirmation config 或读取 confirmation 标签。

任务包中的 H1（决策效果）、H2（强基线比较）和 H3（解除混淆机制）是待验证假设，不是仓库结论。ZIP 中的随机矩阵恒等式和 B4 解析控制只证明代数/解析参考，不能写成主动选点效果、PINN 验证或 confirmation 结果。

## 2. 隔离、来源与授权

1. 首次实现前记录 ZIP SHA256、解压文件名、方案正文 SHA256、当前 git commit、Python/dtype/hardware 和工作树状态。附件给出的历史基线 commit 只作为来源锚点，不得假定它等于当前 checkout。
2. 所有新代码、配置、raw outputs、manifest 和 evidence 使用独立 namespace：
   - `configs/active_design_v1/`
   - `outputs/runs/active_design_v1/`
   - `docs/evidence/active_design_v1/`
3. 不覆盖、不移动、不静默排除既有文件。当前工作树已有与本任务无关的删除和未跟踪文件；提交或推送前必须重新分类，不能把整仓库声明为 clean。
4. AED development seed、held-out seed、confirmation seed 必须在新协议授权时单独登记。不得复用既有 v2 confirmation `[10..19]`，不得把当前 development seed 当成新方向的 confirmation。
5. 只有用户/正式协议明确授权后，才能把 AED-6 的 development gate 转成锁定配置。锁定后修改候选池、成本、噪声、loss、网络、gamma、阈值、seed 或聚合规则，必须停止并写入 `docs/ISSUES.md`。

## 3. 首版科学范围

主线问题是：在已有少量观测、存在 neural state / nuisance 适应和参数混淆时，下一次可实现测量应如何选择，才能以更小累计测量成本改善目标参数或参数组合的反演。

首版 action 只允许 `a=(sensor_type, x, t, cost, noise_model)`，其中 `sensor_type` 为温度或经过标定的热流。改变热源/边界激励属于后续扩展；若未来加入，必须使用条件化前向模型或另行求解，并把额外成本显式计入。在线不可逆过程只允许选择当前之后的时刻；历史时刻只能用于离线设计对照，不能伪装成在线动作。

首版场景为：

- **B4→B5：未知初始幅度。** 选择位置/时间的温度测量，检验是否能解除初始幅度与 `k` 的混淆。
- **B3→B6：共同尺度。** 在温度测量外加入成本与噪声已定义的热流测量，检验是否能解除 `k/C` 共同尺度混淆。
- **B1：正面对照。** 检查方法不会在本来信息充分的场景明显倒退。

解析预期用于 sanity check，不能硬编码“B4 必须选另一时刻”或“B3 必须选热流”。选择器不得访问未选候选的真实测量值、测试真值或答案标签。

## 4. 数学对象与实现约束

在固定线性化点、固定残差尺度、固定旧观测权重和固定 `gamma > 0` 下，令

\[
M=J_w^T J_w+\gamma I,\quad B=J_w^T J_p,\quad C=J_p^T J_p,
\]
\[
Z=M^{-1}B,\quad F=C-B^T Z.
\]

候选观测先按已知正定协方差 `R_a` 白化，得到 `H_w,H_p`。若噪声相关，先做联合/条件白化，不能套用独立块公式。定义 `E_a=H_p-H_w Z`，候选增量为

\[
\Delta F_a=E_a^T(I+H_wM^{-1}H_w^T)^{-1}E_a,\qquad F_{new}=F+\Delta F_a.
\]

实现必须调用线性求解，不显式形成 `M^{-1}`。必须提供：

- explicit 与 matrix-free / JVP-VJP 路径的一致性；
- 直接重新消元与低秩更新的一致性；
- `ΔF` 对称化后的非负特征值检查；
- CG/迭代求解次数、相对残差、JVP/VJP 次数、批处理和预条件器记录；
- 固定 `M` 比较的边界检查。候选改变旧权重、gamma 或重新训练后，必须重新线性化，不能声称仍是同一个精确更新。

`F` 和 `ΔF` 是有限阻尼 PINN 目标的局部 GN 对象，不得称为真实 Fisher 信息、后验精度或自动的 Bayesian information gain。低秩恒等式不蕴含非线性重训后的参数误差必然下降。

## 5. 评分、批次与不确定性

首版评分使用固定物理坐标下的弱方向子空间：

\[
\mathrm{score}(a)=\frac{\operatorname{trace}(V_{weak}^T\Delta F_aV_{weak})}{\mathrm{cost}(a)}.
\]

`V_weak` 只能由当前允许的信息构造，不得从测试真值选择。多候选批次应逐次更新局部块，避免重复挑选冗余动作。若用多个数据相容 checkpoint 做保守评分，必须把它标为有限集合代理，不能称为完整后验。

必须至少比较：random、fixed-uniform、predictive-variance/ensemble、正确处理 nuisance 的 physical plug-in FIM（oracle 真值 FIM 单列）、明确实现的 `PIED-TIP`，以及 SAEPS acquisition、去状态补偿消融和固定/保守 gamma 变体。`H_p^T H_p` 不能作为唯一对手。

## 6. 最小执行顺序

### AED-1：治理与工程边界

建立 namespace、来源 manifest、seed 分配表和停止规则；把任务包现有检查复制为只读 evidence。此阶段不训练、不选点、不读取新测量标签。

### AED-2：代数与 API

先用 tiny/实际 residual 的开发对象验证白化、低秩更新、直接重消元、PSD 和计数。相关噪声、奇异/近奇异候选协方差、solve 失败都必须有显式 terminal status；不能用静默正则化掩盖失败。

### AED-3：动作与候选池

在开发阶段固定 B1/B3/B4 候选池、三档预算、成本和噪声模型。把在线/离线时间规则写入机器可读配置。候选排序稳定性必须在不看真实新测量值的条件下检查。

### AED-4：强基线开发

只使用通过既有 checkpoint 资格门的模型和新分配的 development seeds。每个方法使用相同初始数据、候选池、预算和重训预算；每个失败 run 留在 denominator 中并写 `failure_reason`。禁止按照结果删除难例、替换 seed 或重新选择场景。

### AED-5：最小闭环

每个入选场景先做一次完整候选排序，再执行一次实际加点和重新估计。最低输出包含：参数个体误差、可辨识组合误差、场预测误差、累计测量成本、选点时间、SAEPS solve 时间、重训时间、profile 时间和峰值内存（可可靠取得时）。

### AED-6：开发门

在读 confirmation 之前检查：数据兼容性、stationarity、profile 完成、排序稳定性、B1 是否明显倒退、至少一个 nuisance 场景是否有预算收益，以及与 physical FIM/PIED-TIP 的端到端成本比较。若 SAEPS 不胜过 physical FIM，但有稳定边际成本优势，只能据此收窄 claim；若两者均无优势，停止扩大模型名称和场景。

### AED-7/AED-8：仅在新协议授权后

授权后再锁定 config/hash/seed/聚合器，执行独立 held-out/confirmation 闭环并自动生成 manifest、raw results、figures、tables、summary。聚合必须保留计划 denominator 和所有 terminal status；最终科学状态仍只能为 `SUPPORTED`、`PARTIALLY_SUPPORTED` 或 `NOT_SUPPORTED`。

## 7. 运行记录与审计字段

每个 run 至少记录：`schema_version, run_id, timestamp, git_commit, source_zip_hash, config_path, config_hash, seed, split, benchmark, action_schema, candidate_pool, budget, sensor_layout, noise_model, architecture, dtype, hardware, optimizer, checkpoint_id, stationarity, residuals, parameter_error, identifiable_combination_error, field_error, selected_actions, cumulative_cost, gamma, CG_iterations, CG_relative_residual, JVP_count, VJP_count, training_time, selection_time, saeps_time, reoptimized_time, peak_memory, status, failure_reason`。

状态沿用仓库规则；不得漏写最终状态。truth-dependent 数值必须标记 `validation_only`。figures、tables 和论文摘要只从同一自动聚合数据源生成，不能手工填数字。

## 8. 停止与偏差

以下任一情况必须保留产物并写入 `docs/ISSUES.md`：理论公式和实现无法对应；explicit/matrix-free 持续不一致；候选白化或 solve 不稳定；候选池无法满足在线因果约束；所有可行动作都不能解除已知退化；SAEPS 不优于正确强基线；或需要修改已锁定 active config。科学失败不通过换 benchmark、调 gamma、删 seed 或降低门槛修复。

本细则完成后，项目仍处于“新方向已登记、尚未授权执行”的状态。它不把 ZIP 中的解析结果升级为实验结论，也不改变既有 SAEPS 验证项目的完成状态。

