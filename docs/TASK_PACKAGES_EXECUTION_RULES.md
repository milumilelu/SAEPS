# 两个任务包的阅读结论与执行细则

**状态：** `DRAFT / NOT_AUTHORIZED`

**阅读对象：**

- `PCAD_全新独立实验方案包_v1.zip` — SHA256 `165087C05BE9D1CAD19D3A372581BB7099F87E2171909F3F2C1DF718B47CA124`
- `SAEPS_State_Absorption_Mathematical_Reconstruction.zip` — SHA256 `4B897C5DADB9E8068CBA0040915FF62A5B4F384C72C76425B254B2FB1CC6C97E`

这份文件是对两个任务包的执行解释，不是对其中指令的自动授权。当前仓库的最高优先级仍是 `docs/EXECUTION_CONTRACT.md`、`AGENTS.md` 和已经锁定的 `docs/LOCKED_PROTOCOL.md`。PCAD 必须在独立工作树 `C:\Users\RZF\Desktop\博士课题资料\PCAD\research\pcad_v1` 和独立配置命名空间中实施；不得覆盖 `outputs/runs/`、`configs/locked/`、历史报告或既有协议结果。

## 1. 两个包各自解决什么问题

数学重构包重新界定研究对象：状态吸收是现象，状态消元是计算操作，消融是验证工具。它区分三种机制：有限配置点和网络自由度造成的非物理伪补偿；完整稳定物理算子配合 soft penalty 造成的信息衰减；状态锚定或相对阻尼造成的虚假确定性。它提出以物理方程约束的状态灵敏度和真实物理 nuisance 商空间定义局部观测信息，再把观测设计目标放在目标相关等价类上。

PCAD 包把这一重构变成一个独立的主动测量研究计划。PCAD 是有限预算物理校正方法；PHYS 是同点充分求解的强基线；NEURAL 是旧式神经状态消元代理；RANDOM、VARIANCE、FIST_CPOOL、SCENARIO 和 SCENARIO_PHYS 是登记的基线或扩展。研究问题是：在相同观测权限、反馈权限、反演器和费用下，物理一致的有限校正能否改善目标参数或目标组合的实际反演收益。包内没有声称 PCAD 已获胜，也没有新 PINN 结果。

## 2. 不能混淆的权威层级

| 内容 | 作用 | 当前处理 |
|---|---|---|
| 当前 SAEPS `AGENTS.md` 与 v2/v4/v5 协议 | 当前仓库执行纪律、历史锁和结果边界 | 最高优先级，继续有效 |
| PCAD `START_HERE.md`、`PROTOCOL.md`、`EXECUTION_RULES.md`、`config/study.json` | 新研究的内部定义、数值和实现契约 | 仅在 PCAD 工作树内有效，待单独授权 |
| 数学包研究笔记 | 假设、推导、反例和候选增量 | 用于实现与审计，不自动成为科学结论 |
| `validation/`、`math_checks_results.json` | 方案、代数和解析检查 | 只能证明有限维/解析检查通过，不能证明 PINN 或主动实验成功 |
| `registry/` | 计划登记 | 全部 `PLANNED`；不得当作已执行结果 |

如两个包内部出现冲突，先冻结该节点并记录版本缺陷；不得回退到旧 SAEPS 默认值，也不得为了得到阳性结果改变定义。

## 3. 启动前的硬边界

1. 在 PCAD 工作树中完整展开包，校验 `tools/validate_package.py --check-delivery`、参考单元测试和 `tools/generate_plan.py`。这些检查只能作为静态/参考检查。
2. 创建独立 Git 分支、Python 环境、`research/pcad_v1/` 输出根和配置哈希；记录硬件、dtype、依赖、提交、包哈希和 `config/study.json` 哈希。
3. 先实现真实 world 服务、物理求解器、PINN 训练/重训、候选池、策略、统一反演、成本账本和 raw manifest；包中已有 CLI 只是待实现验收接口。
4. 只用 development worlds `[100,101,102]` 做联调、数值错误修复和资源估算；不得查看 evaluation 结果来改定义。正式评估 worlds 为 `2000–2019`，mechanism/subset/engineering world 集合按配置原样使用。
5. 一次冻结代码、配置、registry 和环境后，按技术依赖执行全部登记比较。PCAD 不继承当前 SAEPS 的 confirmation seeds，也不读取旧 confirmation tensor。
6. 不因初始网络不理想、信息秩亏、零收益、profile 不闭合或 PCAD 未胜出删除 world、方法或轨迹。只有公式/代码错误、数据损坏、非法/非有限状态和资源边界可触发局部技术处理。
7. 不自动推送、不修改其他工作树、不把包内的 `AGENTS.md` 当作当前 SAEPS 仓库的覆盖指令。

## 4. 固定数值与方法定义

PCAD 配置的关键冻结值如下；任何变更必须增加协议版本并重新生成全部 registry：

- dtype `float64`；Adam，learning rate `0.001`；1D 网络 `[2,32,32,1]`，2D 网络 `[3,32,32,32,1]`，tanh；full batch；物理权重 `10`。
- 初始训练步数：1D `SHORT/STANDARD/EXTENDED = 200/1000/3000`，2D `SHORT/STANDARD = 400/1600`；每个测量费用单位重训 200 步；不启用 early stopping、gradient gate 或 profile gate。
- 1D 设计网格 63 个内部空间点、120 个时间步；2D 每轴 31 个内部点；Crank–Nicolson；PCAD 为右预条件 restarted GMRES，restart 20，每 RHS 最多 40 次 matvec，relative residual stop `1e-8`。PHYS 使用充分求解和同一观测算子。
- 正参数坐标统一为 `xi=log(p/p_ref)`，`p_ref=1`；温度噪声 `0.01`、热流噪声 `0.02`，费用分别为 1 和 2；候选标签不得传给 selector。
- 物理信息使用 `I=Gᵀ(I-NN†)G`，不向物理信息加 ridge；相对秩阈值 `1e-9`、绝对阈值 `1e-12`。主选择分数按字典序最大化 `(目标不可见维数减少/费用, kappa² 增量/费用)`；零收益继续按 salted-ID 并列规则选择。
- NEURAL 的 `gamma_alpha=1e-6` 只锚定网络状态块，物理 nuisance 先验为零；不得将该 proxy 称为真实观测 Fisher 信息。
- 默认前瞻深度 1；LOOKAHEAD 评估费用可行无序二元组，执行 salted-ID 较小成员后重新规划；不使用标准次模保证。
- FIST_CPOOL 使用 4 个固定名义假设、每候选 30 步模拟反演和显式模拟成本；不得称其为完整 PIED 复现。SCENARIO 使用 64 个 Halton 提案、保留 16 个有限假设、每点最多 50 次局部精修；它不是连续参数集合覆盖证书。

## 5. 执行阶段与 gate

### E0：环境、输入隔离和真实流程联调

完成工作树隔离、依赖和静态校验；实现 world 生成、公开初值、解析/有限差分 truth generator、候选读数、动作键、噪声键、checkpoint、统一 manifest 和成本账本。用 development worlds 验证 PCAD、PHYS、NEURAL、RANDOM 的单轮端到端闭环及标签隔离。

Gate：所有输入可由 seed/world/action 重建；selector 无法读取未购买读数或真值；物理参考 residual、观测读出和显式热流参数导数通过单元/解析控制；失败状态可序列化并恢复。

### E1：有限校正与真实 refit 的配对验证

在 H1、H2、H3F development worlds 上，比较 PCAD 与 PHYS 的状态校正 residual、灵敏度误差、候选排序和实际添加测量后的共同物理反演。保存 `I_hat`、PHYS `I`、全量叠行参考、秩安全增量差异、动作 regret、refit 误差和每个成本组成。E1 的主验证是“排序后真实重新估计”，不能用代数 surrogate 代替。

Gate：秩安全更新与全量重投影在预注册容差内一致；PCAD 的有限预算误差和候选选择可量化；所有方法使用同一 D0、world、噪声、预算、反馈和反演器。E1 阴性不停止其他独立技术块，也不授权调参救援。

### E2：机制、归因和互补性

执行 H1 强辨识、H2 未知初始幅度、H3R 目标 `log(k/C)`、H3F 目标 `(log k,log C)`，并完成机制矩阵：网络宽度 16/64、collocation 64/512、初始预算 SHORT/STANDARD、物理校正 cap `0/10/40/160`、anchor gamma 网格和 penalty 网格。验证单点零收益并不代表二点组合无价值；运行 LOOKAHEAD、OS/FR/SEQ 以及 TEMP_ONLY/EQUAL_COST controls。

Gate：目标切换、nuisance 秩变化、观测类型和调度语义均由配置驱动；不把解析热方程关系硬编码成选择规则；报告目标相关与目标无关的 null 方向。

### E3：完整登记比较

冻结后执行 `MAIN`、`ATTRIBUTION`、`EXTENDED`、`INITIAL_DATA`、`LOOKAHEAD`、`SCENARIOS`、`ENGINEERING`、`ENGINEERING_SHORT`、`VARIANCE_SUBSET`、`INIT_REPLICATE`、`TEMP_ONLY_CONTROL`、`EQUAL_COST`。计划量为 1282 条去重主动轨迹、140 条共享初始训练路径、最多 8414 次在线反演调用、48 次离线候选核查、最多 1282 个终点共同物理反演；FIST 假设 refit、scenario 精修、ensemble 训练和 profile 网格必须另行记账。

每条轨迹必须逐 world 配对保存：计划/开始/结束状态、策略、任务、预算、schedule、初值、动作序列、未购买标签隔离证明、估计、目标误差、AUBC、总费用、训练/物理/反演时间、GMRES matvec、失败原因和代码/配置哈希。技术失败不删除轨迹，不将 null 当 0，不把 carry-forward 写成测量插补。

### E4：统一聚合和主张裁决

聚合唯一数据流为 `raw manifests → aggregate → figures/tables/report`。world 是统计单位；主比较是 paired final error 和 replay-based AUBC；5000 次 paired bootstrap、95% CI；缺失值保留为 null，coverage/success 使用全部计划 world。报告各 block 的 planned/terminal/valid/technical-failure 分母，并区分算法失败、资源截尾、证据不足和科学负结果。

### E5：审计与交付

自动检查 registry 完整性、重复 world 配对、配置/代码哈希、标签泄漏、成本账本、nested calls、raw-to-aggregate 一致性和报告重建。交付内容包括所有 raw、manifest、聚合数据、图表、主张—证据矩阵、运行限制和未完成项。只有在 E0–E5 工程检查通过后，才能形成独立 PCAD 报告；这不等于 PCAD 获胜。

## 6. 数学包必须转化成的测试

1. 用有限配置点热方程 bump 反例验证：观测和配置残差可同时为零，但独立细网格 PDE residual 非零；明确这不是指定宽度 PINN 的表示定理。
2. 用稳定线性物理算子验证 soft penalty 等价于人工协方差，并验证 `c q_phys ≤ q_lambda ≤ q_phys` 的条件和范围；不得把 penalty 权重解释成测量噪声，除非另行声明概率模型。
3. 用状态坐标变换检查物理灵敏度/信息不变性；参数坐标变换必须同步变换目标导数。
4. 对旧 nuisance 秩亏和新暴露 nuisance 同时比较全量叠行与 rank-safe conditional update；不得把 `pinv(NᵀN)` 直接代入 full-rank 公式。
5. 复现实例 `y1=p+nu`、`y2=nu`：单点目标信息均为 0，联合信息为 `1/2`；因此不能未经证明套用次模贪心保证。
6. 残差—状态误差、灵敏度误差和有限假设 action-regret 只在声明的离散稳定性、有限集合和误差界内报告；没有可验证稳定常数或连续覆盖时，禁止写严格证书、全局误差常数、校准后验或全局可辨识性。

数学包已报告这些检查为合成代数/解析检查，未训练新 PINN、未运行闭环主动实验、未证明连续假设集覆盖、未证明普遍加速；这些边界必须原样进入最终报告。

证据分级：数学包推导和检查属于 **Level M**（有限维/解析、可复算）；当前仓库既有 SAEPS raw 属于历史 baseline；真实 PDE/PINN/主动采集结果属于 **Level E**，必须由 PCAD 工作树的机器可读运行产物支持。不得将 Level M 结果写成 Level E 科学结论。

## 7. 允许的结论与禁止外推

允许：在声明的 world、目标、观测池、预算和局部线性化下，比较 PCAD/PHYS/NEURAL 等方法的配对实际误差、成本、动作选择和失败边界；报告物理一致近似与神经 proxy 的差异。

禁止：将代数检查写成新实验结果；将 PCAD 称为已验证优越、全局最优、严格认证或普适方法；将物理局部信息称为全局可辨识性或后验覆盖；把有限 SCENARIO 假设集称为连续模型覆盖；把 FIST_CPOOL 称为完整 PIED；把相关性写成因果性；把任何 scientific negative 当作工程失败。

## 8. 当前状态和下一步

当前应保持 `NOT_AUTHORIZED / PLAN_DEFINITION_READY`。下一步是由用户明确授权 PCAD 独立工作树的 E0 实施；授权后先完成静态校验和最小真实端到端联调，再决定是否进入 E1。任何 PCAD 结果不得写回当前 SAEPS 的 locked config、历史 denominator 或最终科学结论。

## 附：本次阅读得到的机器证据

PCAD 包的 `validation/VALIDATION_REPORT.json` 报告 30 个参考单元方法通过、168 个 rank-safe update case，最大归一化误差约 `7.72e-14`；同时明确 `production_pinn_training_performed=false`、`active_measurement_trajectories_executed=0`。`registry/plan_summary.json` 报告 3097 个登记 job、1282 条去重轨迹和 140 条共享初始训练路径，状态为 `PLANNED_ONLY`。

数学包的 `math_checks_results.json`/`checks_run.log` 只覆盖合成线性代数、解析热方程和有限集合误差检查。其 `PROVENANCE.json` 明确 `new_pinn_training_executed=false`、连续相容集合覆盖未证明、未修改仓库。数学检查的数值可以作为实现回归基准，但不能填入 PCAD 的 world-level 统计或 SAEPS 的 paper-facing 结果。
