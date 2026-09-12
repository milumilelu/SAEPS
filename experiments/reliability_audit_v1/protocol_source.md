# SAEPS 可辨识性与选择性可靠性补充实验任务说明

本文件是新的实验实施规范，不是已完成实验报告。起始审查版本为 `milumilelu/SAEPS@71fd3b025824f59146851f2ebfb5068e8cc9addb`。目标是判断 SAEPS 是否对真实参数辨识决策提供增量价值，而不是继续只验证它能否接近自己定义的有限阻尼矩阵。已有 V5 和 SO/Phase 2 记录保持原样；所有新增实验使用新命名空间。

## 1. 研究目标与边界

目标输出为：给定方程、观测和噪声条件，报告可靠的参数组合、不能可靠确定的方向，以及补充何种观测能改善辨识。允许明确返回 `UNRESOLVED`。不承诺识别任意问题的所有参数，不声称局部曲率证明全局可辨识性，不默认矩阵逆就是参数后验协方差。

核心假设必须在新数据上接受证伪：

| 编号 | 假设 | 主评价量 | 不支持时的处理 |
|---|---|---|---|
| H1 | 状态消元比冻结状态曲率更少产生错误的可靠性判断 | 同一有效诊断覆盖率下的错误接受率、配对风险差 | 删除泛化可靠性主张，保留有限范围的数值比较。 |
| H2 | 能保留可辨识组合，而非一律拒绝 | 组合参数误差、子空间角度、可用诊断比例 | 不能用零误报掩盖全拒绝。 |
| H3 | 阻尼、尺度和状态表示审查能揭示诊断脆弱性 | 分类翻转、阻尼路径、有效秩和子空间稳定性 | 报告算法依赖，不宣称不变性。 |
| H4 | 诊断能够改善观测设计 | 同观测成本下，新增数据后的实际参数误差/剖面宽度 | 仅有特征值改善不构成成功。 |

结构可辨识性分析、FIM/SVD、剖面似然和数据重采样并非新概念。应将贡献限定为 PINN 神经状态干扰、有限阻尼与实际可靠性之间的具体桥接与验证，比较已有 FIM-guided PINNs、PINNACLE 和相关可辨识性研究。[^L1][^L2][^L3]

## 2. 不可变证据与工作区规则

开始时记录实际 `HEAD`、分支、工作区状态、Python/依赖版本、硬件以及旧证据清单的 SHA256。若远端已更新，记录新旧差异，但不能静默更换本次审查基准。已有未提交工作保留，不使用破坏性的 reset、clean 或历史重写。

以下历史内容只读：`outputs/runs/`、`outputs/posthoc/`、已有 `docs/evidence/`、已有 `paper_artifacts/`、已有锁定配置，以及 `revision_week/outputs/day1/` 和 `revision_week/outputs/phase2_v1/`。不能删种子、覆盖失败、改写旧汇总或把未运行位置记成数值成功。旧主线 `cf76ffe85a78c994351e50b97d013d33a0f01f85` 等 README 中列明的证据提交应继续可追溯。[^R1]

所有新路径均为**拟新增**，不是仓库已经提供的命令或模块：

```text
experiments/reliability_audit_v1/
    protocol.dev.yaml
    protocol.locked.yaml
    run_plan.json
    source_manifest.json
    decision_rule.md
    benchmark_registry.json
src/saeps/reliability_audit/
    observation_models.py
    heat_references.py
    likelihood.py
    diagnostics.py
    profiling.py
    decisions.py
    acquisition.py
    validation.py
tests/reliability_audit_v1/
outputs/reliability_audit_v1/
    pilot/<version>/
    confirmation/<run_id>/
    intervention/<run_id>/
    manifests/
docs/reliability_audit_v1/
    RESULTS.md
    CLAIM_LEDGER.json
    FAILURE_AUDIT.md
    COST_AUDIT.md
    figures/
```

优先以适配器调用现有 `src/saeps/core.py`，不改变旧 API 行为。确需修改旧实现时先新增回归测试、保留旧数值与独立版本记录。推送仓库不属于本任务文件的自动授权范围。

## 3. 概念与接口必须先统一

物理参数使用 `p`，神经状态及未知初始条件等干扰变量统一使用 `w`。定义三个不同对象，禁止混称：

\[
F_{raw}=J_p^TJ_p,
\]
\[
F_\gamma=J_p^T[I-J_w(J_w^TJ_w+\gamma I)^{-1}J_w^T]J_p,
\]
\[
I_{obs}=J_y^T\Sigma^{-1}J_y,
\quad y=\mathcal H(u(p)),
\]

其中最后一个对象依赖独立物理前向模型和观测噪声。当初始幅度等物理干扰参数未知时，`I_obs` 先包含它们，再进行正确的干扰参数消元或非线性剖面；不能拿“干扰量已知的 FIM”作为未知干扰情形的参照。

各模块至少提供明确的数据接口：观测生成器返回实际测量量、噪声协方差及类型；参考求解器返回状态、观测和观测灵敏度；诊断器返回完整物理参数矩阵、阻尼与线性求解误差；判决器返回状态及原因，不仅一个浮点分数。实际函数签名由实施者确定，禁止在文档中声称尚未实现的 CLI 已可运行。

## 4. RI-0：先做解析测试与历史可用性审计

### 4.1 必须复现的解析测试

随附 `verify_identifiability_counterexamples.py` 可独立运行，依赖 NumPy，不依赖 SAEPS。当前交付已运行通过七组检查，其中热方程组同时包含两种混淆。复制到新增测试目录后，需要再针对实际 SAEPS 接口建立一致性测试，而不是仅保留独立公式实现。

| 测试 | 断言 | 要防止的误解 |
|---|---|---|
| 线性状态补偿 | `r=w+p-y` 的无锚定 profile 恒为 0，但 `F_gamma=gamma/(1+gamma)>0` | 精确约化阻尼 Hessian 不等于真实参数信息。 |
| 正阻尼核 | 正阻尼精确算术下 `ker(F_gamma)=ker(J_p)` | 不能用其精确秩直接检测全部状态补偿退化。 |
| 状态重参数化 | `w=c*z`、固定欧氏阻尼会改变诊断；同步变换度量时简单例恢复 | 不能自动声称状态坐标不变。 |
| 联合相关性 | `[[1,1],[1,1]]` 的两个 eta 都是 1，但秩为 1 | 对角相对分数不是单参数独立可靠性。 |
| 配置点复制 | 相同节点复制且权重归一化后矩阵不变 | 新配置点数不等于新独立实验信息。 |
| 热方程两类混淆 | 温度对 k/C 的共同尺度退化；未知初始幅度对单快照的补偿退化 | 物理参数相关与状态补偿是两类不同测试。 |
| 全局别名 | `p**2` 在 ±p 局部曲率都为正但观测相同 | 局部满秩不证明全局唯一。 |

基础线性代数测试使用 float64；中等条件数例的公式误差默认要求 `rtol<=1e-8, atol<=1e-12`。对于理论零值使用绝对误差与已知尺度，不以一个近零量作为相对误差分母。上述为新增工程默认，可在正式冻结前调整并说明，但不能修改历史验收标准。

### 4.2 历史失败根只审计，不追认

读取 Phase 2 的 20 个 scalar 和 10 个 multi 根记录，输出逐根表：损失及分项、归一化状态梯度、原始/加锚状态块谱指标、停止原因、迭代预算、耗时、参数域及 checkpoint hash。区分 `trial_budget_exhausted`、求解器错误、参考不可用、状态非平稳和状态非极小。

历史报告已说明独立有效根为 0/30，E2/E3 因上游条件停止，E6 低成本认证未过门槛。不得把旧失效记录附带的有利 SO 数值当作确认性结果。[^R2]

**RI-0 交付：** `ANALYTIC_TEST_REPORT.json`、`HISTORICAL_ROOT_AUDIT.csv`、`OBJECTIVE_AND_UNITS.md`。没有通过公式与接口测试，不开展新批量训练。

## 5. RI-1：建立有可辨识真值的基准族

### 5.1 共同定义

先采用无量纲合成热方程：`C*T_t=k*T_xx`，`x in [0,1]`，齐次 Dirichlet 温度边界，初始温度 `a*sin(pi*x)`。默认 `k=0.6, C=1.2, a=1`，故 `alpha=0.5`。这些数值只是实验起点，不是材料常数。参数取正，优化与谱比较采用预先声明的对数坐标。

已知量、待估量、干扰量必须写进注册表。不存在已知体热源或非零热流边界；否则共同尺度对称性可能改变。噪声是添加到**实际观测量**上的独立高斯噪声，默认温度 `sigma_T=rho*1`，其中参考 1 是预先固定的仪器/无量纲温度单位，不是对 B4 初始幅度的额外观测，也不根据测试数据或拟合真值后验选取。热流使用单独声明的 `q_ref` 和 `sigma_q`，不能把两种单位不同的观测共用未经解释的权重。

### 5.2 四个主基准与两个恢复基准

| 编号 | 未知物理参数与干扰量 | 观测 | 可辨识参照/目的 |
|---|---|---|---|
| B1 强辨识 | k 未知；C、a 已知 | 多时刻温度 | 单参数信息充分的阳性对照。 |
| B2 弱辨识 | k 未知；C、a 已知 | 极早期短时间窗温度，加噪声 | 结构上可辨识但实际信息不足。 |
| B3 物理参数混淆 | k、C 未知；a 已知 | 多时刻温度 | 只能确定 alpha=k/C；共同对数尺度方向为零。 |
| B4 状态/初值补偿 | k 未知、C 已知；a 是未知干扰量 | 一个非零时刻的完整或多点温度快照 | a 能补偿 k；剖面 k 时必须重新优化 a 和网络状态。 |
| B5 时间观测恢复 | 与 B4 相同 | 在不同时间增加第二次温度快照 | 一般能区分 a 和 k；验证时间激励价值。 |
| B6 物理测量恢复 | 与 B3 相同 | 温度＋已校准热流 | 一般能区分 k、C；验证改变观测类型的价值。 |

B3 的物理参数 Jacobian 自身可能已经秩亏，它不一定能证明 SAEPS 优于 raw。B4 才直接检验状态消元的增量意义。论文主结论不能只建立在 B3 上。

建议 B1/B3 的基础温度点为 `x=[0.2,0.4,0.7]`、`t=[0.02,0.08,0.2,0.4]` 的笛卡尔积。B2 用同样空间点及 `t=[1e-5,4e-5,7e-5,1e-4]`，保持测量数一致。B4 在 `t*=0.2` 选择 12 个内部位置；B5 的第二快照可从预先冻结的候选时刻中选择。所有设计先由解析观测灵敏度核查退化与非退化性。

对于 B4，`a` 必须归入剖面的干扰变量，绝不向训练损失输入真实 `a=1` 的已知初值标签。允许使用已知初值函数形状 `a*sin(pi*x)`，但 `a` 需要估计。参数搜索边界不能把平坦或无界 profile 人为截成“有限置信区间”；触边返回 `TRUNCATED` 并报告。

### 5.3 独立参照

热方程首先用解析式生成数据、灵敏度和 profile；再增加一个独立的有限差分/谱离散求解器做收敛核查，防止 PINN 与“参考”共享同一种误差。先固定参考网格/时间步细化方案，例如连续两级细化后，观测变化小于噪声标准差的 1%，并报告实际结果。零噪声例使用单独绝对数值容差，不出现除以零的似然。

将现有 Burgers、Allen–Cahn 和制造解双参数问题保留为后续外推对照。未经解析或独立 profile 核实，不预先把其全部参数标为“可辨识真值”。旧有效中心用于回归/开发，新的物理可靠性确认须独立数据与新协议。

**RI-1 交付：** 完整 benchmark registry、解析秩与对称性说明、独立参考收敛报告、噪声生成测试以及固定候选观测集合。

## 6. RI-2：有限规模试点，先解决中心可用性

试点使用 B1—B4，在 `rho=1%` 下每个基准 3 个独立数据 realization、每份数据 2 个初始化，共 24 个基础训练。数据与初始化随机流分开；固定 `data_seed` 与 `optimizer_seed`，不使用一个 seed 混合控制所有随机过程。

先用现有 Adam→L-BFGS 管线。若失败集中在优化问题，再在相同 24 个问题上选一个有根据的替代：NNCG 或 SOAP，二选一，不展开大型优化器竞赛。它们是训练工具，不是可靠性诊断方法。按固定的训练预算比较可用性，记录失败，不反复换种子直到过关。相关方法见 ICML 2024 和 2025 年梯度对齐研究。[^L4][^L5]

分开输出三个状态：

| 状态 | 条件与用途 |
|---|---|
| `COMPUTABLE` | Jacobian/HVP/线性求解及数值误差检查通过；仅表明局部算子可计算。 |
| `FIT_QUALIFIED` | 在开发阶段冻结的损失、独立残差与收敛诊断通过；用于后续可靠性流程。 |
| `PROFILE_ELIGIBLE` | 对所声明的同一目标，满足局部剖面解释所需条件；SO 的 SPD/平稳性条件另行严格判断。 |

三者不能互相替代。GN 曲率在非平稳点可计算，但不能因此自动宣称它是极小值处参数 profile 的 Hessian。神经状态全空间 Hessian 因冗余或对称性不严格正定时，不可剪掉负值或加大阻尼后声称证明了原问题可辨识；要报告所改变的目标。[^R3]

开发默认可考察归一化梯度 `<=1e-5` 与连续两次目标相对变化 `<=1e-6`，但它们只是收敛筛查，不是局部极小的数学证明。应冻结归一化公式、检查频率和预算上限。仅为新实验选择标准，不修改旧协议。参考解/真值可用于评估数值准确性，不能输入测试集的实际可靠性判决。

**扩展门槛建议：** 每个主基准至少 5/6 个试点拟合可用，且方法可以在不查看测试真值的情况下输出诊断。该门槛是工程投入决策，不是统计显著性结论。若两种预先限定训练方案都失败，停止批量确认，输出失败原因；可另立版本改用低维状态基、硬初边值实现或约束一致消元，但不能把新对象冒充原对象。

## 7. RI-3：诊断器、判决规则和必要消融

### 7.1 必须实现的比较对象

| 方法 | 作用 | 公平性要求 |
|---|---|---|
| RAW | 冻结状态 GN 基线 | 与 SAEPS 使用相同 checkpoint、参数坐标和残差定义。 |
| SAEPS-GN | 当前主体方法 | 预先冻结阻尼族与选择规则，不按真值误差选择最好 gamma。 |
| VP0/SVD | 未阻尼局部投影基线 | 仅在数值秩稳定时报告；失败保留，不以随意 jitter 假装可用。 |
| 物理观测 FIM | 独立观测映射的局部参照 | 干扰参数已知/未知必须与试验一致；计入前向与灵敏度计算成本。 |
| 非线性 profile | 区间形状和多解参照 | 固定目标参数后，重优化其他物理与状态干扰量。 |
| SAEPS-SO | 次要精度消融 | 只在满足其解释条件时纳入；保留全部计划分母。 |
| 数据 bootstrap | 少量高成本区间核对 | 真正重采样观测并重拟合；不把初始化 ensemble 当 bootstrap。 |

独立物理 FIM 是参照，不要求 SAEPS 比正确参照更准。价值可表现为减少 RAW 的误判，或在已有 PINN 条件下以更低边际代价接近昂贵非线性 profile。不能预先假定 PINN 比小型经典前向求解器更快。

### 7.2 阻尼、尺度与噪声

新的残差必须分清 `observation_likelihood`、`physics_penalty`、`initial_boundary_constraint`、`state_anchor` 四类贡献，保存其各自的权重。观测项按真实 `sigma` 白化；确定性 PDE 配置点使用积分/平均归一化。将训练时 mean 和统计似然的 sum 之间的缩放写清楚，所有 Hessian 参照采用同一目标。

新开发默认阻尼为 `gamma=gamma_rel*s_ref`，`gamma_rel=[1e-8,1e-6,1e-4,1e-2,1]`。`s_ref` 的定义必须固定，例如固定标准坐标中状态 GN 的谱尺度估计；显式或随机估计方式、随机种子和成本一并保存。归一化不能被声称解决任意网络坐标变化。最小阻尼若求解不可靠，返回不可用，而不是静默移除。

正参数使用固定 `log(p/p_ref)`，跨物理量比较以 `p_ref` 或明确的容许误差度量定义坐标。参数尺度、gamma 与损失权重一旦进入确认阶段，不得根据测试结果重调。

### 7.3 最小判决机制

先输出连续指标：完整矩阵、特征值、有效秩、强/弱子空间、绝对曲率尺度、eta、线性求解残差以及阻尼路径。eta 仅命名为“相对保留比例”。数值误差覆盖的近零特征值标为 `UNRESOLVED`，不强行判断正负。

在 gamma 路径上沿固定或经过明确配准的方向，考察曲率是否随 gamma 下降而稳定、是否近似按 gamma 衰减；若可稳健获得 F0，同时报告 `F_gamma-F0`。这是正则化依赖诊断，不是普遍可辨识性定理。不能在每个 gamma 任意切换特征向量后比较“同一方向”。重复特征值用子空间投影距离，而非单根向量角度。

最终允许四种结论：`SUPPORTED_COMBINATION`、`WEAK_OR_CONFOUNDED`、`UNRESOLVED_NUMERICAL`、`UNRESOLVED_MODEL_OR_SCALE`，并附原因。针对单参数的“可靠”标签必须有冻结的误差/信息阈值与开发校准说明。未建立统计模型的分数只能叫 score，不能包装为 95% 置信区间。

结构审查可以成为整个流程的前置环节，但所有竞争方法获得同样的结构信息。基准解析标签只能用作评估真值；不能直接输入 SAEPS 的评分器，又在对比中不给其他方法。分别报告“仅诊断器”与“共同结构审查＋诊断器”的结果，防止把解析知识的作用算成算法增益。

### 7.4 必需消融

在少量固定开发中心上先做：去掉状态消元；只用对角 eta；使用完整联合谱；不检查 gamma 依赖；加入 gamma 依赖与拒绝判断；在可用子集加 SO。所有版本成本与可用率同时报告。

做三种不变性/稳定性检查：保持物理单位等价的坐标换算；保持函数集合等价的状态重参数化；配置点复制并正确归一化。前两者若涉及锚定度量改变，明确比较固定度量和协变度量两种目标。新增不同配置点是离散化精化，另列，不与精确复制混淆。

## 8. RI-4：确认实验与统计设计

试点结束后冻结代码哈希、基准、数据种子、初始化种子、预算、判决规则、主指标及输出清单。使用新的确认数据，不能把试点数据重复计入主结果。

建议的完整确认规模是 B1—B4 × 噪声 `[1%,5%]` × 每格 20 个独立数据 realization × 每份数据 2 个优化器初始化，共 **320 个 PINN 基础拟合**。所有后处理方法尽量复用相同 checkpoint，不把诊断方法数再乘为训练数。零噪声仅为独立数值/解析对照，不计入统计覆盖率。

若资源只允许较小研究，预先冻结为 1% 单噪声版本（160 个基础拟合），相应收窄论文对噪声泛化的结论。不能看到结果后选择保留哪种噪声版本。实际资源预算依据试点实测决定，本文件不预估墙钟时间。

独立统计单位是数据 realization，不是初始化 seed。同一数据的两次拟合按预定规则聚合，或者使用数据层聚类 bootstrap；不把 40 个拟合谎称为 40 份独立观测。多 gamma 和多时刻也不是新增独立样本。

### 8.1 主指标

默认主要参数误差容许量为 `delta=log(1.10)`，用于正参数的绝对 log 误差；5% 和 20% 作为敏感性分析。它们是应用型实验选择，不是可辨识性的普遍标准。B3 对 alpha 单独评估，不把无法确定的 k、C 强行计作成功估计；B4 的 a 是干扰量，但须记录其估计与 profile 状态。

至少输出以下指标：

| 指标 | 定义与注意事项 |
|---|---|
| 可靠判断覆盖率 | 输出可靠参数/组合的数量 ÷ 全部计划目标；失败和拒绝保留在分母。 |
| 错误接受率 | 被判可靠但误差超过 delta 的目标数 ÷ 所有被判可靠目标数；同时列错误接受数 ÷ 全计划数。接受数为 0 时前者为 null。 |
| 风险—覆盖率曲线 | 各诊断分数阈值下的误差风险与接受比例；不因全拒绝得出优越结论。 |
| 组合恢复与子空间误差 | alpha 或其他已验证组合的 log 误差；与解析/独立参照子空间的主角度。 |
| Profile 一致性 | 是否闭合、触边、分支、多峰；区间端点与局部预测的偏差。 |
| 参数区间覆盖率 | 多份独立数据中，区间含真参数的频率及二项不确定区间；与诊断覆盖率分开命名。 |
| 计算成本与可用率 | 全流程和边际成本；每个方法有效/失败/未启动的全部分母。 |

对结构不可辨识的 k、C 或 B4 的 k，所谓窄区间若源于先验/搜索边界，应单列为先验限制或截断，不视为来自数据的可靠识别。局部 FIM 满秩也不自动等于满足 10% 容许误差。[^L1][^L6]

### 8.2 Profile 与覆盖率

热方程参考采用解析前向模型的观测似然，profile 目标不含任意神经锚定。固定一个目标参数/组合，重新优化其余参数和干扰变量。至少保存 31 个预先声明的扫描位置，按冻结规则允许细化和扩大范围；若预算耗尽或触及数值边界，返回 `TRUNCATED/UNRESOLVED`，不把端点当置信界。

PINN 的重新训练 profile 与解析 profile 分开报告；使用相同观测似然解释时，说明物理约束如何实现以及剩余物理违约。对于非高斯、边界、非正则或多模态情形，不机械套用卡方阈值。高斯正则例可把似然比近似作为参考，但需要模拟校验。

20 份独立数据不足以精确验证“95% 覆盖”。可先报告点估计与二项区间；若要把覆盖校准作为强主张，应在固定廉价参照上补足至少 100 份独立模拟数据，并根据希望的统计精度再决定 PINN 覆盖试验规模。不能用大量空间网格点替代独立数据重复。

比较方法时使用配对数据层差异和置信区间。预先选一个主比较，例如“在预设诊断覆盖率区间内，SAEPS 与 RAW 的错误接受率差”，其他对比标为次要/探索。多个 gamma 不分别捡显著性，不在看到结果后更换主指标。

## 9. RI-5：观测干预闭环

只有 RI-4 证明诊断有实际意义，才扩展观测设计。分别处理两类混淆：B4 增加不同时间快照得到 B5；B3 增加热流得到 B6。必须保留同类无效补测对照：B3 只增加温度点，不能因此恢复 k、C 的共同尺度。

对每个独立数据 realization，预先冻结候选集合和测量成本。默认可以设置温度点成本 1、热流点成本 5，但它们只是合成成本；在工程应用中应由实际测量条件替换。方法比较采用相同总成本和相同噪声条件，不简单比较传感器数量。

比较随机/均匀补测、RAW 灵敏度选择、独立物理 FIM 选择，以及 SAEPS 弱方向选择。所有方法只能使用当前已观测数据及允许的物理模型，不得查看候选位置尚未揭示的真实测量值。用合成真值生成新测量只是实验环境，不是选择算法的输入。

增加候选观测后，要更新整个状态—参数线性化或采用有误差说明的更新，不能只给旧 Jp 添加一行、保持旧投影不变而声称精确 Schur 补。选点后必须实际获取新噪声 realization 的测量、重新估计参数并重新计算 profile。最终以参数误差、组合恢复、profile 宽度及失败率判断收益，而不是只报告所选矩阵的最小特征值。

如果已知结构分析足以判断必须测热流，应将这一规则作为所有方法共享的前置知识，并在非退化候选集合中比较更细的选点效率；不能把“知道要测热流”的解析答案包装成 SAEPS 新发现。

**RI-5 交付：** 补测前后成对记录、总测量成本、全部候选评分、所选点、实际新观测、重拟合结果和 profile。结论可以是无额外优势，不能因结果不理想更换候选池。

## 10. RI-6：可选的工程与模型误设验证

主线通过后选一个扩展，不同时开展多种新 PDE。优先使用二维热传导或分层热传导，保留清晰的独立有限元/有限差分参照；或者采用有许可、参数与传感器信息充分的真实热实验。仅增加一个复杂几何图而没有辨识真值，不算应用证据。

增加一个明确的模型误设测试，例如生成数据含小体源而拟合模型忽略它，或者热流测量增益未知。后者尤其重要：温度给出 k/C，未校准热流可能只给出增益与 k 的乘积，重新产生参数混淆。先分析结构，再定义评价目标，不预设诊断必然检测所有模型错误。

如果只完成理想模型、已知噪声的合成试验，最终论文必须保留这一限定，不能写成全面工业可靠性认证。2026 年相关研究已把模型误设与观测结构列为重要限制。[^L7]

## 11. 数值、成本与失败记录规范

每个计划运行都要有一个终态；过程状态、数值状态和科学判决分别存储。例子如下，所有未产生的值使用 JSON null，而不是 0 或伪造默认值：

```json
{
  "run_id": "proposed_unique_id",
  "protocol_id": "reliability_audit_v1",
  "code_commit": null,
  "config_sha256": null,
  "benchmark": "B4",
  "data_seed": null,
  "optimizer_seed": null,
  "physical_parameters": ["log_k"],
  "nuisance_parameters": ["log_initial_amplitude", "neural_state"],
  "noise_model": {"kind": "gaussian", "sigma_temperature": null},
  "parameter_coordinate_definition": null,
  "residual_block_weights": null,
  "gamma": null,
  "gamma_scale_definition": null,
  "execution_status": "NOT_STARTED",
  "numerical_status": null,
  "fit_qualified": null,
  "profile_eligible": null,
  "decision_status": null,
  "failure_reason": null,
  "upstream_gate": null,
  "F_raw_path": null,
  "F_gamma_path": null,
  "observation_FIM_reference_path": null,
  "reference_kind": null,
  "rank": null,
  "rank_threshold_and_error_margin": null,
  "subspace_error": null,
  "profile_status": null,
  "parameter_log_error": null,
  "combination_log_error": null,
  "observation_rmse": null,
  "training_seconds": null,
  "diagnostic_seconds": null,
  "reference_seconds": null,
  "peak_memory_bytes": null,
  "jvp_count": null,
  "vjp_count": null,
  "hvp_count": null,
  "linear_solver_iterations": null,
  "checkpoint_sha256": null
}
```

`execution_status` 区分 `COMPLETED`、`INTERRUPTED`、`NOT_STARTED`、`PROTOCOL_STOP`。`numerical_status` 区分 `PASS`、`FAIL` 和 null。`decision_status` 独立于运行状态，`COMPLETED/PASS` 不表示科学假设获支持。

至少单列五类失败：实现错误、训练/中心不合格、线性或谱计算不可靠、参考不可用、模型/信息不足。下游未启动不记成“方法给出错误结果”，但保留在全计划可用性分母。

成本包括基础训练、重训练、Jacobian/HVP、线性解、谱估计、profile、bootstrap、失败尝试、启动/预热和内存峰值。共享 checkpoint 的训练成本不重复相加；边际诊断成本和端到端成本分别报告。用了 dense Hessian/eigh 的阶段不能称作全矩阵自由；普通数值谱下界不能称作严格认证下界。[^R3]

## 12. 发布级图表、主张清单与终止规则

建议最终只围绕六幅主图组织：状态补偿与阻尼的解析反例；强/弱/结构不可辨识的参数/组合剖面；阻尼及坐标稳定性；风险—诊断覆盖率；补测前后参数恢复；包含失败的成本—精度—可用性。附表给出全部计划分母和原始数据路径。

`CLAIM_LEDGER.json` 为每条主张记录 `SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE / NOT_TESTED`，对应指标、有效与计划分母、证据文件和限制。禁止用含糊的“部分支持”代替“没有有效独立比较”。

| 拟发表声明 | 最低要求 |
|---|---|
| 比 raw 更接近固定有限阻尼参考 | 同目标、同坐标的数值对比；不外推物理可靠性。 |
| 改善参数可靠性判断 | 新数据上的误报/覆盖配对证据；不只比较矩阵。 |
| 恢复可辨识组合 | 组合真值、子空间与独立 profile 证据。 |
| 有观测设计价值 | 同成本补测后实际重拟合收益。 |
| 低成本 | 全流程和边际账本；昂贵参考辅助明确计入。 |
| 置信区间校准 | 独立数据重复覆盖与宽度，同时解释似然/先验。 |
| 全局可辨识、普适认证 | 本计划不支持此类一般性声明。 |

以下情况触发收窄而非追逐结果：解析阴性对照不能正确解释；只能靠全拒绝避免误判；独立参照显示 SAEPS 未比强基线提供精度/成本/可用性收益；中心问题导致多数样本不可评价；阻尼或坐标变化造成广泛未解释翻转；SO 只在筛选后的旧中心有效。

RI-0 与 RI-1 无论正负都必须完整交付。通过试点才执行确认；确认支持 H1/H2 才优先投入补测闭环。若只支持固定目标的局部数值精度，就明确回到窄范围曲率方法论文，保留全部负结果。

## 13. 交付清单与执行入口

最终交付应能回答：方法究竟看到了什么信息、不能判断什么、何时会误判、它相对既有工具的增量是什么。至少包含冻结协议、全运行清单、独立参考、原始记录与哈希、统计脚本、全部图表源数据、失败审计、成本账本和逐条科学主张。

可以将下面这段作为后续执行任务的入口：

> 以本文件为新实验协议草案，在不改写 SAEPS 历史证据的独立分支或工作树中实施。首先只完成 RI-0、RI-1 和 RI-2 的限定试点，验证实际核心接口的解析反例、热方程两类混淆与独立参照，逐根审计原 Phase 2 可用性问题。保存所有失败与未启动分母。试点完成后冻结新的代码、数据和判决规则，再按门槛执行后续确认，不通过则交付止损报告。不得为了得到正结果更换种子、改变搜索边界或降低确认门槛；不得把本计划中的假设和预期写成已完成结果。

## 参考依据

[^R1]: SAEPS README，审查提交 71fd3b0，包含证据范围、历史提交与可复现约束。[固定版本](https://github.com/milumilelu/SAEPS/blob/71fd3b025824f59146851f2ebfb5068e8cc9addb/README.md)。
[^R2]: SAEPS Phase 2 最终执行报告，含 reporting audit；独立有效根 0/30。[固定版本](https://github.com/milumilelu/SAEPS/blob/71fd3b025824f59146851f2ebfb5068e8cc9addb/revision_week/outputs/phase2_v1/final/PHASE2_REPORT.md)。
[^R3]: SAEPS Fixed-target directional curvature 数学说明，SO 恒等式、局部剖面条件与非严格数值谱界的限制。[固定版本](https://github.com/milumilelu/SAEPS/blob/71fd3b025824f59146851f2ebfb5068e8cc9addb/revision_week/METHOD_MATH_NOTE.md)。
[^L1]: Raue 等，2009，Structural and practical identifiability analysis of partially observed dynamical models by exploiting the profile likelihood，Bioinformatics。[DOI](https://doi.org/10.1093/bioinformatics/btp358)。
[^L2]: Naveen Raj R、Santo Banerjee，2026 年卷期，FIM-guided PINNs for real-time parameter identification in digital twins of nonlinear vibratory systems，Knowledge-Based Systems 335:115198。需进一步取得全文核对可复现细节，不依据摘要臆测实现。[论文](https://www.sciencedirect.com/science/article/pii/S0950705125022324)。
[^L3]: Lau 等，2024，PINNACLE: PINN Adaptive ColLocation and Experimental points selection，ICLR 2024。[论文](https://arxiv.org/abs/2404.07662)。
[^L4]: Rathore 等，2024，Challenges in Training PINNs: A Loss Landscape Perspective，ICML 2024。[论文](https://arxiv.org/abs/2402.01868)。
[^L5]: Wang 等，2025，Gradient Alignment in Physics-informed Neural Networks: A Second-Order Optimization Perspective，arXiv:2502.00604v2，本计划按核实到的预印本版本引用。[论文](https://arxiv.org/abs/2502.00604)。
[^L6]: Heitzman-Breen、Dukic、Bortz，2026，A Practical Identifiability Criterion Leveraging Weak-Form Parameter Estimation，Bulletin of Mathematical Biology 88:70。[论文](https://link.springer.com/article/10.1007/s11538-026-01639-x)。
[^L7]: Gu、Zhang、Miles，2026，Identifiability Limits of Physics-Informed Inference for Spatial Stochastic Dynamics from Static Snapshots，arXiv:2607.01749v1，预印本。[论文](https://arxiv.org/abs/2607.01749)。
