# Phase 1.5 方法定型：可执行开发协议

协议 ID：`SAEPS-V6-PHASE15-DEV-001`。日期：2026-09-07。
本次交付为协议、配置和输入清单；实验状态 `NOT_STARTED`。
配置为 `DRAFT`，不是新确认锁；不得声称已执行 A/B/C 或通过进阶门槛。
依据用户贴出的路线，将含糊建议落实为下述明确规则；这些工程选择需在
首次科学执行前连同实现 hash 固定。后续任何修改必须产生新版本，保留旧结果。

## 1. 范围与执行顺序

本轮仅历史矩阵。顺序为协议静态验收 → 数值单测 → 1.5A 谱/机制 →
1.5B 起点对照 → 1.5C 预处理与停止规则 → 自动汇总/方法选择。
每阶段工程状态通过才推进；阴性方法结果保留且不等于工程失败。
不训练新 PINN、不调整 gamma、不启动 matrix-free replay、medium、profile、
Darcy 或 confirmation。旧论文主张和 V2–V5 协议不改。

从 `cd01a26` 建立开发分支。原有用户删除/新增文件不恢复、不提交。
新增代码用 `src/saeps/v6`、`scripts/v6`；配置用 `configs/v6/development`。
数据存储沿用第一层已记录的兼容位置
`outputs/runs/v5/upgrade_pilot/phase15/<execution_id>/`：只是规避旧整树冻结
检查的存储约定，不重开 V5。输出目录必须全新，禁止覆盖。

全部 Burgers 55–69、Allen–Cahn 75–84 进入清单。按归档 `analysis_valid`
确定可计算队列；无效记录每个计划 cell 都生成终态，不替换、不重新精修。
原确认标签保留在 provenance，但在本方法研究中全部标为
`HISTORICAL_DEVELOPMENT`，不能当新 held-out。不得按算法表现删 checkpoint。

## 2. 数学对象与有效性

令 G=G_tt，B=G_tl，Gll=G_ll，H=H_tt_sym，C=H_tl，Hll=H_ll。
所有量来自同一归档的 total-objective 单位，不乘除 residual count。
M=G+gamma I；A=H+gamma I；S=H−G；T=C−B。

Z0=M^{-1}B；Z*=A^{-1}C；Fgn=Gll−BᵀZ0；H*=Hll−CᵀZ*。
K(Z)=Hll−CᵀZ−ZᵀC+ZᵀAZ；D=C−AZ。
在 A 正定时：K−H*=DᵀA^{-1}D=(Z−Z*)ᵀA(Z−Z*)。
初值精确时 D0=T−SZ0；数值初值有残差 rgn=B−MZ0 时，
必须验证 D0=T−SZ0+rgn，不能忽略初始求解误差。

输入有限、尺寸匹配、cross transpose/对称性相对误差≤1e-8；M Cholesky
成功；A 最小特征值正且相对谱尺度>1e-10。失败拒绝，不加额外 damping。
历史 `analysis_valid=false` → CHECKPOINT_INVALID；合法输入但求解未完成
→ SOLVER_FAILURE；非有限、SPD或代数核验失败→NUMERICAL_FAILURE。
PASS 仅表示计算有效；达不到误差门槛仍可为 PASS，另记 method_gate=false。

主误差 e=||K−H*||F/(||H*||F+1e-8)。候选运行不能访问 H*、Z*、
A 特征分解或真实误差；这些只由独立评估器读取。
本轮 p=1；未来 p>1 必须单独验证 block 算法和坐标尺度，不能用逐列
scalar PCG 的结果声称 block-PCG 单调性。

## 3. 1.5A：谱、defect 与抵消

Cholesky M=LLᵀ，求对称矩阵 W=L^{-1}AL^{-T} 的特征对 (lambda,Q)。
v=L^{-T}Q 是 M 正交广义特征向量。报告 lambda 全谱、lambda_max/lambda_min、
max|lambda−1|、|lambda−1|>0.1 和 >0.5 的数量。
原文两行 outlier 阈值格式损坏；这里 0.1/0.5 是新增描述性选择，不是支持门槛。
不能用非对称 M^{-1}A 的 Euclidean singular-value condition number替代谱条件数。

令 d=L^{-1}D0，a=Qᵀd。第 i 个方向的曲率误差能量为 ||a_i||²/lambda_i；
保存绝对值、归一化权重、累计50%/90%/99%能量所需方向数、outlier能量份额。
若总能量≤浮点尺度，归一化份额标 null，保留绝对值。
完整保存谱，不只展示最符合“聚集在1附近”的样本。

对 exact-GN PCG 的 k=0,1,3,5，比较真实能量比与
min(1,4*((sqrt(kappa)−1)/(sqrt(kappa)+1))^(2k))。
该式为精确算术下的上界，不是点预测；谱聚集不必意味着条件数很小。
浮点偏差单独报告。分母初始能量太小时不计算比值。

抵消定义须使用带符号分解：delta_fix=Gll−Hll；
delta_relax=BᵀM^{-1}B−CᵀA^{-1}C；
Fgn−H*=delta_fix−delta_relax。
chi=|delta_fix−delta_relax|/(|delta_fix|+|delta_relax|+1e-8)。
对全队列报告 chi，重点标注 Burgers 59、67。不要仅由初始修正变差
推断误差抵消；必须核对两项符号、大小与相减恒等式，不设置事后“低chi”标签。

## 4. 1.5B：起点、PCG 与公平成本

同一 checkpoint、同一固定 SPD P、同一 arithmetic 下比较 zero-start
与 GN-start。二者都用标准 scalar PCG；GN-start与defect solve代数等价。
第三组 adaptive 是同一GN-start轨迹的不同停止规则，不另称新的线性求解器。

PCG：r=C−Az，w=P^{-1}r，p=w；alpha=(rᵀw)/(pᵀAp)，
z←z+alpha p，r←r−alpha Ap；beta=(r_newᵀw_new)/(r_oldᵀw_old)。
p←w_new+beta p。pᵀAp≤0、非有限或预处理非SPD则失败。
保留递推与显式核验残差，差异超出1e-8尺度则记数值异常；不静默rescue。
使用缓存Az更新K；不得每个日志点免费追加A乘法。

B 对所有候选跑到 n_theta 步或核验相对响应残差≤1e-10，记录首次达到
5%、1%、0.1%、0.01%真实曲率误差的步数与累计成本。
这四项只能由离线oracle选first-hit；不能作为在线停止实现。
未达到为 null + target_reached=false，不以最大步数冒充达到。
同时报告初始K误差，允许GN-start在0次扩展满足目标。

GN初始化也不能免费：用对M的完全重正交Lanczos/Galerkin，从B开始，
记录所有Gv及基向量，至核验残差≤1e-10，最大n_theta。保存残差历史、Q、GQ。
此实现面向小矩阵可审计开发，不预先声称大规模高效。
A阶段dense Z0只作oracle；B/C以实际迭代Z0运算，另核对与dense的差异。

报告 cold-start total（包括GN初始化）和 already-SAEPS incremental 两种成本。
recycled/hybrid 的zero-start对照也需先生成同一个P，其GN初始化不能免费。
diagonal/Nyström/exact的zero-start则不需Z0；明确记录不对称初始化成本。

## 5. 1.5C：固定候选

以配置中的预算和rank为准，所有方法含预算0基线。随机Nyström每个rank
使用5个PCG64 seed [0..4]，与checkpoint seed字段严格分开。
同checkpoint/sketch seed生成n×32标准正态矩阵，rank r取前r列再QR；跨rank配对。

|候选|rank|扩展预算（另含0）|
|---|---|---|
|diagonal|无|1,3,5,10|
|Nyström|4,8,16,24,32|1,3,5|
|recycled Ritz|4,8,16,24|1,3,5|
|hybrid defect|8,16,24|1,3,5|
|exact GN|full|1,3|

diagonal：P=diag(M)。本轮读取稠密对角，必须标为dense-access setup；
未来随机VJP对角估计不在本协议中，不能把当前对角访问称为matrix-free免费。
exact GN：Cholesky M，setup和三角求解单独计时，仅oracle-like控制，不参与胜出选择。

Nyström：Omega=QR(sketch)，Y=G Omega（按列计r次Gv），T=OmegaᵀY。
对称T，特征分解保留 t_i>1e-11*max(t)；显著负值→失败；数值零截断。
F=Y Q_t diag(t^{-1/2})，thin SVD F=U Sigma Vᵀ，Lambda=Sigma²。
P=gamma I+U Lambda Uᵀ，P^{-1}d=d/gamma−U[(Lambda/(gamma*(gamma+Lambda)))⊙Uᵀd]。
同时实现更稳定的正交/补空间拆分形式并交叉检查；不得添加改变gamma的shift。
这是显式固定的Nyström近似方案，不宣称等同所有文献中的优化预处理公式。

recycled：从GN初始求解累计的Q/GQ构造 QᵀGQ Ritz分解，取最大非负
Ritz值对应的r个方向，按同一低秩逆公式应用。若可用维数不足r，记录实际rank，
不为凑rank继续GN求解，也不从完整G特征分解偷取Ritz向量。
Ritz小系统与正交化计时；缓存GQ不重复计Gv。复用减少额外setup，但初始求解
成本仍在cold total，不能声称整个预处理免费。

hybrid：总rank r，使用前r−1个recycled方向，再加入归一化D0的正交补。
两遍重正交，独立性≤1e-11则不补；不追加随机方向。对Qh执行投影
QhᵀGQh，缺失的Gq列计入setup，用Ritz低秩逆。D0包含C/A信息，故其
形成成本计入setup；zero-start hybrid对照使用同一个P，不能隐去这笔成本。
所有P在外迭代开始前固定，禁止按外残差更新P后继续使用标准PCG。

## 6. 自适应指标与停止

eta=DᵀP^{-1}D；eta/(|K|+1e-8)<1e-3时停止，最多5次外扩展；
输入使用显式核验D，核验A乘法计入成本。指标准则可能过早或过晚停止，
不得用oracle纠正、退回Fgn挑较好值或延长预算。未触发仍输出第5步，
stop_reason=MAX_BUDGET，不伪报收敛。新确认规则尚未授权。

若 c1 P≤A≤c2 P，则 eta/c2≤DᵀA^{-1}D≤eta/c1。
这里只在开发评估器用广义谱算c1/c2验证；算法不可读取它们。
因此eta只是indicator，不是certificate。比较eta与真实gap的全轨迹
log尺度Spearman、eta/gap范围、过早停止数及未停止数，分checkpoint报告，
不能把同一checkpoint的迭代点当独立样本做显著性检验。

## 7. 完整成本和运行字段

必须拆分 initial_GN、preconditioner_setup、cross_block_access、
initial_defect、outer_solve、explicit_verification、oracle_validation、I/O。
method_total不含oracle和I/O，但包含用于停止的所有核验。
单线程float64；1次warmup、5次计时重复，各次从相同初始化开始。
重复不改变sketch，不挑最快值；报告中位及范围。平台、BLAS/版本、线程数记录。

N_Gv/N_Hv按向量列数计，不按一次批量调用计；A v计1 Hv，gamma axpy另计。
本轮真实JVP/VJP/HVP调用为0；dense_Hv与future_HVP_equivalent分字段，
Gv可标注理论上对应1JVP+1VJP，禁止冒充真实测量。直接矩阵分解、矩阵读取、
对角访问、内存和低秩运算不能仅用matvec数代表；必须有时间和存储字节数。
peak native memory不能可靠测则null+reason；禁止把tracemalloc当完整native峰值。

每条record：schema_version、execution_id、protocol/config/code/input SHA256、
git_commit/dirty_files、timestamp、source_path/source_seed/original_status、split、
benchmark、n_theta/p、gamma、dtype/hardware/package_versions、candidate/rank_requested/
rank_actual/sketch_seed/start、status/failure_reason、SPD/symmetry/solve checks、
initial_GN_residual、逐步K/Dnorm/eta/basis或PCG步数/累计成本/stop_reason、
separate oracle e/gap/first_hits、原SAEPS e、method_gate。
无关训练/profile字段记null+not_run，不虚构training_time或stationarity新测量。

## 8. 汇总、选择与进阶门槛

所有摘要、表、图从同一raw记录生成。始终报告25计划、源有效/无效、
每个cell计算成功/失败数；随机方法另报告checkpoint×5重复分母。
同checkpoint配对。随机门槛用每checkpoint的5个sketch中的最差误差，
任一失败即该checkpoint不满足门槛，不能选最好sketch或将5次当5个checkpoint。

固定预算与adaptive分别汇总；可进入后续replay的候选必须满足：
有效历史全队列均计算成功；中位误差<0.005，最差<0.03；每checkpoint
e_new≤e_GN+1e-10（仅浮点非劣容差）；最多5次扩展；额外setup Gv≤30。
该“5次”是外迭代上限，不是总HVP上限；另外报告初始defect和核验HVP。
exact GN不参与选择。额外setup门槛不豁免GN初始化cold成本。
上述约束是开发的工程进阶规则，不是论文支持级别或成本优势证明。

候选先按上述门槛筛选；合格者按中位cold method_total、最差cold total、
总Hv、总Gv、rank、名称字典序择一（均用5次计时中位数）。adaptive必须独立
满足门槛，否则只保留fixed-budget候选，不能称自适应算法已定型。
若无人合格，记录NOT_SUPPORTED（对本候选集合的门槛），工程可PASSED，
停止后续replay/训练，不扩rank/预算求阳性。若合格，结论限为开发可行，
仍不自动授权后续层级，更不能写“已建立可扩展算法”。

## 9. 文件与验收接口

|拟新增文件|职责|
|---|---|
|src/saeps/v6/operators.py|纯operator接口、dense适配器、独立计数|
|src/saeps/v6/curvature.py|K、defect、独立oracle评估|
|src/saeps/v6/defect_response.py|GN初始化与可复用Lanczos缓存|
|src/saeps/v6/pcg.py|本轮scalar PCG、显式残差、停止原因|
|src/saeps/v6/preconditioners.py|固定SPD候选与setup计数|
|src/saeps/v6/stopping.py|仅indicator，无oracle依赖|
|scripts/v6/spectral_audit.py|A阶段全部检查点与抵消|
|scripts/v6/preconditioner_dev.py|B/C完整计划和fail-soft写盘|
|scripts/v6/build_phase15_report.py|逐seed/失败、谱、成本Pareto与自动gate|
|tests/v6/test_phase15_numerics.py|SPD恒等式、PCG、低秩逆、计数、oracle隔离|

这些为实现清单，不代表已有可运行文件。未来测试至少涵盖真实历史矩阵
与独立随机SPD、退化rank、负曲率、GN不精确、zero/GN轨迹同解、首达目标
不可用、成本缓存及无效保存。抽样“好seed”不能替代全队列阶段验收。
新测试放tests/v6；legacy tests原样保留。单独报v6_unit、v6_development_gate、
legacy_integrity；统一validator失败原因不得被新版PASS掩盖。

当前可运行入口为 `scripts/v6/validate_phase15_protocol.py`，只校验配置、
全输入hash清单、候选计划完整性及未授权执行状态，不计算新科学结果。
首次执行前需将实现测试通过的commit/hash加入execution manifest，再开启
新execution授权记录；不得事后覆盖本DRAFT或既有输入清单。

## 10. 理论与创新边界

配方恒等式、Galerkin最优性与PCG收敛属于经典线性代数结构。
其在本目标上的价值须由谱、目标方向能量和完整成本数据验证。
不能预先宣布“少数困难方向”“误差抵消”或“创新性已成立”。
Nyström预处理已有研究，本协议只把它作为候选数值组件：
[Frangella, Tropp, Udell, Randomized Nyström Preconditioning](https://arxiv.org/abs/2110.02820)。
全文前景判断和未来投稿路线不构成本协议的成功结论。
