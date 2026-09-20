# 投稿前实验意见补救评估

日期：2026-09-20  
范围：用户提供的《投稿前最终检查报告》与当前 SAEPS v2.0 / V5 证据。

## 结论

风险1和风险2都不是完全不可补救，但不能用事后改判来补救。可以保留较强主张的路线是：保留原锁定结果作为历史结果，同时另立一个写明门控、独立 solver 和比较对象的补强协议。风险3的原始 9/10 门槛不能直接改成 8/10；风险4可以通过匹配阻尼的 operator audit 强化，但不能把 operator feasibility 当成大网络精度证据。

因此不建议直接覆盖原配置、追加未经预注册的 confirmation seed，或只为增加通过数而降低阈值。应先完成门槛敏感性审计，再决定是否启动独立 rescue cohort。当前最稳妥的论文定位仍是：

> SAEPS is a finite-damping, checkpoint-dependent local Gauss--Newton state-elimination diagnostic. Its primary evidence is a paired comparison with an exact finite-γ local reference; finite-displacement nonlinear-profile validity remains unresolved.

## 意见逐项判断

| 检查报告意见 | 能否补救 | 推荐动作 | 能解决什么 | 不能解决什么 |
|---|---|---|---|---|
| Profile 收敛未建立 | **不能在当前协议内补救** | 保留 21/21 可计算、21/21 branch-comparable、20/21 参照接近、0/21 严格驻点、5/126 refinement 达标，以及历史 1/5；新增三层状态定义 | 让审稿人清楚 numerical consistency 与 convergence 的区别，并解释诊断的有限范围 | 不能把 20/21 改写成 profile validation，也不能证明局部二次模型在有限位移下可靠 |
| Profile 失败原因诊断 | **可以补强** | 使用 S2 v1/v2、中心一致性、Newton/basin、fit-window 和误差预算报告“数值/科学原因未决” | 说明已检查 conditioning、center consistency、finite-difference amplification 和 basin reachability | 不能排除方法在有限位移下本身失效 |
| 经典 variable-projection / Schur 基线缺失 | **部分可以补救** | 把已有 VP0/SVD 后验结果作为非绑定 baseline appendix；报告 0/12、0/9 classical admissibility 和 TSVD 敏感性；明确无 exact γ=0 gold standard | 说明经典无阻尼目标为何在这些中心不可用，并回应“SAEPS 不是凭空与 raw 比”的问题 | 不能宣称 SAEPS 已优于经典 VP；matched finite-γ VP 与 SAEPS 代数上相同，不能当作独立阳性结果 |
| 双参数 8/10 未达 9/10 | **可以通过降级定位补救** | 从主结论移到 secondary/directional evidence；保留失败 seed、state-center gate 和 `inconclusive` verdict | 降低过度外推风险，完整回答为何不能称为 joint-geometry confirmation | 不能补成 9/10，也不能证明跨问题泛化 |
| 大规模 α=10^-2 与精度 α=10^-8 不一致 | **可以通过范围澄清补救** | 将 100001-state 结果标为 operator feasibility；把 finite-γ sweep 和 matched-cost 结果作为阻尼敏感性/成本证据 | 清楚说明它验证的是 JVP/VJP、CG 和存储可行性 | 不能支持大网络 accuracy、生产级 speedup 或大规模 SAEPS efficacy |
| 增加 2D / 非合成 benchmark | **不建议作为本轮补救** | 如无新协议，不启动；现有 non-affine saturation 作为结构扩展即可 | 若未来另立协议，可增加外部有效性 | 对当前锁定结论没有追溯性，短期投入大且不解决 profile gate |
| 报告 α 敏感性 | **已有证据可补强** | 使用现有 finite-damping sweep（含低 α resolved-count 限制），补充一张表或放入 supplement | 说明 SAEPS 是带 relaxation price 的族，而非单一分数；解释 α 增大趋向 frozen limit | 不能选择一个“最优 α”来挽救 profile，也不能把不同 α 的精度直接混合比较 |

## 风险1：是否是门控过严，以及怎样真正补救

### 现有失败的直接原因

E7 的 profile 点并非算不出来。21/21 个步长满足 branch-comparison，20/21 与 Schur reference 在 10% 内接近；失败集中在优化精度和小步长误差地板：

- 三个梯度门槛是 (10^{-8},10^{-10},10^{-12})，但每个位移点最多 1000 次 L-BFGS 迭代；
- 记录显示 (10^{-8}) 级只有 5/42 branch refinements 达标，(10^{-10}) 和 (10^{-12}) 级为 0/42；
- 对称差分的优化误差按 (h^{-2}) 放大，所以 (h=10^{-4}) 处即使 branch 可比，也可能出现明显曲率误差；
- 既有误差呈 V 形：大步长受局部截断影响，小步长受 profile 优化误差影响；
- 历史 V5 bridge 的 5 个 seed 都可计算，但只有 1/5 同时满足最细 profile error 和 last-two curvature-change 门槛。

因此，原门控并非无意义地严格；它对于“严格有限位移 profile 收敛”这个强命题是合理的，但把全局固定梯度阈值直接用于所有 (h) 会把 solver precision、曲率分辨率和科学有效性混在一起。门控更像是**对强主张过严、对数值误差结构又不够针对**。

### 可执行的 rescue protocol

如果目标是保留 nonlinear-profile 支撑，应启动新的 S3 development/rescue，而不是改写 V5 结果。最小闭环为：

1. 固定原锚点、原 (gamma)、原步长方向和独立起点规则；
2. 将 1000 次预算提高到预先声明的预算，采用 safeguarded Newton/CG 或 L-BFGS + Newton polish；
3. 用 positive-Hessian 下的 objective-error bound 设定每个 (h) 的允许 profile 误差：
   [
   2,deltaPhi(h)/h^2 leq 	au_{m profile}|H_{m red}|,
   ]
   不再只用一个与 (h) 无关的梯度数字；
4. 对每个分支增加 independent-start repeat 和 objective non-increase 检查；
5. 至少保留三个尺度，分别检查 branch stationarity、局部最小值、曲率随 (h^2) 的 plateau 和误差预算；
6. 在看到结果前锁定 fit window、(	au_{m profile})、重复起点和失败处理。

只有当独立 rescue cohort 同时通过这些条件，才能把“SAEPS agrees with independently converged nonlinear profile curvature”重新列为 supported claim。若新 cohort 只显示更好的 numerical consistency，仍不能跳过 convergence certificate。

### 当前数据支持的门控敏感性结论

对 E7 已保存的梯度记录做只读审计可见：若只把梯度门槛放宽到 (10^{-7}) 或 (10^{-6})，42/42 branches 都会被标记为数值达标；但这并不自动修复 (h^{-2}) 放大，也不能证明 profile 曲率误差已受控。反过来，原 (10^{-8}) 门槛下只有 1/21 个双侧 step 同时达标，说明“0/21 strict stationarity”主要反映门槛与预算组合，而不是 21 个点完全没有下降。

这个审计支持“门控需要按误差预算重构”，不支持事后把 0/21 改报成 PASS。

## 风险2：经典基线怎样补救

风险2可以比风险1更快补强，因为仓库已经有两类证据：

- P5 记录中有 independent classical forward profiles；有效记录的 classical profile 有明确内部 minimum 和正曲率，不能说“完全没有经典基线”；
- `POSTHOC_VARIABLE_PROJECTION_V1` 给出了 VP0/SVD 的 21 个 scalar centers、rank/nullity、cutoff sensitivity 和 exact (gamma=0) admissibility。

缺口是这些结果没有在 CAMWA 投稿包中注册成统一的 `raw--SAEPS--classical-profile--VP0` 比较表。补强应做三件事：

1. 从 P5 机器记录自动聚合 classical profile 的 minimum、curvature、(R^2)、valid denominator，并与 raw/SAEPS 同 seed 对齐；
2. 将 VP0/SVD 作为 formal matrix-only baseline，明确 `0/12` Burgers、`0/9` Allen--Cahn 的 exact (gamma=0) admissibility，以及 TSVD cutoff sensitivity；
3. 把主张写成“SAEPS fills an ill-conditioned, finite-damping diagnostic regime and is checked against a conventional forward profile where available”，不要写成“SAEPS universally outperforms variable projection”。

如果想保留更强的“相对经典方法优势”主张，下一步应运行独立 classical forward solver 的 profile curvature，并在同一 parameter offsets、同一 observation/noise 条件下对齐。这个实验比继续增加 PINN seed 更能回应审稿人。

## 风险3：8/10 能否直接把门槛降到 8/10

不能直接把原始 9/10 scientific gate 改成 8/10。8/10 是现有数据的描述性事实，9/10 是确认协议的验收规则；两者不能在看到结果后互换。可以做两种合规补救：

- **敏感性审计：** 同时报告 8/10 和 9/10 的 verdict，说明结论对 availability rule 的依赖；不改变原 verdict；
- **新 cohort：** 在新协议中先声明新的 availability rule、failure handling 和 seed 数量，再运行独立 confirmation。新结果与原 8/10 分开，不能回填原 denominator。

若不补新 cohort，最强可支持措辞仍是“all eight valid matrix comparisons favor SAEPS, but the preregistered availability target was not reached”。

## 风险4：阻尼不一致的定量判断

风险4不是“(alpha=10^{-2}) 下方法无效”，而是两个问题被混在一起：

- 精度实验用 (alpha=10^{-8})，目标是观察 state adaptation 对局部曲率的影响；
- 100001-state 实验用 (alpha=10^{-2})，目标是测试 JVP/VJP、CG、内存和 operator application 的可行性。

已有 finite-damping sweep 显示，(alpha) 改变的是被测对象本身：低阻尼时 retained fraction 较低，增大阻尼后逐渐接近 frozen-state limit。故不能把 (alpha=10^{-2}) 的运行当作 (alpha=10^{-8}) 精度结果，也不能因目标不同就称大规模运行“无效”。

最有效的补强是一个低成本的 matched-α operator audit：

1. 在小/中型网络上用 (alpha=10^{-8},10^{-6},10^{-4},10^{-2}) 做 dense-vs-CG/LSQR agreement，作为 solver correctness anchor；
2. 在 100001-state expansion 上至少复现 (alpha=10^{-8}) 和 (alpha=10^{-2}) 的 matrix-free residual、symmetry/bilinear consistency、CG iteration and JVP/VJP counts；
3. 将结果标为 operator feasibility and damping transferability，不把它写成 trained large-network accuracy；
4. 若资源允许，再对一个真正训练的中型宽网络做同阻尼 curvature reference，这才是从 operator feasibility 走向 accuracy 的证据。

这样可以保住“SAEPS 的 matrix-free implementation scales to the tested operator dimensions”这一主张，但不能把它升级成“100001-parameter SAEPS 已经验证精度”。

## Profile 风险的可审计写法

正文和补充材料应采用三层状态，而不是二元的“通过/失败”叙述：

1. **PROFILE_EVALUABLE**：有限位移目标完成计算，程序产生数值结果；
2. **NUMERICALLY_CONSISTENT**：在声明步长和 branch-comparison 规则下，与 local Schur reference 接近；
3. **PROFILE_CONVERGED/VALID**：严格 state stationarity、局部 basin/最小值检查和多尺度曲率一致性同时满足。

当前 saturation E7 只能支持前两层，不能支持第三层。历史 V5 bridge 只有 1/5 达到第三层。建议正文使用：

> The finite-displacement evaluations were numerically consistent with the local Schur reference at most tested steps, but strict profile stationarity and small-radius convergence were not established. We therefore treat these results as a numerical-consistency diagnostic, not as evidence of nonlinear-profile equivalence.

紧接着回答诊断价值：

> Without a converged finite-displacement profile, SAEPS remains useful for the narrower task it directly computes: quantifying state-adaptation confounding and comparing frozen-state Gauss--Newton curvature with an exact finite-γ local reference at a declared checkpoint. A profile interpretation requires a separate convergence certificate.

对“数值问题还是方法问题”的回答必须保持不可判定：

> The observed failures are compatible with ill-conditioned state blocks, center inconsistency, finite-difference error amplification, and local-basin reachability limits. Because the profile did not satisfy its convergence certificate, the current evidence cannot distinguish a solver limitation from a finite-displacement limitation of the local quadratic model.

## 经典基线的正确补强方式

已有 `docs/evidence/POSTHOC_VARIABLE_PROJECTION_V1.md` 和稿件中的 VP0/SVD 分析足以补齐“经典方法是否被检查过”这一层，但不能制造一个不存在的 gold standard。建议在补充材料中并列报告：

- raw fixed-state GN：原始比较基线；
- SAEPS：有限阻尼 local state elimination；
- VP0/SVD：形式上的无阻尼矩阵极限及 cutoff sensitivity；
- exact γ=0 classical target：Burgers 0/12、Allen--Cahn 0/9，在冻结的正定 admissibility rule 下不可用。

因此论文应说“SAEPS provides a regularized alternative in the tested ill-conditioned regime”，不能说“SAEPS outperforms classical variable projection”。

## 不建议继续投入的实验

- 继续增加 profile seed 或 branch 数量，但不改变 convergence gate；
- 以 finest-pair-only 代替多尺度二次拟合；
- 放宽 gradient/stationarity threshold；
- 根据失败结果改选 γ、步长、profile 区间、source 或 benchmark；
- 重新运行 confirmation 以追求 9/10、1/5 以上或 0/21 改善；
- 把大规模 α=10^-2 运行扩展成“大网络精度验证”。

这些操作要么违反锁定协议，要么只会改变科学问题，不能为当前主张提供独立证据。

## 投稿前最值得做的四项工作

1. 在正文 profile 小节和 Discussion 中加入三层状态与“诊断价值”段落；
2. 在 supplement 增加 VP0/SVD baseline registry，说明 admissibility 失败和 cutoff sensitivity；
3. 把双参数和 100001-state 结果明确移到 secondary/descriptive evidence；
4. 修复 Highlights、表格列宽、参考文献首行、重复标题和未解析引用等格式问题，再编译并逐页检查 PDF。

## 证据来源

- `docs/EXECUTION_CONTRACT.md`：锁定协议、confirmation 隔离与禁止通过调参修复 scientific failure；
- `docs/paper_strengthening/WRITING_MATERIALS_LIMITED_CLAIMS.md`：收缩主张素材与 profile 失败分层；
- `docs/paper_strengthening/S2_FIT_WINDOW_DECISION.md`：v1 fit-window 裁决；
- `docs/paper_strengthening/S2_V2_MODIFICATION_REPORT.md`：v2 数值修改和未形成完整 cohort 的记录；
- `docs/evidence/POSTHOC_VARIABLE_PROJECTION_V1.md`：经典 VP0/SVD 后验 baseline；
- `CAMWA_submission_package/manuscript_source/manuscript.tex` 与 `supplement.tex`：当前投稿版写法和 profile 分母。
