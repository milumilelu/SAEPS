> **V5 effective-protocol notice（2026-08-23，科学执行前）**
>
> 本文件在commit `126f125a91b4e0df654e8aa7dacb68fded68c3a8`中的LF-normalized版本（SHA-256 `6abb0864cddb40fd63f29a24d97004c539727744d35b2ac9821888d0a90d0f12`）是parent protocol；用户提供的pre-normalization source bytes SHA-256为`274b1179ace363cdd61897c05c43001a9435cbbf2f8d0caa58ef09a7dd796b52`。V5的唯一有效协议是该parent protocol与`docs/v5/V5_PROTOCOL_AMENDMENT_001.md`的有序组合；如二者冲突，pre-execution amendment优先。有效协议身份及全部哈希记录在`docs/v5/V5_PROTOCOL_FREEZE.md`与`configs/v5/V5_GOVERNANCE_FREEZE.json`。本通知不授权任何科学执行。

基于仓库现在的 **V4 最终审计、Burgers/Allen–Cahn confirmation、controlled mechanism、two-parameter recovery、scalability 和 robustness**，我会把后续工作收缩得很明显。

先给结论：**现在不需要再铺 PDE、不需要再扩 noise×sparsity、不需要再堆 scalar seeds。真正影响 JCP 投稿的只剩 3 个科学问题 + 1 个低成本数值问题：**

1. **把 nonlinear reduced-profile 这条证据链处理干净**：要么验证，要么明确删除这个强 claim。
2. **完成一个真正 untouched 的两参数矩阵 confirmation**。
3. **补 finite-(\gamma) / effective-rank 敏感性，证明不是挑了一个好看的 (\gamma)**。
4. **给现有 scalability 再补一个 residual dimension (m) 方向的轻量 scaling audit**。

如果严格执行下面这个 V5，我认为已经是“最小 JCP 补实验集”，继续加第三个 PDE 或更多 robustness 的边际价值很低。

------

# 一、当前实验结果 → JCP 投稿 Gap Audit

JCP 官方 scope 对计算方法论文明确要求在已有方法存在时进行比较，并讨论 **efficacy、robustness、computational complexity 和 reproducibility**；同时它明确欢迎位于 predictive simulation 与 machine learning 交界的方法。([Elsevier 商店](https://shop.elsevier.com/journals/journal-of-computational-physics/0021-9991?utm_source=chatgpt.com))

你现在的仓库在 reproducibility 上已经明显不是短板，真正的问题是**科学 claim 的闭环程度**。

| 审稿人会问的问题                                             | 当前仓库证据                                                 | 我的判定                                   | V5 是否补                                          |
| ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------ | -------------------------------------------------- |
| SAEPS 是否真的优于 fixed-state/raw curvature？               | Burgers 12/15 planned wins，12 个 valid 全赢；Allen–Cahn 9/10 planned wins，9 个 valid 全赢 | **已满足**                                 | 不补                                               |
| 是否跨 PDE？                                                 | Burgers + Allen–Cahn 独立 confirmation 均 supported          | **已满足**                                 | 不补第三 PDE                                       |
| SAEPS 是否近似 exact finite-(\gamma) reduced curvature？     | Burgers median error 7.50%；Allen median 27.86%              | **比较优势成立，但绝对精度 PDE-dependent** | 不重新证明，正文如实写                             |
| SAEPS 是否预测真正重新优化后的 nonlinear reduced objective？ | Allen gamma-matched profile 仅 1/10 pass；历史 gamma-profile 也出现 convergence failure | **当前未建立**                             | **必须处理**                                       |
| 多参数全矩阵理论是否成立？                                   | V4.6 engineering 3/3 PASS，但 held-out 1/2，confirmation 105–114 未运行 | **核心缺口**                               | **必须补**                                         |
| tangent-overlap mechanism 是否无条件成立？                   | valid seeds 上 6/6 monotonic、median Spearman=1，但 planned denominator 仅 6/10 | **conditional evidence，不能作强验证**     | 不补，降级 claim                                   |
| 对 (\gamma) 是否敏感？                                       | 历史有 gamma development，但当前主结果仍基于固定 finite-(\gamma) | **审稿风险仍存在**                         | **低成本补**                                       |
| 对噪声/稀疏性是否稳健？                                      | 45/45 records，43 valid；exact anchor 14/14 SAEPS wins       | **足够作为 robustness**                    | 不再扩                                             |
| 对网络 architecture 是否稳健？                               | width8 5/5，width16 4/5，width32 0/5 center-valid            | **wide architecture 未验证**               | 不作为 V5 blocker，明确 limitation                 |
| 能否扩展到实际参数量？                                       | matrix-free 101→100001 parameters 均 PASS                    | **工程 scaling 已较强**                    | 只补 (m)-scaling                                   |
| 仓库是否可复现？                                             | 80 tests PASS、hash/integrity/rebuild 全通过                 | **已满足**                                 | 只做 submission packaging                          |
| 与最近 inverse-PINN diagnostic 工作区别是否清楚？            | 当前主要 baseline 是 raw/frozen                              | **论文 framing 仍需强化**                  | 用 V5 profile 同时输出 frozen baseline，不另铺算法 |

V4 最终审计自己的判断其实和这个高度一致：Burgers、Allen scalar confirmation 已经 supported，但 controlled confirmation 未 supported、two-parameter confirmation 未测试、Allen profile reliability 很弱、wide architecture 没有 valid center，所以最终只能 `PARTIALLY_SUPPORTED / NOT_READY_FOR_FULL_JCP_CLAIM`。

------

## 1. Scalar comparative efficacy：已经达到论文级，不要再跑

Burgers v4.2 是现在最强的主证据：15 planned、12 valid、12 planned strict wins，median (D=27.6363)，exact one-sided sign-test (p=2.44\times10^{-4})。更重要的是所有 12 个 valid seeds 上，SAEPS 都比 raw 更接近 exact finite-(\gamma) reduced Hessian。

Allen–Cahn 又独立重复了这个现象：10 planned、9 valid、9 planned strict wins，median (D=20.0065)，(p=0.001953)，9 个 valid seeds 全部 SAEPS 胜出。

所以 V5 **禁止再做第三个 scalar PDE 来证明同一件事情**。再跑一个 reaction-diffusion、KdV 或 Darcy scalar，对 JCP 的增益远小于补上 multi-parameter。

不过正文必须同时报告 absolute error：

- Burgers median (E_{\rm SAEPS}\approx7.50%)；
- Allen–Cahn median (E_{\rm SAEPS}\approx27.86%)。

因此不能写成“SAEPS accurately recovers the exact Hessian”，更合理的是：

> SAEPS-GN substantially reduces the error of fixed-state curvature relative to the exact finite-(\gamma) reduced curvature, while the remaining Gauss–Newton approximation error is PDE- and checkpoint-dependent.

------

# 二、当前真正最大的 Gap：nonlinear profile

这是我现在最关心的一项。

Allen–Cahn confirmation 中，虽然 curvature comparative endpoint 非常漂亮，但 **gamma-matched nonlinear profile bridge 只有 1/10 planned seeds 通过**。

更早的 gamma-profile development 也已经暴露过同类问题：在 seed20 中，exact gamma-matched Hessian reduction 本身 PASS，但 profile 在最细 (h) 上没有达到 curvature convergence / optimization-accuracy convergence，CG gate 也失败。

这意味着目前下面两句话必须严格区分：

[
\boxed{\text{SAEPS approximates local finite-\gamma reduced curvature}}
]

已经有较好证据。

而

[
\boxed{\text{SAEPS predicts the nonlinear reoptimized reduced profile}}
]

**目前没有证据支持。**

这不是小问题，因为后一句实际上比前一句强很多。

### 对论文的处理原则

V5 不应该为了把 nonlinear profile “跑阳性”而大规模重新调参。

只需要做一次专门的、数值上严谨的 profile-bridge resolution：

- 如果成功，就作为漂亮的 secondary validation；
- 如果仍失败，直接把论文主 claim 缩回 **local finite-(\gamma) reduced curvature**。

这样科学上完全成立，而且比不断追 profile 阳性更可信。

------

# 三、第二个真正的 JCP Blocker：two-parameter

V4.6 本身并不是方法完全失败。

engineering seeds 100–102 三个全部 binding-valid，exact reduction、solver、explicit/matrix-free agreement 都通过，而且 coupling 都很强，约 (0.82)–(0.88)。

真正的问题是 executable freeze 后的 recovery held-out：

- seed115：center invalid；
- seed116：完整 PASS；
- 因而只得到 1/2 binding-valid；
- confirmation 未授权。

仓库也明确记录了 seeds 105–114 **保持未运行并永久停止**，因此 two-parameter comparative hypothesis 实际上从来没有被检验。

如果论文数学形式仍然以

[
\lambda\in\mathbb R^p
]

作为一般方法，那么这会是审稿人非常容易抓住的一点：

> “所有正式 confirmation 都是 scalar，为什么我要相信 Schur/reduced geometry 在 coupled parameter space 中还能工作？”

所以 **V5 两参数 confirmation 是最高优先级实验。**

------

# 四、controlled mechanism：不要再救

V4.5 的结果是一个典型的“科学机制条件成立，但实验可用性不足”：

- 10 planned；
- 6 binding-valid；
- 这 6 个全部 monotonic；
- median valid-seed Spearman = 1；
- 但 planned monotonic 只有 6/10，因此 locked result 是 `NOT_SUPPORTED`。

我不建议 V5 再开一个 controlled confirmation。

论文可以很清楚地说：

> Conditional on a valid stationary checkpoint, the controlled tangent-overlap experiment exhibits the predicted monotone behavior; however, the preregistered planned-denominator mechanism gate was not satisfied because of checkpoint availability.

这反而比较有说服力。

继续补到 8/10 或 10/10，会很容易产生“为了把旧阴性救成阳性”的观感。

------

# 五、architecture：width32 的 0/5 不需要现在硬救

V4.8 已经做得够诚实：

- width8：5/5 binding-valid；
- width16：4/5；
- width32：0/5；
- 所有 width32 都死在 state-center gate，而不是 SAEPS curvature gate。

所以目前能支持的是：

> Wide-network scientific validity was not tested because no checkpoint satisfied the preregistered local-center criterion.

而不是：

> SAEPS fails on wide networks.

这个 distinction 一定要保留。

我不会把“重新调 width32 PINN 直到能训练出来”放进最小 V5。那会迅速变成另一个优化算法项目。

------

# 六、scalability：已经不错，只差 (m) 方向

V4.7 已经覆盖：

[
n_\theta=101,;1001,;10001,;50001,;100001
]

五个 scale，全部 solver PASS。

最大 (100001)-parameter case：

- CG 12 iterations；
- solve time ≈ 5.04 s；
- verified relative residual (5.26\times10^{-12})。

这个结果足够进入 JCP 主文。

唯一容易被问的是：所有 scaling cases 的 residual dimension 都是

[
m=213.
]

所以现在只需要补一个非常廉价的 (m)-scaling，不要重新训练大批网络。

------

# 七、recent competitor 带来的 framing 压力

这个问题在最近一周变得更重要。

2026 年 8 月刚出现的 Zhang & Tao 预印本 *Beyond Field Accuracy* 同样做 inverse-PINN post-training diagnosis；它的核心之一是**冻结 learned field 后的 residual profile / score displacement**，并且已经展示了三个 scalar PDE，以及一个 coupled two-parameter Darcy matrix check。([arXiv](https://arxiv.org/abs/2608.15373?utm_source=chatgpt.com))

所以 SAEPS 不能只宣传：

> “我们也提出一个 inverse-PINN residual diagnostic。”

差异必须变成：

> frozen-state sensitivity/profile
> **vs.**
> state-adapted tangent elimination
> **vs.**
> exact finite-(\gamma) reduced geometry / reoptimized profile.

因此 V5 不需要大规模增加竞争算法；只要在**同一个 checkpoint、同一个 residual metric、同一个 parameter perturbation**上把：

[
\text{raw/frozen}
\quad\rightarrow\quad
\text{SAEPS}
\quad\rightarrow\quad
\text{exact/reoptimized}
]

这三层放在一起，方法差异就非常清楚。

------

# 八、我建议 V5 之后论文的核心 claim

如果 V5 two-parameter confirmation 成功，我建议把全文主 claim 锁成：

> **SAEPS is a local finite-damping reduced-curvature diagnostic for inverse PINNs. At a numerically stationary checkpoint, it eliminates the residual response that can be locally absorbed by neural-state adaptation and provides a substantially better approximation to the exact finite-(\gamma) reduced curvature than fixed-state Gauss–Newton sensitivity.**

然后实验 claim：

> The comparative effect is confirmed on Burgers and externally replicated on Allen–Cahn, examined under noise and observation sparsity, extended to a coupled two-parameter geometry, and implemented matrix-free up to (10^5) neural-state parameters.

**只有 V5 profile bridge 通过时**，才再增加：

> The local curvature prediction is also consistent with directly reoptimized gamma-matched reduced profiles.

否则这句不要出现。

------

# SAEPS V5 最小 JCP Gap-Closure Task Book

下面这份就是我建议真正执行的 V5。

------

## V5 总目标

V5 只回答四个问题：

[
\boxed{
\begin{aligned}
Q_1 &: \text{finite-}\gamma\text{ 结果是否依赖一个特殊的 }\gamma?\
Q_2 &: \text{exact reduced Hessian 与 nonlinear profile 是否数值一致?}\
Q_3 &: \text{SAEPS comparative advantage 是否扩展到 coupled }p=2?\
Q_4 &: \text{matrix-free cost 对 residual dimension }m\text{ 如何变化?}
\end{aligned}}
]

除此之外一律不扩实验面。

------

# V5.0 — Governance Freeze

**目的：先冻结 V5，后看结果。**

必须新建：

```text
docs/v5/V5_JCP_MINIMAL_PROTOCOL.md
docs/v5/V5_SCIENTIFIC_GATES.md
docs/v5/V5_SEED_REGISTRY.json
docs/v5/V5_SEMANTIC_GATE_GRAPH.json
configs/v5/
outputs/runs/v5/
docs/evidence/v5/
```

历史结果保持只读：

```text
v2
v3.x
v4.1--v4.8
```

尤其禁止：

```text
v4.2 Burgers confirmation 55--69
v4.4 Allen confirmation 75--84
v4.5 controlled confirmation 90--99
v4.6 stopped confirmation 105--114
```

不得产生诸如：

```text
corrected_v4
revised_v4
recomputed_v4
```

这种结果。

### V5 科学状态统一为

```text
SUPPORTED
PARTIALLY_SUPPORTED
NOT_SUPPORTED
INCONCLUSIVE
```

工程状态独立：

```text
PASSED
FAILED
BLOCKED
```

------

# V5.1 — Finite-(\gamma) / Effective-Rank Audit

### 优先级

**Mandatory，但不需要新训练。**

这是性价比最高的补实验。

### Checkpoint

只允许使用已有 **development / engineering checkpoints**，不要动正式 scalar confirmation cohort。

例如按照确定性的 seed-order rule：

- Burgers：从已有 engineering pool 中取前 3 个 binding-valid checkpoints；
- Allen–Cahn：从 seeds 70–74 中取前 3 个 binding-valid checkpoints。

选择标准只能是：

```text
binding-valid
seed number
```

禁止根据：

```text
eta
D
E_SAEPS
E_raw
figure appearance
```

选择。

### Gamma family

令

[
\gamma=\alpha\lambda_{\max}(J_\theta^TJ_\theta)
]

使用：

[
\boxed{
\alpha\in
{10^{-10},10^{-8},10^{-6},10^{-4},10^{-2},1,10^2}
}
]

其中保留当前 nominal value。

### 每个 checkpoint × gamma 保存

[
F_{\rm raw}
]

[
F_{\rm se}^{GN}(\gamma)
]

[
H_{\rm red}^{exact,\gamma}
]

[
E_{\rm SAEPS}(\gamma),
\qquad
E_{\rm raw}(\gamma)
]

[
\eta(\gamma)=
\frac{F_{\rm se}^{GN}(\gamma)}
{F_{\rm raw}}
]

以及 (J_\theta) singular spectrum。

定义 damping-dependent effective rank：

# [ r_{\rm eff}(\gamma)

\sum_i
\frac{\sigma_i^2}
{\sigma_i^2+\gamma}.
]

同时保存：

[
m,\qquad n_\theta,\qquad r_{\rm eff}.
]

### 必须验证的数值极限

对 GN quantity：

[
F_{\rm se}^{GN}(\gamma)
\rightarrow
F_{\rm raw}
\qquad \gamma\rightarrow\infty.
]

并展示小-(\gamma) 下 state absorption 增强的趋势。

注意不要声称 exact Hessian 也必然趋向 (F_{\rm raw})，因为 exact Hessian 仍包含 residual second-order terms。

### V5.1 不设“必须 SAEPS 赢”的科学 gate

它是 sensitivity audit。

即使发现 SAEPS 只在很窄的 (\gamma) 范围内有优势，也必须原样报告。

**绝对禁止根据该 sweep 重新选择 nominal (\gamma)。**

------

# V5.2 — Nonlinear Profile Bridge Resolution

### 优先级

**Mandatory for resolving the claim，but secondary scientifically.**

目的不是证明 SAEPS。

首先验证：

[
H_{\rm profile}^{\gamma}
\stackrel{h\to0}{\longrightarrow}
H_{\rm red}^{exact,\gamma}.
]

如果这一步本身不成立，说明 nonlinear-profile numerical bridge 不可靠，此时不应拿 profile 判断 SAEPS。

------

## V5.2A — Profile engineering

只用旧 Allen development seeds `70--74`。

不得使用 confirmation 75–84 调 profile optimizer。

定义真正与 finite-(\gamma) reduction 对应的 objective：

# [ \Phi_\gamma(s)

\min_\theta
\left[
\frac12
|\bar r(\theta,q_0+s)|^2
+
\frac{\gamma}{2}
|\theta-\theta_0|^2
\right].
]

这里：

- (q=\log\lambda)；
- ((\theta_0,q_0)) 是 frozen checkpoint；
- residual/collocation set 必须与 SAEPS 完全相同；
- 必须保存 diagnostic-set hash。

对每个 (s)，**独立从 (\theta_0) warm start**，禁止：

```text
-h -> ... -> +h
```

顺序 continuation 作为 primary。

### Radius

开发后冻结：

[
h\in
{0.04,0.02,0.01,0.005}.
]

计算：

# [ H_{\rm profile}(h)

\frac{
\Phi_\gamma(h)-2\Phi_\gamma(0)+\Phi_\gamma(-h)
}{h^2}.
]

### 优化器选择规则

可以在 development 中比较：

- strict L-BFGS；
- Newton-CG / trust-region Newton-CG，如果当前实现支持；
- 更严格 gradient tolerance。

但**选择 optimizer 只能看**：

- profile-state stationarity；
- optimization residual；
- (\pm h) symmetry；
- (H_{\rm profile}) 对 (h) 的 convergence；
- 与 exact Hessian 的数值一致性。

不得看：

[
E_{\rm SAEPS}<E_{\rm raw}
]

来选择 optimizer。

------

## V5.2B — Fresh held-out bridge

新 seeds：

```text
200, 201, 202, 203, 204
```

5 个。

这不是新的 primary efficacy confirmation，所以 5 个足够。

每个 seed：

1. train/freeze stationary checkpoint；
2. compute exact finite-(\gamma) reduced Hessian；
3. compute SAEPS-GN；
4. compute raw；
5. run frozen profile；
6. run gamma-matched reoptimized profile at all four (h)。

### Profile bridge engineering success

对一个 seed 定义：

```text
PROFILE_VALID
```

需要：

- center PASS；
- all ±h optimization PASS；
- exact Hessian PASS；
- smallest two radii curvature finite；
- smallest-radius profile curvature 与 exact Hessian relative error ≤ 10%；
- last-two-radius relative curvature change ≤ 5%。

阈值必须在 200 之前 freeze。

### Scientific interpretation

如果：

[
\ge4/5
]

PROFILE_VALID 且 profile→exact 一致：

```text
PROFILE_BRIDGE_SUPPORTED
```

可以在论文中声称 secondary nonlinear-profile consistency。

如果：

```text
<4 valid
```

则：

```text
INCONCLUSIVE
```

如果有充分 valid profiles，但 profile curvature 系统性不收敛到 exact Hessian：

```text
PROFILE_BRIDGE_NOT_SUPPORTED
```

然后直接**删除 nonlinear-profile-equivalence claim**。

不要再创建 V5.2C 去救。

------

# V5.3 — Coupled Two-Parameter Exact Geometry Confirmation

这是整个 V5 的**最重要实验**。

### Benchmark

禁止重新筛选 PDE。

直接沿用 V4.6 已经 engineering-pass 的：

```text
same coupled PDE
same parameterization
same residual construction
same width-6 architecture family
```

因为 V4.6 engineering 100–102 已经显示 3/3 binding chain 和 nontrivial coupling 均成立。

------

## V5.3A — Center-only development

新 seeds：

```text
210, 211, 212
```

只允许解决 V4.6 真正失败的问题：

> stationary center availability.

可以改：

- optimizer duration；
- deterministic L-BFGS settings；
- stationarity stopping；
- numerical solver tolerances。

禁止开发阶段使用：

[
D,\quad
E_{\rm raw},\quad
E_{\rm SAEPS},
]

以及 favorable generalized eigenvalues。

reuse V4.6 的：

- nontrivial coupling gate；
- exact finite-(\gamma) semantics；
- explicit/matrix-free agreement；
- solver validity。

### Development gate

要求：

[
3/3
]

binding-valid。

否则停止 V5.3。

------

## V5.3B — Frozen executable held-out

seeds：

```text
213, 214
```

在 byte-frozen executable 上运行。

要求：

[
2/2
]

binding-valid。

如果只有 1/2：

```text
V5.3 = BLOCKED_BY_CENTER_AVAILABILITY
```

**不得运行 confirmation。**

这时论文只能保持 scalar claim。

------

## V5.3C — Untouched confirmation

只有 A+B 全通过后授权：

```text
215,216,217,218,219,
220,221,222,223,224
```

共 10 seeds。

------

# V5.3 Primary matrix quantities

对

[
p=2
]

保存：

[
F_{\rm raw},
\qquad
F_{\rm se}^{GN},
\qquad
H_{\rm red}^{exact,\gamma}.
]

不要用 coordinatewise (\eta_j) 作为 primary。

------

## Coordinate-stabilized comparison

定义：

[
B=F_{\rm raw}+\tau I.
]

(\tau) 必须沿用已有 locked rule；如果 V4.6 没有适合的 rule，则必须在 V5.3 development 前固定，禁止按 confirmation 结果选择。

定义 whitened matrix：

# [ \widetilde A

B^{-1/2}AB^{-1/2}.
]

然后：

# [ E_{\rm SAEPS}^{(2)}

\frac{
|
B^{-1/2}
(F_{\rm se}^{GN}-H_{\rm red}^{exact,\gamma})
B^{-1/2}
|*F
}{
|
B^{-1/2}
H*{\rm red}^{exact,\gamma}
B^{-1/2}
|_F+\epsilon
},
]

# [ E_{\rm raw}^{(2)}

\frac{
|
B^{-1/2}
(F_{\rm raw}-H_{\rm red}^{exact,\gamma})
B^{-1/2}
|*F
}{
|
B^{-1/2}
H*{\rm red}^{exact,\gamma}
B^{-1/2}
|_F+\epsilon
}.
]

paired endpoint：

# [ D^{(2)}

## E_{\rm raw}^{(2)}

E_{\rm SAEPS}^{(2)}.
]

这比直接比较两个矩阵的 coordinatewise entry 更适合作为多参数 primary。

------

## Generalized geometry secondary endpoint

求：

# [ F_{\rm se}^{GN}v_k

\eta_k Bv_k
]

并归一化：

[
v_k^TBv_k=1.
]

然后计算 exact directional curvature：

# [ \eta_k^{exact}

v_k^T
H_{\rm red}^{exact,\gamma}
v_k.
]

报告：

- (\eta_k)；
- (\eta_k^{exact})；
- retained/absorbed direction；
- eigengap；
- generalized eigenvector angle，仅在 eigengap 足够时解释。

不要在近简并情况下强行解释 eigenvectors。

------

# V5.3 Confirmation gate

planned denominator：

[
10.
]

强 `SUPPORTED` 要同时满足：

[
n_{\rm valid}\ge9,
]

[
n_{\rm planned-win}\ge9/10,
]

[
\operatorname{median}(D^{(2)})>0,
]

以及 exact one-sided sign test：

[
p\le0.05.
]

所有 invalid planned seeds：

[
\boxed{\text{count as planned non-wins}}
]

不得替换。

如果：

[
n_{\rm valid}<9
]

则：

```text
INCONCLUSIVE
```

而不是缩小 planned denominator。

如果 valid coverage 足够但 comparative gate 失败：

```text
NOT_SUPPORTED
```

此时**禁止再加第三个 multi-parameter PDE 来救结论**。

------

# V5.4 — Residual-Dimension Scalability Complement

这部分很轻。

V4.7 已经很好地覆盖了 (n_\theta)，但固定了 (m=213)。

所以只补：

[
n_\theta\in
{10^3,10^4,10^5}
]

以及：

[
m\in
{213,853,3413}.
]

形成：

[
3\times3=9
]

个 solver conditions。

每个 timing：

[
3
]

次独立重复。

总共只有：

[
27
]

个 solver timing evaluations。

不用重新训练。

### 保存

- wall time；
- solve time；
- CG iterations；
- JVP count；
- VJP count；
- verified residual；
- peak memory，如果运行环境可可靠获取；
- failure status。

不要从三个 (m) 点拟合一个过度精确的“理论复杂度指数”。

论文只展示 empirical scaling + analytic operator complexity。

------

# V5.5 — Baseline consolidation

不增加新训练。

在 V5.2 的 5 个 held-out scalar seeds 上，同时画：

[
\Phi_{\rm frozen}
]

[
\Phi_{\rm SAEPS}^{quadratic}
]

[
\Phi_{\rm reopt}^{\gamma}.
]

以及 curvature：

[
F_{\rm raw},
\qquad
F_{\rm se}^{GN},
\qquad
H_{\rm red}^{exact,\gamma},
\qquad
H_{\rm profile}^{\gamma}.
]

这样自然形成最有说服力的 ablation：

```text
freeze neural state
        ↓
locally eliminate neural state
        ↓
exact finite-gamma state adaptation
        ↓
actual nonlinear reoptimization
```

这也正好把 SAEPS 与最近的 frozen-field inverse-PINN diagnostics 区分开来，而不需要再搞十几个 PINN optimizer baseline。近期相关预印本确实已经证明 frozen-field profile/score 能在多个 PDE 和 coupled two-parameter case 中提供有用的 parameter diagnostic，所以 SAEPS 最应该证明的增量就是 **state adaptation elimination 带来了什么**。([arXiv](https://arxiv.org/abs/2608.15373?utm_source=chatgpt.com))

------

# V5.6 — Final JCP Evidence Audit

必须生成：

```text
V5_FINAL_JCP_AUDIT_REPORT.md
docs/evidence/v5_final_audit.json
docs/evidence/v5_final_validation.json
paper_artifacts/
```

最终表格至少包含：

| Evidence                           | Status                                         |
| ---------------------------------- | ---------------------------------------------- |
| Burgers scalar comparative         | inherited SUPPORTED                            |
| Allen scalar replication           | inherited SUPPORTED                            |
| noise/sparsity robustness          | inherited DESCRIPTIVE + exact-anchor support   |
| controlled mechanism               | inherited NOT_SUPPORTED / conditional evidence |
| gamma family                       | V5 result                                      |
| nonlinear profile bridge           | V5 result                                      |
| two-parameter comparative geometry | V5 result                                      |
| (n_\theta) scalability             | inherited PASSED                               |
| (m) scalability                    | V5 result                                      |
| wide architecture                  | inherited UNTESTED due invalid centers         |

历史阴性不能被 V5 的新阳性覆盖或删除。

------

# 九、明确禁止 V5 做的实验

为了不再膨胀，我建议在任务书里直接写死：

- **不做第三个 scalar PDE。**
- **不重跑 Burgers 55–69 或 Allen 75–84。**
- **不重新做 controlled confirmation。**
- **不把 noise×sparsity 从 60 runs 再扩成几百 runs。**
- **不重新扫一整套 architecture。**
- **不为了 width32 0/5 临时更换 validity threshold。**
- **不加入 real data 作为 JCP 强制项。**
- **不做 20–50 seed 的 optics-driven 扩样本。**
- **不比较十几个 PINN training algorithms。**
- **不根据 (\gamma) sweep 重新选最好看的 nominal (\gamma)。**
- **不因为 two-parameter confirmation 失败而再换 PDE。**

------

# 十、V5 预计新增计算量

按这个设计，新增量其实不大。

| Phase                              | 新 base trainings | 主要额外计算                                   |
| ---------------------------------- | ----------------- | ---------------------------------------------- |
| V5.1 gamma audit                   | 0                 | 约 6 checkpoints × 7 gamma                     |
| V5.2 profile                       | 5                 | 约 40 个 ±h reoptimizations                    |
| V5.3 two-param development/heldout | 5                 | exact geometry                                 |
| V5.3 confirmation                  | 10                | 10 个 matrix confirmations                     |
| V5.4 scaling                       | 0                 | 27 solver timings                              |
| **总计**                           | **20**            | 约 40 profile reopts + 轻量 solver diagnostics |

而且存在早停：

如果 seeds 210–214 的 two-parameter center chain 过不了，就**不会运行后面的 10 confirmation seeds**。

所以最坏也就是约 20 个新训练，远小于重新铺一套 benchmark。

------

# 十一、V5 后的投稿决策树

### 情形 A：最好，也是我建议瞄准的结果

- scalar 两 PDE：已有 SUPPORTED；
- gamma family：结论不依赖单一点；
- two-param：SUPPORTED；
- profile：SUPPORTED 或至少清楚解释；
- scalability：完整。

那么可以形成一个相当标准的 **JCP methods paper**。

------

### 情形 B：two-param 成功，profile 仍失败

这其实**完全可以投稿 JCP**。

只需要把题目和 abstract 从：

> predicting the nonlinear reduced objective

改成：

> approximating the exact local finite-damping reduced curvature.

profile failure 作为 limitation。

我认为这是非常可接受的结果。

------

### 情形 C：profile 成功，two-param 因 center availability 无法 confirmation

论文证据仍然不错，但 general (p)-parameter claim 会比较虚。

此时要么：

1. 把正文明确限制为 scalar inverse parameter reliability；
2. general matrix formulation 作为理论 extension，不声称 empirical validation。

JCP 风险会明显上升。

------

### 情形 D：two-param 有足够 valid seeds，但 SAEPS comparative hypothesis 真失败

不要继续补实验。

这意味着：

> scalar comparative effect is real, but matrix generalization is not empirically supported.

此时应写成 scalar-focused paper，而不是继续扩 benchmark。

------

# 十二、我现在会怎么重构论文故事

现在最值得保留的故事已经不是原稿中那种：

> “我们通过 (\eta) 找到了 state-absorbed / weak / reliable 三种 regime。”

而是：

[
\boxed{
\text{fixed-state curvature}
;\longrightarrow;
\text{state-adapted GN curvature}
;\longrightarrow;
\text{exact finite-}\gamma\text{ reduced curvature}
}
]

其中：

1. Schur/Tikhonov elimination 给出 SAEPS-GN；
2. exact full-Hessian reduced curvature 给出 small-network gold standard；
3. Burgers confirmation 证明比较优势；
4. Allen–Cahn 独立复制；
5. noise/sparsity anchors 说明 robustness；
6. coupled (p=2) 检验矩阵几何；
7. matrix-free 实现说明计算可行性；
8. nonlinear profile 只负责解释“local curvature 是否真的连接到 finite perturbation”，而不是承担主方法成败。

这个故事比最初的 heuristic reliability classification **严谨很多，也更像 JCP 的 numerical-methods paper**。

我会把 **V5.2 profile 和 V5.3 two-parameter** 视为真正的最后科学实验；其余都只是审稿防守性补充。当前仓库的 reproducibility、scalar confirmation、robustness 和 (10^5)-parameter matrix-free scaling 已经没有必要再重复建设。

如果你下一步继续用 Codex 跑实验，我建议直接把上面这份变成仓库里的 `V5_JCP_MINIMAL_PROTOCOL.md`，并把 **V5.3 的 two-parameter gate 设成整个 V5 的最高优先级**。
