# SAEPS-Active 实验验证执行细则（AED-v0.2-DRAFT）

## 1. 执行重点与授权边界

本版响应任务更新：工作重点是**推进实验验证**，论文定位只用于确定可检验的主张、对照和指标。新的 `SAEPS_Active_论文方法与实验方案包.zip` 与粘贴文本是方法建议和待执行协议，不是已经完成的 PINN、主动反演、真实测量或提速结果。

本细则不覆盖 `AGENTS.md`、`docs/EXECUTION_CONTRACT.md` 和 `docs/LOCKED_PROTOCOL.md`，不修改既有配置、历史结果、`PROTOCOL_STOP` 或 confirmation seeds `[10..19]`。新实验只能使用独立 `active_design_v2` namespace；在单独协议授权、seed/split 登记和配置 hash 冻结前，状态保持 `NOT_STARTED`，不得启动 confirmation。

实验验证的证据链固定为：

```text
状态适应建模 → 候选评分 → 上界筛除 → 盲选动作
→ 获取候选观测 → 统一重反演 → 真实目标收益与端到端成本
```

不把论文写作、文献新颖性判断或旧诊断审计当作实验完成条件。

## 2. 首要实验顺序

执行顺序是 `E0 → E1 → E2/E3 → E4/E5 → 聚合审计`。

- **E0** 先证明实现、输入权限和筛除逻辑正确。
- **E1** 是第一真实科学门：验证高分候选是否在真实 query+refit 后改善目标，而不是只验证矩阵恒等式。
- 只有 E1 出现稳定、可解释的实际收益，才进入 E2/E3 机制实验。
- E4 工程扩展与 E5 计算效率最后执行，避免在排序无效时扩大工作量。

开发阶段可采用方案建议的流程规模：4 个合格 checkpoint × 6 个候选 × 每候选 2 个独立噪声副本，最多 48 次后续重反演。该规模只用于流程和趋势检查，不构成最终统计或 confirmation。

## 3. 实验隔离和数据权限

1. 记录新 ZIP SHA256 `09745BC5B254B49184774260E905CA7B88DE8F1B6BF32BB36993CD0152A285DD`、manifest、方案文件哈希、基线 commit、当前 git commit、硬件和工作树状态。
2. 新代码、配置、raw outputs 和 evidence 分别放入 `src/saeps/active_design/`、`configs/active_design_v2/`、`outputs/runs/active_design_v2/` 和 `docs/evidence/active_design_v2/`。
3. `world_id` 表示一套物理参数、nuisance 和观测噪声 realization。方法在同一 world 共享初始数据和噪声；噪声按 `world_id × action_id × replicate_id` 固定。
4. 隐藏真值、未购买候选标签、真值 FIM/profile 只能由数据生成器和离线评价器使用。selector 不得读取 `y_a`、测试真值或答案标签。
5. 物理 plug-in FIM 可使用当前估计值，但作为独立具名基线，必须计入其前向求解成本，不能进入 SAEPS 主评分。
6. 新观测增加数据项，不得以新的样本总数重缩放旧数据；物理残差使用固定域求积权重；恒为零约束行不得改变非零数据项权重。

## 4. 需先实现并验证的局部模型

固定 checkpoint、旧权重、残差尺度和状态惩罚 `Gamma_z`，令 `z=(theta,nu)`，`xi=log(p/p_ref)`：

\[
A=\partial\bar r/\partial z,\quad B=\partial\bar r/\partial\xi,
\]
\[
M=A^TA+\Gamma_z,\quad Z=M^{-1}A^TB,\quad F=B^TB-B^TAZ.
\]

候选噪声白化导数为 `C_a`、`D_a`，并定义：

\[
E_a=D_a-C_aZ,\quad S_a=I+C_aM^{-1}C_a^T,
\quad \Delta_a=E_a^TS_a^{-1}E_a.
\]

只用线性求解，不显式形成逆矩阵。必须有 explicit、matrix-free/JVP-VJP 和直接重消元三条路径的数值一致性，以及白化、相关噪声条件化、重复 PDE 点权重和候选标签隔离测试。

`Gamma_z` 中的网络数值阻尼与物理 nuisance 真实先验分开；没有真实先验的 nuisance 不得凭空增加先验精度。`M` 不可解时记录 solver/numerical failure，不用正则化悄悄制造可辨识性。`F`、`Delta_a` 是局部 GN 对象，不是 Fisher、后验精度或 Bayesian information gain。

## 5. 主评分和上界筛除

每个实验任务先固定目标 `g(xi)` 和目标尺度 `W_g`。例如 E3 使用 `log(k)-log(C)` 或完整 `[log(k),log(C)]`。令 `L=W_g ∂g/∂xi`、`K=F+epsilon I`：

\[
V(F)=\operatorname{tr}(LK^{-1}L^T),\qquad
U(a)=\frac{V(F)-V(F+\Delta_a)}{c(a\mid D_r)}.
\]

`epsilon I` 是设计正则，不是观测信息；`U` 是局部目标设计代理，不是真实 MSE 或校准后验。不得先删除 null 子空间后声称全参数设计。

利用 `S_a >= I` 得到：

\[
0\preceq\Delta_a\preceq E_a^TE_a,qquad
0\le U(a)\le \overline U(a),
\]

其中 `U_upper` 用 `E_a^T E_a` 替换 `Delta_a`。每轮严格按以下流程执行：

1. 共同求解 `Z`，构造 `F,K,L`；
2. 对全部可行候选计算便宜 `U_upper`，固定降序和候选 ID 并列规则；
3. 对仍可能获胜的候选计算精确 `U`，更新最佳值；
4. 剩余上界低于当前最佳时停止，否则继续精算；
5. 读取真实 `y_a` 前锁定 selected action、cost 和 model hash；
6. 追加数据、统一预算重反演，再刷新下一轮模型。

筛除只保证固定局部模型、精确算术下与穷举选择一致，不保证全局预算最优、实际误差下降或严格浮点认证。必须记录近并列回退、最坏情况全精算、所有候选导数、求解次数、排序、预条件、缓存、wall time 和内存。

## 6. E0：代数、完整目标和权限验证

**输入：** tiny/实际 residual 的开发 checkpoint、固定候选池、固定 `Gamma_z`/`epsilon`。

**验证：**

- `Delta_a` 与直接新增行重消元一致；
- explicit 与 matrix-free/JVP-VJP 一致；
- `Delta_a` 对称化后的特征值满足预设数值容差；
- 独立/相关噪声白化正确；
- 重复 PDE 点只分摊求积权重，不改变完整目标；
- selector 在读取 `y_a` 之前完成并记录动作；
- 上界筛除与全候选精算同选，且保留回退记录。

E0 通过只说明工程实现对应定义，不能写成 PINN 主动反演效果。

## 7. E1：候选排序与真实重反演

这是第一优先级。固定 4 个 checkpoint、6 个候选、目标和预算；每个候选由独立评价器生成 2 个噪声副本。对每个 world：

1. 用相同初始数据运行 selector，不能读取候选标签；
2. 记录全部候选 `U`、`U_upper`、selected action 和计算成本；
3. 追加被选观测，按相同 optimizer/stopping/re-fit budget 重反演；
4. 评价目标误差变化、预测 `U` 与实际收益的 rank correlation、top-action regret；
5. 保留未选候选的离线评价，用于验证而不回流选择器。

实际收益定义为：

\[
\Delta_{real}(a)=E_g^{before}-E_g^{after\ query+refit}.
\]

如果“矩阵算得正确但排序与真实收益长期无关”，将 E1 记为科学失败，停止扩大主动实验，不调参挽救。

## 8. E2/E3：机制验证

### E2：未知初始幅度与时间信息

B4→B5 同时提供同快照的更多空间点和不同时间候选，验证是否购买真正解除初始幅度—`k` 补偿的时间信息。主指标为 `k` 个体误差—预算、动作时间分布和独立 profile；B1 已知幅度作为正面对照。同快照加密不能替代时间信息。历史时刻只能称离线 pool-based 对照，在线版本不得回购过去时间；重启实验记录重启成本和 nuisance 是否共享。

### E3：混合测量与目标切换

B3→B6 在同一 world、checkpoint、候选池和噪声下比较：扩散率目标 `log(k)-log(C)` 与完整目标 `[log(k),log(C)]`。温度成本 1、热流成本 2 是归一化实验设定，并加同成本对照；不得硬编码热流永远第一。只有温度候选时共同尺度不可解除，保留为负对照。

## 9. E4/E5：扩展和效率

E4 仅在 E1/E2/E3 通过后执行一个二维各向异性非稳态导热案例。使用至少两个独立模态、独立有限差分/有限体积生成器和同一个高精度物理逆求解器重放各方法选择的观测集合；数值案例不能称实验室验证。

E5 在相同 checkpoint、目标、阻尼、候选池和费用下比较全候选精算与上界筛除，候选池 64/256/1024。保留四项消融：不处理 nuisance、去掉 `S_a` 使用 `E_a^T E_a`、目标无关评分、关闭筛除。阻尼和设计正则只做有限敏感性，不进行大规模扫描。

## 10. 强基线、公平性和指标

主比较至少包括 random/space-filling、predictive uncertainty（含 ensemble 成本）、nuisance-aware physical plug-in FIM、PIED-MoTE/FIST 的明确序贯适配、SAEPS 全精算和 SAEPS 上界筛除。所有方法共享初始数据、候选池、world、噪声、预算和重反演预算；不能限制对手更新而允许 SAEPS 更新；不能故意让物理 FIM 逐候选重解 PDE 来制造提速。

主指标为：

\[
E_g(b)=\frac{1}{\dim g}\|W_g(g(\hat\xi_b)-g(\xi^\star))\|^2,
\]

并报告误差—累计测量成本曲线、AUBC、固定预算终点误差、达标比例、`Delta_real`、rank correlation、regret、`C_measurement` 与 `C_computation`。未达标轨迹保留。统计按独立 world 配对重采样；网络初始化属于嵌套重复。

## 11. 运行状态与停止条件

仓库 run 的最终 `status` 仍只能是 `PASS`、`CHECKPOINT_INVALID`、`PROFILE_FAILURE`、`SOLVER_FAILURE`、`NUMERICAL_FAILURE`。主动过程的 `termination_reason` 单独记录 `BUDGET_EXHAUSTED`、`NO_FEASIBLE_ACTION`、`ACQUISITION_UNRESOLVED`、`TARGET_NOT_IDENTIFIED` 等原因，不新造 status 绕过聚合。

每个 run 至少记录 world/action/replicate、target 定义、候选 hash、先选后读顺序、`Gamma_z`/`epsilon`、`F/Delta/U/U_upper`、solve/JVP/VJP 计数、timings、measurement/computation/refit cost、误差和失败原因。真值字段标为 `validation_only`。

不可辨识本身不是禁止选点的理由；只有 checkpoint 无效、solver/数值失败、输入泄漏、预算耗尽、无可行动作，或 E1 长期不能改善真实目标，才停止对应轨迹。profile 尚未实现应如实标记范围缺失，不能伪装通过。

## 12. E1 开发门与最终裁决

E1 开发门至少要求 E0 通过、selector 无输入泄漏、强基线公平可运行、失败记录完整，并在至少两个机制任务中出现稳定可解释的真实收益（目标误差、达标成本或相近精度下的实际计算优势）。不预设 30% 或 10× 等结果阈值；阈值必须在新协议锁定前确定。

若 SAEPS 与 physical FIM 精度接近但更便宜，可收窄为计算优势；若二者均无优势，停止扩展。正式科学状态只能为 `SUPPORTED`、`PARTIALLY_SUPPORTED` 或 `NOT_SUPPORTED`。方案包现有 24 组矩阵、12 组筛除同选及解析控制，只能作为 algebra/reference evidence，不能写成新的 PINN、真实测量收益、校准或提速结果。

