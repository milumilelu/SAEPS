# SAEPS Master Research Program v4.0

> **HISTORICAL v4 PROGRAM — not the current paper-facing evidence state.** See [`V5_FINAL_JCP_AUDIT_REPORT.md`](V5_FINAL_JCP_AUDIT_REPORT.md) for the V5 final audit. The program below remains preserved as executed history.

**从 scalar one-shot confirmation 到论文级扩展验证**

总体目标不是“把 SAEPS 做成阳性”，而是回答四个层次的问题：

1. **SAEPS 是否稳定优于 raw fixed-state curvature？**
2. **SAEPS 的 GN 近似误差何时可控、能否自诊断？**
3. **这一机制能否跨 PDE、跨参数维数复现？**
4. **方法能否从 65 参数的小验证网络扩展到实际 PINN 尺度？**

下面这个任务可以直接作为 Codex 的大任务书基础。

------

## Phase A — v3.6 one-shot confirmation

这是唯一允许首先执行的科学任务。

### A1. Preflight

在运行任何 seed 之前：

- 验证 v3.6 locked config SHA256；
- 验证 lock commit；
- 验证 seeds 精确为 `30..44`；
- 验证不存在已有 `v3_6` run；
- 验证 source configs 与 v3.5 frozen engineering choice hash；
- `pytest`、v3.6 lock validator 全部通过；
- 保存 `PRE_CONFIRMATION_AUDIT.json`。

**任何一项失败：不得运行 confirmation。**

------

### A2. 一次性执行 seeds 30–44

严格执行已经锁定的：

- baseline → enhanced rescue center；
- fixed (\gamma=10^{-8}\lambda_{\max}(J_\theta^TJ_\theta))；
- two-pass scaled-LSQR refinement；
- exact finite-(\gamma) reduced Hessian；
- SAEPS-GN curvature；
- raw curvature；
- frozen GN indicator。

每个 seed 只能有一个正式结果。

必须保存：

[
F_{\rm raw},
\quad
F_{\rm se}^{GN},
\quad
H_{\rm red}^{exact,\gamma},
]

[
E_{\rm raw},
\quad
E_{\rm SAEPS},
\quad
D=E_{\rm raw}-E_{\rm SAEPS}.
]

以及：

- center status；
- rescue status；
- solver residual；
- solver iterations；
- exact Hessian diagnostics；
- (\gamma)；
- (I_{\rm GN})；
- failure reason。

invalid seed **不能补 seed、不能重跑、不能删除**。

------

### A3. 自动 adjudication

完全按照 v3.6 lock。

`SUPPORTED` 必须同时满足：

[
n_{\rm valid}\ge12,
]

[
n_{\rm planned-win}\ge12/15,
]

[
\operatorname{median}(D)>0,
]

以及：

[
p_{\rm sign}\le0.05.
]

同时输出 secondary：

- 全部 (E_{\rm SAEPS})；
- median；
- IQR；
- range；
- (E_{\rm SAEPS}\le5%) count；
- (E_{\rm raw})；
- planned/valid/invalid counts；
- GN indicator confusion matrix；
- accuracy；
- Spearman；
- calibration error。

### A4. Confirmation freeze

结果出来后立即生成：

```text
docs/evidence/V3_6_CONFIRMATION_REPORT.md
docs/evidence/v3_6_confirmation.json
docs/evidence/V3_6_FAILED_SEEDS.md
configs/v3_6/CONFIRMATION_RESULT_RECORD.json
```

并记录：

- result commit；
- config hash；
- raw manifests hash；
- scientific status。

然后：

[
\boxed{\text{v3.6 永久关闭。}}
]

不允许因为结果不好再跑 30–44。

------

# Phase B — Confirmation 后的决策树

这是整个大任务最重要的治理规则。

## Branch B+：如果 v3.6 `SUPPORTED`

意味着 comparative core claim 得到 untouched confirmation：

[
E_{\rm SAEPS}<E_{\rm raw}.
]

此时不要继续优化 Burgers。

直接进入**外部有效性 + 多参数 + scalability**。

------

## Branch B−：如果 v3.6 `NOT_SUPPORTED`

先不要做：

- multi-parameter；
- 大规模 robustness；
- 第二 PDE confirmation。

先做 postmortem。

把 failure 分成四类：

### B−1 numerical availability failure

大量：

- center invalid；
- solver invalid；
- exact gold invalid。

说明当前 pipeline engineering 不够可靠。

### B−2 comparative scientific failure

有足够 valid pairs，但：

[
D\le0
]

出现过多。

说明核心 comparative claim 不成立。

### B−3 GN approximation failure

SAEPS 始终比 raw 好，但：

[
E_{\rm SAEPS}
]

经常非常大。

这意味着：

> state elimination 思想成立，但 GN surrogate 不够好。

### B−4 indicator failure

comparative claim 成立，但：

[
I_{\rm GN}
]

无法预测 GN error。

则删除“self-diagnostic”强 claim，但 SAEPS 主结论仍可能成立。

任何新方法只能进入：

```text
POST_CONFIRMATION_DEVELOPMENT
```

并使用全新 seeds。

------

# Phase C — Second-order mechanism consolidation

无论 v3.6 最终阳性还是阴性，我都建议保留这一阶段，因为这是目前最有理论价值的新发现之一。

目标：

> 解释 SAEPS-GN 与 exact reduced curvature 的差距为什么跨 seed 从几个百分点变化到十几个百分点。

已有分解：

[
H=J^TJ+S
]

并进一步得到：

[
S_{\theta\theta},
\quad
S_{\theta\lambda},
\quad
S_{\lambda\lambda}.
]

### C1. Shapley decomposition

继续保留：

[
\phi_{\theta\theta},
\quad
\phi_{\theta\lambda},
\quad
\phi_{\lambda\lambda}.
]

但论文称：

> second-order block attribution

而不是“physical causal contribution”。

------

### C2. First-order reduced correction

重点研究：

# [ \Delta H_{\rm first}

S_{\lambda\lambda}
-2x^TS_{\theta\lambda}
+x^TS_{\theta\theta}x,
]

其中：

[
x=
(J_\theta^TJ_\theta+\gamma I)^{-1}
J_\theta^TJ_\lambda.
]

如果 v3.6 confirmation 中：

# [ I_{\rm GN}

\frac{|\Delta H_{\rm first}|}
{|F_{\rm se}^{GN}|}
]

仍然和真实 GN error 高相关，则把它发展成论文第二个方法贡献：

> **SAEPS adequacy diagnostic**

------

### C3. Matrix-free directional implementation

一个很重要的新工程研究：

定义

[
w=
\begin{bmatrix}
-x\
1
\end{bmatrix}.
]

则：

[
\Delta H_{\rm first}=w^TSw.
]

研究能否通过：

- Hessian-vector product；
- directional second derivative；

直接求该量。

目标是避免显式构造 full Hessian blocks。

必须验证：

[
\Delta H_{\rm directional}
\approx
\Delta H_{\rm explicit}
]

relative error，例如达到 (10^{-6}) 数值级一致。

这会非常有 JCP 味道。

------

# Phase D — 第二个 scalar PDE 外部复制

如果 v3.6 primary `SUPPORTED`，这是我认为优先级最高的外部实验。

不要再筛选 PDE。

直接使用之前保留的第二个候选，例如：

[
\boxed{\text{Allen--Cahn}}
]

作为外部 replication。

目的不是证明“Allen–Cahn 也一定阳性”，而是测试：

[
\boxed{
F_{\rm raw}
\rightarrow
F_{\rm se}^{GN}
\rightarrow
H_{\rm red}^{exact}
}
]

这一关系是否跨 PDE。

建议：

### Development

3–5 seeds。

只解决：

- forward stability；
- center convergence；
- exact Hessian；
- solver。

禁止根据 (D) 选择配置。

### 独立 confirmation

推荐：

[
10\text{ seeds}.
]

primary 仍然使用 paired：

[
D=E_{\rm raw}-E_{\rm SAEPS}.
]

但 Allen–Cahn 必须有**新的独立 protocol lock**。

不能直接把 Burgers 的 numerical thresholds 当作已经验证的 Allen–Cahn protocol 而不做 development。

------

# Phase E — 最终 two-parameter validation

这是当前论文还明显缺失的一块。

推荐继续使用一个 genuinely coupled 两参数 PDE，例如现有 CRD，如果 development 确认 coupling 足够非平凡。

参数：

[
\lambda=(\lambda_1,\lambda_2).
]

核心对象：

[
F_{\rm raw},
\qquad
F_{\rm se}^{GN},
\qquad
H_{\rm red}^{exact,\gamma}.
]

这里不要再用 coordinatewise (\eta_j) 作为 primary。

使用稳定 generalized eigenproblem：

# [ F_{\rm se}v

\eta
(F_{\rm raw}+\tau I)v.
]

并规范化：

[
v^T(F_{\rm raw}+\tau I)v=1.
]

研究：

- retained direction；
- absorbed direction；
- condition number；
- coupling；
- generalized eigenvectors。

小网络可以直接计算 exact reduced Hessian，然后验证：

[
v^TH_{\rm red}^{exact}v
]

是否和：

[
v^TF_{\rm se}^{GN}v
]

一致。

建议：

- development 3–5 seeds；
- confirmation 10 seeds。

代表 seed 的 2D nonlinear surface 只做：

[
1\text{--}3
]

个预注册 seed，不要每个 seed 都做 (5\times5)。

------

# Phase F — Practical scalability

这是现在最明显的工程短板。

当前 solver 需要：

[
n_\theta
]

次 basis JVP 来得到 exact diagonal，因此只适合 small-network validation。

下一步真正值得研究的是：

> 如何在不显式进行 (n_\theta) basis JVP 的情况下获得足够好的 preconditioning。

比较至少：

1. no scaling；
2. exact diagonal —— small reference only；
3. stochastic Hutchinson diagonal；
4. layer-wise/block diagonal；
5. cheap empirical scaling；
6. 可行的话 low-rank / randomized preconditioner。

### Scaling grid

网络：

[
n_\theta:
10^2,\ 10^3,\ 10^4,\ 10^5
]

不一定每一级都训练完整 PINN，可以复用 checkpoint 做 solver benchmark。

同时变化 residual dimension：

[
m.
]

报告：

- wall time；
- JVP count；
- VJP count；
- iterations；
- memory；
- curvature error；
- solver failure rate。

特别报告：

[
\frac{
T_{\rm SAEPS}
}{
T_{\rm nonlinear\ reoptimization}
}.
]

这个阶段对于 JCP 很重要。

------

# Phase G — Noise × sparsity robustness

这应该在 core confirmation 成功以后做，而不是之前。

建议：

[
\sigma
\in
{0,\text{medium},\text{high}}
]

以及 observation fraction：

[
f
\in
{1.0,0.5,0.2}.
]

即：

[
3\times3=9
]

cells。

每 cell：

[
5\text{ seeds}
]

作为 descriptive stress test。

不需要 45 个 case 都算完整 nonlinear profile。

所有 cell 至少计算：

[
F_{\rm raw},
\quad
F_{\rm se},
\quad
\eta,
\quad
\text{stationarity},
\quad
\text{solver status}.
]

只在三个预注册 anchor cells：

- clean/full；
- medium；
- noisy+sparse；

额外做 exact reduced Hessian。

这样计算量会合理很多。

------

# Phase H — Architecture robustness

建议三种：

[
\text{narrow / nominal / wide}.
]

每种：

[
5\text{ seeds}.
]

主要回答：

> SAEPS 的 state absorption 是否依赖某一个网络宽度？

尤其关注之前理论上非常重要的问题：

当：

[
J_\theta
]

越来越接近 full row rank 时，

[
\gamma\rightarrow0
]

可能导致：

[
F_{\rm se}\rightarrow0.
]

所以需要同时报告：

- (m)；
- (n_\theta)；
- singular spectrum；
- effective rank；
- (F_{\rm se}/F_{\rm raw})；
- (\gamma) sweep。

这会正面回应 overparameterization degeneracy。

------

# Phase I — (\gamma) family，不再把 (\gamma) 当“魔法超参数”

现在论文应该明确：

[
F_{\rm se}=F_{\rm se}(\gamma).
]

建议固定 checkpoints 后做 cheap sweep：

[
\gamma_\alpha
\in
{
10^{-12},
10^{-10},
10^{-8},
10^{-6},
10^{-4},
10^{-2},
1
}.
]

报告：

[
F_{\rm se}(\gamma),
\quad
\eta(\gamma),
\quad
I_{\rm GN}(\gamma),
]

以及 solver conditioning。

在 small networks 上同时算：

[
H_{\rm red}^{exact,\gamma}.
]

重点不是找“最好 (\gamma)”，而是研究：

> SAEPS 所定义的 state-adaptation scale 如何随 damping 改变。

------

# Phase J — 最终论文 evidence package

只有前面的必要阶段完成以后才开始重写 manuscript。

论文核心可以组织成：

### Result 1 — Mechanism

Raw fixed-state curvature 严重高估 state-adapted curvature。

### Result 2 — SAEPS

SAEPS 删除 neural-state tangent adaptability，并显著接近 exact reduced geometry。

### Result 3 — Approximation limit

SAEPS 是 reduced Gauss–Newton approximation，而非 exact Hessian surrogate。

### Result 4 — Adequacy

Second-order directional correction 可以诊断什么时候 GN approximation 可能不够准确。

### Result 5 — External validity

跨第二 PDE / multi-parameter / robustness。

### Result 6 — Computation

Matrix-free realization 与 scalability。

------

# 推荐的优先级

不要一口气把所有实验全开。

建议顺序严格是：

[
\boxed{
\text{v3.6 confirmation}
}
]

↓

[
\boxed{
\text{freeze + scientific adjudication}
}
]

↓

如果 `SUPPORTED`：

[
\boxed{
\text{second scalar replication}
}
]

↓

[
\boxed{
\text{two-parameter validation}
}
]

↓

[
\boxed{
\text{scalability}
}
]

↓

[
\boxed{
\text{noise/sparsity + architecture}
}
]

而 second-order indicator / directional-HVP 研究可以和 external replication 并行 development。

如果 v3.6 `NOT_SUPPORTED`，则：

[
\boxed{
\text{立即停止外部扩展，先进行 confirmation postmortem。}
}
]

# 

```text

```

