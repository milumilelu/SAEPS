# Codex 任务书：SAEPS 一周强化实验与方法升级

> **执行模式：先审计仓库，再实现并运行实验；不要只返回另一份计划。**
>
> **时间预算：7 天。** 短期目标是完成面向中科院二区投稿的实质性修改，同时评估“方向性二阶修正 + 可计算误差控制”能否形成进一步的方法贡献。
>
> **默认交付：** 可复现代码、冻结协议、完整逐样本结果、数学与数值单元测试、图表、失败分析、论文修改建议。不要承诺结果一定改善，不要承诺期刊录用。
>
> **仓库：** `https://github.com/milumilelu/SAEPS`
>
> **本文性质：** 作者拟执行的实验协议，不是已经完成的实验报告。文中所有新方法效果、新阈值、新运行预算均为待验证或待冻结的设计。

---

## 0. 给执行代理的第一条指令

你需要在保留历史证据的前提下，完成下面的工作：

1. 查清当前仓库的分支、协议、原始结果、检查点、模型与求导入口，找到可复用的真实文件，不凭分支名猜测结果。
2. 首先复用现稿报告的 21 个已重构标量中心，验证方向性二阶修正及误差恒等式；这一阶段原则上不重新训练。
3. 实现矩阵无关版本，以及有明确适用条件的后验曲率误差控制。
4. 补充独立两参数验证和宽度 32 的准确性验证；预算允许时再做宽度 64。
5. 把计算出的状态响应用于 profile 重优化初始化，并完成一个小型、受保护的局部参数更新实验，使方法不再只有事后诊断用途。
6. 保留所有失败、未完成和不支持预期的结果，最后判断哪些结论能进入论文。

**首次运行至少完成：仓库审计、数学核心实现、合成单元测试，以及可获得历史中心上的 E0。** 不要在没有检查仓库的情况下要求作者先解释所有分支。只有缺少无法自动恢复的文件、权限或计算资源时才提出具体问题。

如果无法在当前会话持续完成全部实验，必须提交已执行成果和可恢复命令，准确说明哪些任务尚未执行；不得声称后台会自动继续。

---

## 1. 依据、已有证据及核查边界

依据是作者提供的 `manuscript3.pdf` 和本任务所指定的仓库。下表是**现稿报告的事实**，不是本任务已重新核验的仓库结果。

| 现稿证据 | 来源位置 | 本轮用途 |
|---|---|---|
| Burgers 原队列 15 次计划、12 个有效中心；Allen–Cahn 10 次计划、9 个有效中心 | 主文 Table 2，pp. 12–13 | 21 个中心用于开发和回顾性验证，不当作新独立测试集 |
| 重构后归档完整 exact/GN Hessian blocks | §3.3、Appendix I，pp. 12–13、29 | E0 的优先数据来源；文件是否真的可访问仍须核实 |
| 两参数实验 8/10 有效，未达到原协议的 9/10 可用率目标 | Appendix E，p. 26 | 旧结果保留；另建新队列，不能追加种子改变旧结论 |
| width 32 未取得有效驻点 | Appendix D，p. 25 | 设置独立的驻点精化试验和固定次数的规模验证 |
| 非线性 profile 仅 1/5 通过原一致性条件 | Appendix F，pp. 26–27 | 分析数值误差来源；另建修订协议，不覆盖旧结果 |
| 100001 状态参数的结果验证计算可行性，而非该规模准确性 | §4.5、§5.2、Appendix G | 保留，不继续追求更大的参数量 |
| Appendix I 的全局扰动界条件在 21 个中心均不满足 | Appendix I，p. 29 | 对比新的方向性缺陷表达式，但不保证新界一定实用 |

现稿列出的历史追溯点：

- 投稿快照：`jcp-submission-v1`，报告对应 `d5a231d857e4`。
- 主结果：`cf76ffe`。
- 精确分解：`39343bc`。
- variable-projection / paper-facing statistics：`c868127`。
- whitening sensitivity：`0428a1f`。

这些引用必须通过 `git show`、清单或文件内容实际核对。缺失时写入审计报告，不能假定当前工作区已经包含它们。

本任务**没有预先确认所有分支的最新内容**。尤其不能假定 `codex/v6-phase15-protocol` 已经实现本方案，也不能假定版本号最大的分支最好。

---

## 2. 执行化澄清：以下规则优先于早期口头方案中的简写

### 2.1 数值公式必须支持不精确线性求解

早期公式 `F_SO = F_SAEPS + V^T S V` 中，`F_SAEPS` 若用简化 Schur 形式计算，隐含 GN 状态线性系统已解准。本任务要求对近似解使用完整二次型，避免把求解残差误当成方法误差。

### 2.2 二阶修正不保证逐点优于 SAEPS

在状态块正定时，二阶方向二次型是 exact reduced Hessian 的 Loewner 上界；这**不等于**它一定比 GN 约化曲率更接近参考。原 GN 误差可能存在抵消，必须实测。

### 2.3 误差上界只约束所定义局部曲率的计算误差

不得把曲率误差上界称为“真实参数正确性证书”“置信区间覆盖保证”或“全局可辨识性保证”。

普通双精度 `eigvalsh` 的最小特征值是数值结果，不自动构成严格数学下界。普通 Lanczos 最小 Ritz 值也不能直接当作最小特征值下界。

### 2.4 固定尝试数，不固定成功数

所有新队列写成“计划运行 N 次，报告有效/计划”，不得写成“跑到 3 个有效中心为止”。旧失败样本不能替换；新队列失败也不能追加好种子补齐。

### 2.5 固定目标函数、权重、阻尼与锚点

同一次比较必须使用相同残差、权重、数据、参数坐标、阻尼和正则化锚点。不能为某方法单独增大阻尼使其通过，也不能在 HVP 或 profile 扰动中重新计算阻尼而不计其导数。

### 2.6 “不再只诊断”需要实际使用结果

仅增加二阶项仍然是事后曲率计算。必须至少尝试：

- 使用状态响应预测来初始化参数变化后的状态重优化；
- 使用约化曲率完成一次受保护的参数更新。

若第二项未完成或没有收益，只能声称完成了第一项，不能写成提高了反演精度。

---

## 3. 仓库审计与安全操作

### 3.1 不允许破坏历史记录

- 先检查 `git status`，保留作者尚未提交的修改；不执行破坏性 reset、clean、删除或强制切分支。
- 优先用 `git show` / `git ls-tree` 检查其他分支，必要时用独立 worktree。
- 在干净、经审计的基线上建立新的本地工作分支，例如 `research/saeps-so-week1`；存在同名分支时先检查，不覆盖。
- 不自动 push，不覆盖 release/tag，不修改原始 CSV/JSON/检查点。
- 可以生成本地协议快照和提交；若环境缺少 Git 身份，不修改全局配置，可用文件 SHA-256 记录冻结状态。
- 不把大体积检查点、环境缓存或凭据自动加入 Git。
- 若允许联网，可获取远程分支和 tags；若不允许，说明审计仅覆盖本地可见引用。

### 3.2 至少检查这些分支或其等价可达提交

```text
main
posthoc/exact-fixed-state-decomposition-v1
posthoc/exact-fixed-state-decomposition-v2
posthoc/exact-fixed-state-decomposition-v3
posthoc/variable-projection-baseline-v1
posthoc/whitening-sensitivity-v1
release/jcp-submission-v1
release/public-release-report-v1
codex/public-jcp-release
codex/v6-phase15-protocol
```

分支不存在、已合并或不可访问都应记录，不得伪造路径。

### 3.3 生成 `REPO_AUDIT.md` 和 `artifact_manifest.csv`

对每组可用证据记录：

```text
experiment_id, branch_or_ref, commit, actual_path, sha256,
protocol_path, checkpoint_path, raw_result_path,
pde, parameterization, architecture, dtype,
planned_n, available_n, historical_valid_n,
status, reuse_decision, reason
```

必须回答：

1. 哪些历史文件是 binding / frozen 主结果，哪些是 post-hoc、开发或 aborted？
2. 21 个中心的矩阵、原始状态、数据、梯度能否分别恢复？
3. 原始 coupled 实验具体是哪组 PDE/参数？使用什么尺度与 whitening？
4. 原始 residual 是 sum 还是 mean？是否含块归一化？W 是否随参数或迭代变化？
5. 自动微分的参数打包顺序是什么？物理参数是否经过 log 变换？
6. 原 stationarity / SPD / solver-validity 判断的精确定义在哪个函数？
7. V6 是否存在已经实现且有证据支持的重合功能？若有，优先复用或提取，不重复开发。
8. 现有 seed 清单、训练成本、可用 CPU/GPU、内存和自动微分框架版本是什么？

**不要将“21 个中心原稿称已归档”理解成一定能直接读取全部文件。** 只有矩阵而没有检查点时，E0 可先做；HVP 和梯度审计标记为等待恢复。确需重构时，单独计入成本并记录与原矩阵的重现误差。

---

## 4. 数学规格：实现必须以本节为准

### 4.1 统一记号

设固定权重的残差为 `rbar(theta, lambda)`，未附加状态锚定项的目标为

\[
\ell(\theta,\lambda)=\tfrac12\|\bar r(\theta,\lambda)\|_2^2.
\]

状态维数为 `n`，物理参数维数为 `p`。所有导数必须来自**同一个标量目标与同一组变量**：

\[
G=J^T J,\qquad H=\nabla^2\ell,\qquad S=H-G.
\]

在当前局部实验中，使用固定的 `gamma > 0`：

\[
M=G_{\theta\theta}+\gamma I,\quad B_G=G_{\theta\lambda},\quad C_G=G_{\lambda\lambda},
\]

\[
A=H_{\theta\theta}+\gamma I,\quad B=H_{\theta\lambda},\quad C=H_{\lambda\lambda}.
\]

不要把 `gamma I` 重复加入 G/H，又在公式中再次加入。建议 H、G 只对应 `ell`，锚定项单独处理。

若实际代码含其他正则项，先推导其应属的 Hessian/残差块，再纳入；禁止为了符合这些公式而静默丢弃目标函数项。

### 4.2 原 SAEPS 与完整 GN 二次型

GN 状态响应解：

\[
Z_G=M^{-1}B_G,\qquad \delta\theta_{\rm pred}=-Z_G\,\delta\lambda.
\]

精确求解时：

\[
F_G=C_G-B_G^T Z_G.
\]

对任意实际算得的近似 `Z`，使用完整二次型：

\[
Q_G(Z)=C_G-B_G^TZ-Z^TB_G+Z^TMZ.
\]

对应 GN 求解残差 `R_G = B_G - M Z`。用于测试的恒等式为

\[
Q_G(Z)-F_G=R_G^T M^{-1}R_G.
\]

因此不要使用尚未解准的 `C_G - B_G.T @ Z` 代替完整二次型。

### 4.3 方向性二阶修正

定义

\[
V=\begin{bmatrix}-Z\\I_p\end{bmatrix}.
\]

本任务的二阶方向近似为

\[
\boxed{F_{SO}(Z)=Q_G(Z)+V^T S V.}
\]

它等价于

\[
\boxed{F_{SO}(Z)=C-B^TZ-Z^TB+Z^TAZ.}
\]

在 `Z = Z_G` 时，才恢复早期讨论中的简写

\[
F_{SO}=F_{SAEPS}+V^TSV.
\]

### 4.4 精确约化参考与方向性误差恒等式

当 `A` 可逆时定义代数 Schur 参考：

\[
F_* = C-B^T A^{-1}B.
\]

定义状态响应缺陷

\[
D=B-AZ.
\]

对任意 Z，恒等式为

\[
\boxed{F_{SO}(Z)-F_*=D^T A^{-1}D.}
\]

只有在 `M Z = B_G` 解准时，才能进一步简写

\[
D=S_{\theta\lambda}-S_{\theta\theta}Z.
\]

近似 GN 解情况下应使用 `D=B-AZ`，或补上 `R_G`，不能丢弃 GN 求解残差。

若 `A ≻ 0`，则

\[
F_{SO}(Z)-F_*\succeq0.
\]

**适用范围：** 这个代数恒等式不要求联合驻点；但将 `F_*` 解释成局部重新优化 profile 的 Hessian，需要相应带锚定目标的状态驻定与局部最小条件。必须分别记录 `algebraic_schur_valid` 和 `local_profile_valid`。

**不能推出：** `F_SO <= F_raw`、SO 总比 GN 准、Hessian 本身正定、真实参数正确。不要把原 SAEPS 的 Loewner 结论直接转移给 SO。

### 4.5 不精确二阶升级的正确公式

若近似求解

\[
A W\approx D,
\]

更新

\[
Z_+=Z+W,\qquad D_+=D-AW.
\]

新的方向二次型应直接重算，或用

\[
\boxed{F_{SO}(Z_+)=F_{SO}(Z)-D^TW-W^TD+W^TAW.}
\]

只有 W 真正解准时，才能简化为 `F_SO - D.T @ W`。

不得对不精确 W 直接使用这个简化式并宣称保持上界。也不要未经证明宣称逐列独立 CG 的每次矩阵更新都具有 Loewner 单调性。

---

## 5. 可计算误差控制与矩阵无关实现

### 5.1 条件性误差上界

若获得有效下界 `mu > 0`，满足 `A ⪰ mu I`，则

\[
0\preceq F_{SO}-F_*\preceq U_{mat}:=D^TD/\mu,
\]

\[
\|F_{SO}-F_*\|_2\le U:=\|D\|_2^2/\mu.
\]

`U` 是绝对误差界。若 `f = ||F_SO||_2 > U`，则还可推出

\[
\frac{\|F_{SO}-F_*\|_2}{\|F_*\|_2}\le\frac{U}{f-U}.
\]

要求真实相对误差不超过 `tau` 的充分条件是

\[
U\le\frac{\tau}{1+\tau}\,f.
\]

`U/(f+epsilon)` 只能叫输出尺度归一化指标，不能不加说明地称为对未知参考的真实相对误差界。`f <= U` 时，返回“无有限相对误差保证”，不得靠 epsilon 把它包装成通过。

### 5.2 三类边界来源必须分开

每条记录包含 `bound_status` 与 `mu_source`：

| 状态 | 条件 | 允许的表述 |
|---|---|---|
| `verified_bound` | 有经验证、含浮点误差控制的正下界，例如可信的区间方法；实现细节可审计 | 在已声明矩阵/目标及假设下的验证型曲率误差界 |
| `numerical_bound_estimate` | 普通 dense eigensolve，附对称性、特征残差、正交性和数值余量检查 | 双精度数值误差界估计；不得称严格证书 |
| `indicator_only` | 仅有未保证的谱估计或无可靠正下界 | 缺陷/残差指示量，不能作认证停止依据 |

默认一周内完成第二类，不强行引入新的区间计算基础设施。严格验证属于可选增强。

普通 Lanczos 最小 Ritz 值不得填入 `verified_mu`。若尝试 Gershgorin 下界，负值意味着该方法没有提供正下界，不意味着 A 必然非正定；含浮点舍入保证的实现才能列入 `verified_bound`。

无法分辨 SPD 或下界接近舍入误差时，记为 `spd_unresolved` / `mu_unresolved`。不要通过裁剪最小特征值到正数伪造有效下界。

### 5.3 两参数的界与误差必须用同一坐标

复用原稿 whitening：`B2 = L L^T`，令 `T=L^{-T}`，则

\[
\widehat F=T^T F T=L^{-1}FL^{-T}.
\]

相同坐标中的缺陷是 `D T`，误差界应为

\[
\widehat U=\|DT\|_2^2/\mu.
\]

不能将物理坐标中的界直接与 whitened error 比较。所有方法、参考、方向角及阈值使用相同且预先规定的变换。

### 5.4 矩阵无关路径

不构造完整 J、H、S、A，不构造三阶张量。使用仓库实际框架的 JVP/VJP/HVP。

对 `V=[-Z;I]` 的 p 列计算联合 `H V`，则

\[
D=(HV)_\theta-\gamma Z,
\]

\[
F_{SO}=V^T(HV)+\gamma Z^TZ.
\]

GN 完整二次型可由

\[
Q_G(Z)=(JV)^T(JV)+\gamma Z^TZ
\]

计算。这样无需显式形成 `S=H-G`。

这里“p 列 HVP”只描述 SO 方向计算，不包括 GN 求解、谱下界估计、二阶升级、训练或 profile 重优化。所有实际调用都要计数，不能把完整流程宣称为只花 p 个 HVP。

### 5.5 自适应流程

```text
输入：同一目标与中心、固定 gamma、目标容差、计算预算
1. 用原矩阵无关 GN 求解器求 Z_G，验证求解残差。
2. 用完整二次型计算 Q_G；计算 F_SO 和 D。
3. 根据 mu 的来源给出验证型界、数值界估计或 indicator-only 状态。
4. 满足所声明层级的容差 -> 返回结果与状态。
5. 不满足 -> 在剩余预算内解 A W ≈ D，更新 Z、D 和完整二次型。
6. 在预设迭代检查点重复计算界/估计；不能用 oracle 真误差决定何时停。
7. 达到预算仍未满足 -> 返回 tolerance_not_met；可以输出近似，但不得标成已达标。
8. 发现非正定/无法确认适用条件 -> 返回相应失败状态；不临时改变目标 gamma。
```

matrix-free 生产路径中的停止判据不能读取 dense reference。dense reference 只由独立验证模块生成并在事后评估。

若下界只来自完整 A 的 eigensolve，该版本应标为 `dense-assisted`，其谱计算时间与内存必须计入；不能据此宣称整个误差控制流程矩阵无关。

---

## 6. 单元测试：不通过则禁止启动正式新队列

### T1. 合成小矩阵代数

覆盖 `p=1,2,3`；构造 SPD A、SPD M，并允许 reduced Hessian 不定。随机 Z 不必是精确 GN 解。

验证：

- 两种 `F_SO` 表达式一致。
- `Q_G - F_G = R_G^T M^{-1}R_G`。
- `F_SO - F_* = D^T A^{-1}D`。
- 任意不精确 W 的更新公式正确。
- `D.T @ D / mu - (F_SO-F_*)` 为 PSD，mu 使用已知可验证的构造下界。
- whitening 后界和误差保持一致。

合成良态测试的归一化代数误差目标：`<= 1e-10`。不得直接求逆，使用 solve。病态压力测试允许报告舍入误差与不可分辨状态，不能无条件套这个阈值。

### T2. 显式与自动微分一致性

在小网络比较 JVP、VJP、HVP 与显式 J/H 的结果。检查变量顺序、log 参数、残差权重、正则化是否一致。归一化算子误差目标：`<= 1e-8`。

有限差分梯度检查使用多步长平台而不是单一极小步长；不得用同一错误实现生成“独立参考”。

### T3. 原标量模型的参数梯度恒等式

若审计确认固定 theta 下 `rbar=a(theta)+exp(lambda)b(theta)`，权重固定且无附加参数正则项，则检查

\[
H_{\lambda\lambda}-G_{\lambda\lambda}=\partial_\lambda\ell.
\]

同时记录状态与参数梯度的绝对值、原协议归一化值、相对参考曲率的尺度。

若模型或实际目标不符合此前提，解释原因，不强制套用。若符合却测试失败，先排查实现或目标不一致，不能继续写“GN truncation 主导/次要”的机制结论。

参数坐标检查也必须包含非驻点 Hessian 变换的梯度项。对 `mu=exp(lambda)`：

\[
H_{\lambda\lambda}=\mu^2H_{\mu\mu}+\mu\,g_\mu.
\]

不得在参数未驻定时只比较 `mu^2 H_mu_mu`。

### T4. 错误路径

至少测试：A 不正定、mu 未解析、GN 未收敛、二阶升级超预算、NaN、极小参考曲率、重特征值、历史文件缺失。输出必须为明确状态和原因，不得自动替换数据或返回伪造零误差。

---

## 7. 实验总表与默认工作量

| 编号 | 实验 | 默认预算 | 优先级 |
|---|---|---:|---|
| E0 | 历史 21 中心：数学审计、SO、界与缺陷 | 21 个原有效中心；不新增训练 | P0 |
| E1 | HVP 一致性、误差控制、精度—成本曲线 | 6 个开发中心；多个容差复用 | P0 |
| E2 | 新独立两参数队列 | 12 次计划训练 | P1 |
| E3a | width 32 准确性验证 | 2 PDE × 3 次 = 6 次计划训练 | P1 |
| E3b | width 64 准确性验证 | 2 PDE × 3 次 = 6 次计划训练 | 可选；冻结前决定 |
| E4 | profile 与 GN 状态预测初始化 | 4 个中心 × 2 方向 × 3 步长 × 2 初始化 = 48 次内层求解 | P1 |
| E5 | 受保护的一步参数更新 | 4 中心 × 2 偏移 × 5 方法；每方法至多 2 次候选评估 | P1，小型功能验证 |

新正式训练默认 18 次，含 E3b 则 24 次；不含最多 4 次开发期优化器试验。E4/E5 默认复用可追溯中心，不新增大规模训练。

**这不是保证一周完成的运行时预测。** 实际预算应由 Day 1–2 的测量决定，冻结后不得根据实验好坏随意增删队列。

---

## 8. E0：历史中心上的开发与方法筛选

### 8.1 输入与参考

优先读取真实归档矩阵。必须先复现原 `F_raw`、`F_SAEPS`、`F_*` 的报告值；历史摘要不足以代替矩阵。

独立参考使用 `C - B.T @ solve(A,B)`，不得只通过 SO 缺陷恒等式反向定义 oracle，否则验证会成为循环论证。

### 8.2 每中心输出

```text
F_raw, F_G_reference, Q_G_actual, F_SO, F_star
GN_normal_residual, D_norm, lambda_min_A_numeric
algebra_identity_error, original_reproduction_error
absolute_error_raw, absolute_error_GN, absolute_error_SO
relative_error_raw, relative_error_GN, relative_error_SO
SO_improvement_factor, SO_improved
mu_value, mu_source, bound_status, U_absolute, U_relative_if_available
bound_effectivity, state_gradient, parameter_gradient
historical_valid, algebraic_schur_valid, local_profile_valid
```

`bound_effectivity = U / true_absolute_error`；当真误差低于数值分辨率时记为 `not_resolved`，不能用任意 epsilon 得出漂亮效能系数。

### 8.3 开发期决策规则

以下是资源分配规则，不是统计显著性证明：

- 若 SO 相对 GN 的**逐中心误差改善倍数中位数 >= 2**，且至少 75% 可比较中心改善，则继续以 SO 为主方法候选。
- 若 SO 改善有限，但缺陷升级在相同精度下有成本优势，则继续研究 adaptive response refinement；不得宣称 SO 单步近似稳定更好。
- 若界普遍过松，仍运行有限次残差修正，看新缺陷能否下降；不能仅通过放大 mu 改善界。
- 若数学恒等式、历史复现或目标一致性失败，暂停新增训练，先修错误。
- 若方法无实际优势，保留全部负结果，转向证据补齐与局部状态预测用途。

21 个历史中心是开发资料。基于它们选择方法后，不能再称它们为独立确认性证据。

---

## 9. E1：矩阵无关一致性与误差控制的实际代价

### 9.1 开发中心选择

在 E0 中按预先规定的排序规则，各 PDE 选 3 个中心，覆盖低、中、高 GN 误差；并记录其条件数。它们明确标为开发集，不以“最好看”的中心作为新测试集。

### 9.2 比较方法

```text
RAW                 冻结状态 GN 曲率
SAEPS-GN            原有限阻尼约化 GN，使用验证过的实际求解器
SO                   方向性二阶二次型
SO-ADAPT             按缺陷/界控制的二阶状态响应升级
REDUCED-NEWTON-REF    独立 full-Hessian / high-accuracy Schur 参考
```

匹配目标与正则化的经典 reduced GN 与 SAEPS 代数等价时，作为**实现一致性基线**报告，不包装成另一个被击败的方法。

### 9.3 容差与预算

默认目标相对容差：`0.10, 0.05, 0.01`。二阶求解默认每 RHS 最多 100 次 A 乘法，在 `0,1,2,4,8,16,32,64,100` 次附近记录误差和代价。

算法停止只使用其允许获得的界或数值估计。真误差在结果落盘后由 oracle 模块计算。

报告：

- 达到目标的比例、未达标比例、无正下界比例；分母同时给计划数和参考有效数。
- 验证型达标与数值估计达标分开。
- U 对真实绝对误差的包络、效能系数和迭代收紧情况。
- 达到相同真误差的耗时、JVP/VJP/HVP 次数、峰值内存。
- GN 初始化、SO、谱估计、升级、参考构造的分项成本与总成本。

只有给算法额外输入 oracle 特征值才能完成的实验必须标记 `oracle_spectral_assistance`，不能作为可部署方法的效率结论。

---

## 10. E2：独立两参数队列

### 10.1 协议

复用仓库中已经存在的 coupled 问题，不自行换成未经核实的新 PDE。新队列固定 12 次尝试，不替换失败种子。

先用开发数据确定优化与求解方案，再冻结新队列。新协议不得悄悄修改原历史 8/10 队列的判定或分母。

比较 RAW、SAEPS-GN、SO、SO-ADAPT 与同目标 exact reference。默认 gamma 规则和 whitening 复用原 coupled 协议；不要把标量 alpha 擅自套到 coupled 上。

### 10.2 指标

1. 原稿的 whitened Frobenius error，以及相同坐标的绝对矩阵误差。
2. 最小曲率特征值误差。
3. 同一 whitened 坐标中最小曲率方向的夹角：

\[
\arccos\bigl(|v^Tv_*|/(\|v\|\|v_*\|)\bigr).
\]

4. 原 GN 的 generalized retained eigenvalues。
5. SO/SO-ADAPT 的界、真实误差与计算量。
6. 每个有效性条件及失败原因。

若 exact eigen-gap 太小，单一特征向量方向不稳定；默认归一化 gap `<1e-3` 时将单方向角标为不可解释，可选报告子空间角。这个规则必须在看新结果前冻结。

若参考 Hessian 不正定，称“最小曲率方向”，不能直接称“可靠性最弱方向”。SO 的 generalized eigenvalues 不必处于 `[0,1]`，不套用原 GN 的保留比例解释。

12 次是本周资源预算，不代表预先具备某种统计功效，也不保证可给出确认性结论。

---

## 11. E3：width 32/64 的准确性过渡验证

### 11.1 目的与命名

对原单隐层 `2-w-1` 网络，若结构核实不变，状态维数是 `4w+1`：width 32/64 分别为 129/257。这属于**比原主实验更宽的过渡规模**，不得宣传成真正的大规模准确性验证。

### 11.2 开发期驻点精化

最多 4 次开发运行，总计覆盖两 PDE 的 width 32。复用现有 Adam/L-BFGS，然后试验一个有固定预算的精化流程：

```text
原训练 -> L-BFGS restart -> 必要时受保护 Newton-CG / trust-region polish
```

不得新增五六种优化器大规模调参。精化采用训练目标而非临时更改后的目标。新中心与旧中心具有不同 ID，不能覆盖历史结果。

分别记录：

```text
state_stationary
joint_stationary
historical_primary_gate_passed
regularized_state_block_spd
local_profile_valid
```

当某中心仅满足状态驻定但不满足原联合 gate 时，可以进入单独标记的 profile/代数探索，不能当作“原严格 gate 已通过”。

### 11.3 冻结测试

- E3a：Burgers、Allen–Cahn，各 width 32 × 3 个新种子，共 6 次计划。
- E3b：同样配置的 width 64，共 6 次；是否启用在正式测试前冻结。
- 每个任务固定训练、restart、polish 的最大预算。
- 所有方法在相同中心比较。某方法失败仍保留该中心，不通过全方法共同过滤隐藏失败率。

沿用或明确继承原始有效性定义，不降低门槛以凑成功数。

若宽网络精化仍失败，按预算停止并报告。不要换 seed 跑到有成功案例。保留现有 100k 算法可行性结果，但不扩大其准确性结论。

---

## 12. E4：profile 收敛与状态响应的实际用途

### 12.1 中心和用途

默认在旧标量有效中心中，按 seed 排序每 PDE 取前 2 个，共 4 个；选择规则在运行前冻结，不挑“最好收敛”的中心。

必要时先执行固定预算的中心精化，生成新的子记录并保留父中心。无法得到合格中心时该位置记失败，不替换。

这是小型功能/机制验证，因中心来自开发资料，不称独立泛化证据。预算允许时，可按冻结规则在 E3a 的每 PDE 第一个计划中心各复验一次；失败不能换成第二个。

### 12.2 固定 profile 目标

在合格根中心 `(theta_c,lambda_c)` 固定

\[
L_\gamma^{(c)}(\theta,\lambda)=\ell(\theta,\lambda)+\tfrac\gamma2\|\theta-\theta_c\|^2.
\]

`theta_c`、gamma、残差权重、数据和配点在整个 profile 实验中固定。局部 profile 是同一局部分支上的状态驻定解所定义的函数，不声称求得全局最小。

**gamma 必须在根中心计算一次并停止求导。** 不能在每个 `lambda_c ± h` 重算 alpha 对应的 gamma，也不能移动正则化锚点。

### 12.3 步长与初始化

默认 3 个 log 参数步长：`h0, h0/2, h0/4`。优先使用原仓库的 h0；若没有可用定义，在开发阶段固定 `h0=0.02`，不得看最终曲线后挑最佳步长。

对正负两侧，比较：

```text
BASE:       theta_init = theta_c
GN-PRED:    theta_init = theta_c - Z_G * delta_lambda
```

两种初始化使用同一求解器、容差、预算和目标。GN-PRED 的状态响应计算成本必须计入总时间，分别给单次使用和重复 profile 时的摊销结果。

可选的小型增强是比较经缺陷修正的 `Z_plus` 初始化，但不是默认必做项，不能用 exact oracle 方向冒充 SO 本身已有的状态预测。

### 12.4 记录与解释

保存目标值、状态梯度、迭代/函数评估次数、总时间、最终状态差异、分支一致性迹象，以及

\[
H_{FD}(h)=\frac{\Phi(\lambda_c+h)-2\Phi(\lambda_c)+\Phi(\lambda_c-h)}{h^2}.
\]

根点 `Phi(lambda_c)` 也必须与相同求解精度和同一锚定目标一致。

每个 h 比较 `H_FD` 与独立 exact local Hessian；不要只选最好的一个 h。

记录更严格再优化所引起的目标变化，作为数值误差估计。其被 `h^{-2}` 放大的效应可以解释误差平台，但该估计不是无条件的全局最优误差界。

若两种初始化收敛到不同目标/局部分支，先报告不可直接比较，不把较低迭代数直接当加速。不得要求曲线一定是 U 型，也不得为形成预期图形挑数据。

---

## 13. E5：一次受保护的参数更新，回应“只做事后诊断”

### 13.1 起点必须有更新空间

复用 E4 的固定根 profile。对每个中心设

\[
\lambda_s=\lambda_c\pm\Delta,\qquad \Delta=0.05
\]

（log 坐标；如原参数坐标不同，在开发期定义等价无量纲尺度并冻结）。

固定 lambda_s，优化状态，使 **同一个 `L_gamma^(c)`** 满足状态驻定。这时要求的是带锚定总目标的状态梯度小，不能误用未加锚定的 `grad_theta ell` 判定。

不要求参数梯度小；使用非零 `g_lambda` 才能检验参数更新。起点失效则所有方法共享该起点失效记录，不为不同方法提供不同的好起点。

### 13.2 在相同目标上比较五种曲率

```text
RAW
SAEPS-GN
SO
SO-ADAPT
EXACT-REDUCED-ORACLE
```

所有方法共用相同起点、参数梯度、坐标、gamma、根锚点、信赖半径和验收规则。精确参考只作为 oracle，不提供给实用方法选择步长或停止条件。

一周内只做 one-step，不扩展成长程训练算法。

### 13.3 受保护步长

在共同尺度下计算移位后的 Newton 型步：

\[
\delta\lambda=-(\operatorname{sym}F+\beta I)^{-1}g_\lambda.
\]

采用统一规则使移位矩阵具有正的数值下界；尺度由共同的 RAW 矩阵定义，不能按方法分别手调。记录所有 shift，不隐藏负曲率。

将步限制在共同半径内，默认 `||delta_lambda|| <= 0.1`；使用最多两次候选系数 `[1.0,0.5]` 和同一 Armijo 常数 `1e-4`。两次均不接受则标为 `step_rejected`，不能无限 line search。

候选目标通过同一 profile 重优化过程评估。为隔离曲率的影响，五种方法的候选状态初始化**统一使用该起点的 GN 状态预测器**。如另比较改进状态预测器，单列消融，不混到曲率对照里。

gamma 和根锚点在起点、候选点评估中完全一致，不能每更新一次参数就换目标。

### 13.4 指标

- 实际 profile decrease：`Phi_before - Phi_after`。
- 二次模型 predicted decrease，以及 actual/predicted ratio；分母不可分辨时不报告比值。
- 步接受率、拒绝率、状态求解失败率。
- 真实参数误差变化，仅作为合成数据事后评价，不用于算法调参。
- 总耗时及函数/梯度/HVP 计数，包含曲率计算和候选状态重优化。
- 与 oracle 的步长/下降量差异。

目标下降不保证真实参数误差下降。参数估计存在偏差时，必须同时报告两者；不能只挑其中改善的一项。

默认 4 根中心 × 2 偏移 × 5 方法 = 40 次一步比较，至多 80 次候选内层求解，加 8 次公共起点求解。与 E4 的 48 次合计最多 136 次主要内层求解；另设总硬上限，防止失败样本无限重试。

这 8 个偏移起点并非 8 个完全独立实验，统计汇总以根中心为配对/分组单位。

---

## 14. 冻结协议模板

下面是**需要 Codex 根据审计生成的模板**，不是当前仓库已经存在的配置。含 `REQUIRED_FROM_AUDIT` 的字段未填齐时禁止正式新队列运行。

```yaml
project: saeps_so_week1
protocol_version: 1
mode: development_until_frozen
repository: https://github.com/milumilelu/SAEPS
source_commit: REQUIRED_FROM_AUDIT
run_root: revision_week/outputs

numerics:
  dtype: float64
  device: REQUIRED_FROM_AUDIT
  cpu_threads_per_worker: 1
  deterministic_where_supported: true
  disable_mixed_precision: true
  gamma_rule_scalar: REQUIRED_FROM_AUDIT
  gamma_rule_coupled: REQUIRED_FROM_AUDIT
  freeze_gamma_inside_derivatives_and_profiles: true
  historical_validity_function: REQUIRED_FROM_AUDIT
  history_weighting_and_normalization: REQUIRED_FROM_AUDIT
  min_eig_source_default: dense_numerical_estimate
  claim_rigorous_certificate_by_default: false

unit_tests:
  well_conditioned_algebra_rtol: 1.0e-10
  operator_parity_rtol: 1.0e-8
  fail_on_target_mismatch: true

adaptive:
  relative_tolerances: [0.10, 0.05, 0.01]
  max_A_matvecs_per_rhs: 100
  record_iterations: [0, 1, 2, 4, 8, 16, 32, 64, 100]
  use_oracle_error_to_stop: false
  report_numerical_and_verified_bounds_separately: true
  complete_quadratic_for_inexact_solves: true

cohorts:
  E0:
    role: retrospective_development
    source: original_21_reproduced_valid_centers
    allow_replacement: false
  E1:
    role: development_operator_validation
    n_centers: 6
  E2:
    role: new_frozen_coupled_validation
    planned_attempts: 12
    seed_base_candidate: 712000
  E3a:
    role: new_frozen_scalar_width32_validation
    pdes: [burgers, allen_cahn]
    widths: [32]
    attempts_per_pde_width: 3
    seed_base_candidate: 710000
  E3b:
    enabled: false
    decision_must_precede_new_test_results: true
    role: new_frozen_scalar_width64_validation
    pdes: [burgers, allen_cahn]
    widths: [64]
    attempts_per_pde_width: 3
    seed_base_candidate: 711000
  E4:
    role: functional_profile_development
    selection: first_two_original_valid_seeds_per_pde
    n_roots: 4
    h0: REQUIRED_FROM_AUDIT_OR_DEVELOPMENT
    h_multipliers: [1.0, 0.5, 0.25]
    signs: [-1, 1]
    initializations: [base, gn_predictor]
  E5:
    role: functional_one_step_development
    roots: same_as_E4
    parameter_offset: 0.05
    trust_radius: 0.1
    line_search_factors: [1.0, 0.5]
    armijo_c1: 1.0e-4
    methods: [raw, saeps_gn, so, so_adapt, exact_oracle]
    common_state_initializer: gn_predictor

training:
  base_recipe: REQUIRED_FROM_AUDIT
  polish_recipe: REQUIRED_FROM_DEVELOPMENT
  max_development_training_attempts: 4
  max_initial_training_seconds_per_attempt: 2400
  max_polish_seconds_per_attempt: 1200
  max_profile_seconds_per_solve: 600
  these_are_budget_caps_not_convergence_guarantees: true

budgets:
  max_concurrent_training_jobs: 2
  soft_aggregate_runtime_hours: 24
  hard_aggregate_runtime_hours: 48
  max_primary_profile_inner_solves: 144
  include_failed_and_interrupted_jobs_in_costs: true
  no_replacement_seeds: true
  no_auto_extend_for_significance: true

metrics:
  inherit_original_denominator_floor: true
  report_absolute_error_alongside_relative: true
  weak_direction_normalized_gap_floor: 1.0e-3
  cluster_repeated_offsets_by_root_center: true
  require_all_attempts_in_status_table: true
```

资源上限是执行保护，不是对运行时的预测。允许在开发期依据实际硬件调整，**正式队列冻结后不得根据测试结果修改**。如必须因环境故障修改，建立新协议版本，旧队列仍完整保留。

seed base 仅为候选。先扫描所有可访问分支的历史 seed；发生冲突时，在任何新结果生成前按固定规则将整个 base 增加 10000，直到无冲突，写入最终 `seed_manifest.csv`。

`freeze` 必须保存：最终配置、源代码 commit/dirty patch、配置 SHA-256、seed manifest、环境信息和冻结时间。仅内部冻结协议时称“预先固定协议”，不冒称外部注册的预注册研究。

---

## 15. 实现结构与命令接口

以下是**建议新增**的隔离目录，并不声称已存在。先检查冲突，再映射或实现。尽量复用现有模型和求导代码，不重写整个训练框架。

```text
revision_week/
  README.md
  run.py
  config/
    protocol.template.yaml
    protocol.frozen.yaml
  adapters/
    repo_adapter.py
  core/
    directional_curvature.py
    error_control.py
    functional_profile.py
  experiments/
    e0_archived.py
    e1_operator_adaptive.py
    e2_coupled.py
    e3_width_bridge.py
    e4_profile.py
    e5_one_step.py
  tests/
    test_algebra.py
    test_operator_parity.py
    test_failure_paths.py
  outputs/<run_id>/
    audit/
    protocol/
    metrics/
    traces/
    figures/
    reports/
```

文件可以合并，避免为了跑少量实验开发通用调度平台。必须提供稳定 CLI，并在 README 说明实际命令。

最低接口合同：

```bash
# 下列命令在 Codex 实现对应入口后才可执行。
python revision_week/run.py audit --repo .
python revision_week/run.py self-test
python revision_week/run.py run --experiment E0 --config revision_week/config/protocol.template.yaml
python revision_week/run.py run --experiment E1 --config revision_week/config/protocol.template.yaml
python revision_week/run.py freeze --config revision_week/config/protocol.template.yaml
python revision_week/run.py run --experiment E2 --config revision_week/config/protocol.frozen.yaml
python revision_week/run.py run --experiment E3a --config revision_week/config/protocol.frozen.yaml
python revision_week/run.py run --experiment E4 --config revision_week/config/protocol.frozen.yaml
python revision_week/run.py run --experiment E5 --config revision_week/config/protocol.frozen.yaml
python revision_week/run.py report --run-id ACTUAL_RUN_ID
```

运行器必须支持断点恢复和已完成任务去重。继续同一数值任务可以，不能把一次失败重启换随机种子后记作原任务成功。中断恢复时保存累计成本。

### 15.1 核心函数接口建议

```python
# 输入输出含义必须在实际代码中使用类型标注和 docstring 说明。
load_historical_center(center_id)
make_residual_and_objective(center, frozen_target)
solve_gn_response(center, frozen_target, solver_config)
evaluate_directional_so(center, Z, frozen_target)
estimate_or_verify_mu(center, frozen_target, config)
refine_state_response(center, Z, frozen_target, tolerance, budget)
compute_independent_dense_reference(center, frozen_target)
solve_local_profile(frozen_target, lambda_value, theta_init, budget)
run_one_step_comparison(profile_root, start_offset, config)
```

`evaluate_directional_so` 返回 F、D、GN 残差、对称性误差和调用计数。`refine_state_response` 返回最终 Z/F、停止理由、界来源和完整轨迹，不能只返回一个数。

---

## 16. 数据记录、统计与图表

### 16.1 每条运行记录至少包含

```text
run_id, experiment_id, protocol_hash, source_commit, source_ref
center_id, parent_center_id, data_seed, init_seed, noise_seed
pde, parameterization, n_state, n_parameter, residual_count
weights_hash, dataset_hash, gamma, gamma_anchor_id
method, status, failure_reason, historical_validity_flags
state_grad_absolute, state_grad_normalized, parameter_grad
reference_status, spd_status, mu_value, mu_source, bound_status
error_absolute, error_relative, U_absolute, U_relative
gn_residual, response_defect, identity_residual
jvp_count, vjp_count, hvp_count, A_matvec_count
setup_seconds, solve_seconds, total_seconds, peak_memory
```

E4/E5 另存每个 h/偏移/候选步的逐步轨迹。NaN、失败和未执行必须保留原因，不能把缺失写成 0。

每个表同时呈现：计划数、实际尝试数、参考可用数、方法成功数、容差达标数。方法比较可给 paired-valid 子集，但同时报告各方法失败率，避免通过交集筛选掩盖失败。

原稿相对误差与新绝对误差同时保留；不得以新归一化让原结果显得更好。seed 重复、同中心多个 h、容差扫描和重复计时不当作独立样本。

### 16.2 必需图表

| 输出 | 内容 | 用途 |
|---|---|---|
| Figure A | 逐中心 RAW/GN/SO/ADAPT 对 exact 的误差 | 是否存在实际曲率改进 |
| Figure B | U 与真实绝对误差；标明数值估计/验证界 | 界是否有效、是否过松 |
| Figure C | 精度—HVP/时间曲线，含全部前置成本 | adaptive 是否有代价优势 |
| Figure D | 新 coupled 误差和非退化弱方向角 | 多参数几何而非只标量大小 |
| Figure E | width 32/64 误差及 valid/attempted | 准确性过渡验证 |
| Figure F | 全部 h 的 profile 曲率误差和初始化总成本 | 状态预测能否实际使用 |
| Figure G | 一步更新的实际下降、接受率、参数误差变化 | 是否超出事后诊断 |

表格至少包含：历史重现、方法总体对比、新队列可用率、误差控制达标率、下游功能结果。

不能完成某图时说明未完成，不画空结果或合成“示意实验结果”。所有图必须可由保存的原始表重新生成。

---

## 17. 一周排程与停止条件

### Day 1：审计与最低数学验证

完成 REPO_AUDIT、来源清单、合成单元测试和 E0 首批/全量矩阵分析。原矩阵不可获得时先报告具体缺口，不能把“复现 21 个中心”标为已完成。

### Day 2：HVP 与开发期方法冻结

完成 E1 的显式/矩阵无关一致性、界来源标记、有限次升级测试。最多启动 4 次驻点精化开发运行，测量成本。决定是否启用 E3b。冻结代码配置与新种子。

### Day 3–4：独立队列

按硬件预算运行 E2、E3a，以及预先启用的 E3b。任务按冻结顺序执行，不看哪个 PDE 更好再追加。

### Day 5：profile 与状态预测

执行 E4；先排查固定目标、根点精度与内层优化误差，再讨论收敛曲线。不能通过删除难例修复 profile 结果。

### Day 6：一步参数更新

执行 E5 的小型功能验证。优先保证与同目标 oracle 的公平比较，而不是扩大迭代次数。

### Day 7：复核、生成论文素材并冻结结果

重跑快速单元测试与摘要生成；检查数据泄漏、分母、成本与引用。输出论文可用结论和边界，生成新本地结果快照。

### 停止规则

1. **数学/复现错误：** 恒等式、目标一致性、变量顺序错误未解决，不开正式新队列。
2. **SO 无收益：** 保留负结果，检查 adaptive 是否有独立价值；没有则不继续包装新方法。
3. **界过松：** 不改变 mu 取值规则迎合结果；转为残差估计 + 有限预算修正，明确未获认证。
4. **驻点不可得：** 用尽预设 polish 预算后记录失败，不降低 gate、不补好 seed。
5. **profile 不稳定：** 用尽冻结预算后停止，只报告局部或代数结果，保留旧 1/5 记录。
6. **主动更新无收益：** 不宣称提升参数准确性；状态预测若有收益可单独报告。
7. **预算超限：** 开发期优先关闭 E3b 和额外复验；正式队列开始后若遇硬上限，剩余任务标为未执行，不将已完成子集冒充完整队列。

不得把新队列做到一半后反复调方法，再把同一队列称为 held-out。确需调试时，该队列降级为开发；本周来不及新增独立队列就如实说明。

---

## 18. 最终交付清单与允许的论文结论

### 必交文件

```text
REPO_AUDIT.md
artifact_manifest.csv
protocol.frozen.yaml
seed_manifest.csv
environment.json
TEST_REPORT.md
METHOD_MATH_NOTE.md
ALL_RUNS.csv
METHOD_SUMMARY.csv
FAILURE_ANALYSIS.md
COMPUTE_BUDGET_REPORT.md
RESULTS_SUMMARY.md
PAPER_REVISION_NOTES.md
RESUME_COMMANDS.md
```

数学说明必须给出完整二次型、缺陷恒等式、近似升级公式、误差界假设、whitening 变换及浮点验证层级。它们是本项目推导与实现规格，不凭恒等式本身宣称首次提出。

### `RESULTS_SUMMARY.md` 必须明确回答

1. 现有仓库的哪些结果被实际重现？哪些仅能从原稿核对？
2. SO 在旧开发集和新队列分别改善多少、失败多少？
3. 误差界有多少是真验证型、多少是数值估计、多少无法获得？
4. 自适应方法是否在相同精度下节省了**总成本**？谱信息是否来自 oracle？
5. 宽度验证解决了什么，仍未解决什么？
6. 状态预测是否降低了同目标重优化成本？
7. 一步更新是否改善 profile 下降和真实参数误差？两者是否有冲突？
8. 当前证据支持的方法贡献是什么，而不是预期贡献是什么？

### `PAPER_REVISION_NOTES.md` 使用三栏

```text
可进入主文的结论 | 直接支持的运行/图表 | 必须保留的限定条件
```

允许的候选贡献包括：

- 对有限阻尼局部约化曲率的参数方向二阶修正。
- 对近似状态响应的缺陷表达与相应条件性后验误差控制。
- 实际可复现的矩阵无关实现及精度—成本权衡。
- 状态预测、受保护参数更新中的已验证用途。

没有证据时禁止写：

- “首次二阶约化 Hessian / 首次 variable projection”。
- “严格可靠性证书”，但 mu 实际只是普通特征值估计。
- “显著提升真实参数辨识精度”，但只测了曲率误差。
- “不再局限局部”，但只做了一步局部更新。
- “大规模准确性得到验证”，但准确性只做到 129/257 状态参数。
- “全部样本成功”，但只展示有效子集。
- “100k 全流程矩阵无关认证”，但谱下界来自不可扩展的 dense oracle。

**完成标准不是所有结果都成功，而是证据可追溯、公式正确、比较公平、成本完整、负结果透明，并据此完成一次可以投稿使用的实质性修改。**

---

## 19. 现在开始执行

按以下次序开始，不等待作者逐项确认可从仓库自行确定的信息：

```text
检查工作区与本地/远程引用
  -> 核实历史证据和实际代码入口
  -> 输出仓库审计与复用清单
  -> 实现/验证完整二次型和误差恒等式
  -> 运行 E0
  -> 汇报真实结果、下一阶段取舍与累计成本
  -> 再进入 E1 和冻结后的新队列
```

第一次进度汇报应提供实际路径、实际 commit、实际完成的测试和结果，而不是只复述本任务书。
