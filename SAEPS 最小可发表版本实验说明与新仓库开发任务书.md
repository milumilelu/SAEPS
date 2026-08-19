# SAEPS 最小可发表版本实验说明与新仓库开发任务书

**版本：MVP v1.0**  
**目标：从零建立独立、可复现、可审计的 SAEPS 实验仓库，并完成一套足以支撑论文核心结论的最小实验闭环。**

---

# 1. 项目重新定位

## 1.1 不再采用旧实验逻辑

原稿实验主要试图通过不同 PDE 展示三类诊断状态：

- reliable-local-signal；
- state-absorbed；
- score-misaligned。

这种设计的问题是，不同状态高度依赖训练 checkpoint、网络 architecture、residual weighting、Tikhonov damping 和参数化方式，因此容易变成“不断寻找能够产生目标现象的模型”。

原稿本身已经明确 SAEPS 是训练 checkpoint 上的局部 residual-space 方法，其核心量来自 Tikhonov state elimination，并可解释为 joint Gauss–Newton 矩阵的 Schur complement。 同时，原实验中 state-absorbed 和 score-misaligned targets 对 damping 存在明显敏感性。

因此，新版本不再要求某个 PDE 必须产生某种标签。

---

# 2. 新论文唯一核心问题

论文实验只回答一个主问题：

> **SAEPS 对神经状态切空间的局部消元，能否正确预测固定参数扰动后真正重新优化神经网络状态所形成的 nonlinear reduced objective？**

即验证：

\[
\boxed{
\text{SAEPS local elimination}
\quad\longleftrightarrow\quad
\text{actual nonlinear state reoptimization}
}
\]

这将成为整篇论文最核心的实验命题。

---

# 3. 最小论文主张

MVP 只允许支持以下四项结论。

## Claim 1：线性化层面的数学与数值实现正确

SAEPS 给出的

\[
F_\lambda^{se}
=
J_\lambda^\top
A_\theta^{(\gamma)}
J_\lambda
\]

确实对应消除网络权重增量后的 reduced quadratic curvature。

不宣称这是新的 Schur-complement 数学；创新点是将其用于 inverse-PINN checkpoint 的 state-adaptation audit。

---

## Claim 2：SAEPS 能识别可控的 neural-state absorption

在人为控制 parameter residual direction 与

\[
\operatorname{range}(J_\theta)
\]

夹角的 benchmark 中，retained sensitivity 应随 tangent overlap 系统变化。

该实验负责证明“state absorption”机制，而不再依赖寻找某个碰巧 state-absorbed 的 PDE。

---

## Claim 3：SAEPS 比 raw fixed-network sensitivity 更接近真实 nonlinear reduced profile

比较三种对象：

\[
\text{Frozen network profile}
\]

\[
\text{SAEPS quadratic profile}
\]

\[
\text{State-reoptimized nonlinear profile}.
\]

其中：

- \(F^{raw}\) 应描述 frozen-network profile；
- \(F^{se}\) 应更接近 state-reoptimized profile。

这将是论文最重要的验证结果。

近期 inverse-PINN 参数诊断研究已经系统验证了 frozen-field residual score 与 frozen nonlinear profile 之间的对应关系，并进一步进行了 locked seeds、architecture transfer 和 fresh-noise validation。 因此，新 SAEPS 论文应明确把差异化重点放在 **state-reoptimized profile**，而不是重复 frozen-field diagnosis。

---

## Claim 4：多参数情况下必须分析完整 reduced matrix geometry

对于两个物理参数，验证：

\[
F_\lambda^{se}\in\mathbb R^{2\times2}
\]

的：

- eigenvalues；
- eigenvectors；
- off-diagonal coupling；
- reduced Newton/Gauss–Newton direction；

是否能够预测真正重新优化网络后的二维 reduced geometry。

不再简单地把 joint alignment 拆成若干逐坐标标签。

---

# 4. 明确不做的事情

MVP 第一版暂不承担以下目标：

- 不证明 global identifiability；
- 不建立 posterior uncertainty；
- 不声称 SAEPS 是 parameter-error estimator；
- 不建立通用 reliable / unreliable 阈值；
- 不追求大量 PDE benchmark；
- 不要求出现 score-misaligned benchmark；
- 不做全面 architecture × noise × sparsity × optimizer 全笛卡尔积；
- 不使用真实实验数据作为 MVP 必要条件。

这些可以作为后续扩展，而不能阻塞核心论文。

---

# 5. 整体实验体系

最终只需要三类核心 benchmark。

| Benchmark | 作用 | 是否必须 |
|---|---|---|
| A. Controlled tangent-geometry benchmark | 验证 state absorption 机制 | 必须 |
| B. Scalar inverse-PDE benchmark | SAEPS vs nonlinear reoptimization | 必须 |
| C. Two-parameter inverse-PDE benchmark | 验证完整矩阵与参数耦合 | 必须 |

Noise、sparsity 和 architecture 作为第二级 robustness experiments。

---

# 6. Benchmark A：Controlled Tangent Geometry

## 6.1 基本 PDE

建议继续使用简单线性 parabolic manufactured problem：

\[
u_t-Du_{xx}+cu
=
\lambda q_\alpha(x,t)+s_\alpha(x,t),
\]

\[
(x,t)\in[0,1]\times[0,1],
\]

例如固定：

\[
D=0.05,\qquad c=1,\qquad \lambda^\star=1.
\]

选择一个固定 manufactured truth：

\[
u^\star(x,t).
\]

然后由

\[
s_\alpha
=
u_t^\star
-Du_{xx}^\star
+cu^\star
-\lambda^\star q_\alpha
\]

反推出 forcing，使所有 \(\alpha\) 共享同一个 reference state。

---

## 6.2 不直接人工指定“好”和“坏”source

先建立一个固定 Fourier candidate library，例如：

\[
\mathcal Q
=
\{
\sin(k\pi x)\sin(l\pi t),
\sin(k\pi x)\cos(l\pi t),
\ldots
\}.
\]

在一个明确声明为 **development-only** 的 pilot network 上计算每个 candidate 的 tangent overlap：

\[
\omega(q)
=
\frac{
q^\top P_\theta q
}{
q^\top q
},
\]

其中理想化情况下

\[
P_\theta
=
J_\theta J_\theta^\dagger .
\]

选出：

\[
q_{\parallel}
\]

作为 tangent-explainable source，以及

\[
q_{\perp}
\]

作为较强 transverse source。

然后锁定这两个函数。

不得根据 confirmation seeds 再重新选择。

---

## 6.3 构造连续 source family

归一化两个 source 后构造：

\[
q_\alpha
=
\sqrt{1-\alpha}\,q_\parallel
+
\sqrt{\alpha}\,q_\perp,
\]

取：

\[
\alpha
\in
\{0,0.25,0.5,0.75,1\}.
\]

实验研究：

\[
\alpha
\longrightarrow
\eta^{se}.
\]

论文不必要求严格满足

\[
\eta^{se}=\alpha.
\]

真正需要证明的是：

> 随 residual direction 从 tangent-explainable 转向 transverse，SAEPS retained sensitivity 稳定、单调地增加。

---

## 6.4 输出

核心 Figure：

**Controlled tangent overlap vs retained sensitivity**

横轴：

\[
\alpha
\quad\text{或 measured tangent overlap}.
\]

纵轴：

\[
\eta^{se}.
\]

同时报告 5 个 locked confirmation seeds。

---

# 7. Benchmark B：Scalar Physical Inverse PDE

## 7.1 不提前强制指定最终 PDE

建立两个 candidate：

1. Burgers viscosity；
2. Allen–Cahn / scalar reaction coefficient。

Development stage 只允许依据以下条件选择最终 benchmark：

- classical forward problem 数值稳定；
- observation profile 有清晰局部 minimum；
- PINN 能稳定训练；
- checkpoint 能通过 stationarity gate；
- SAEPS quantities 数值有限且 solver 稳定。

**不能以“哪个模型的 \(\eta^{se}\) 更漂亮”为唯一选择依据。**

未入选模型的 screening 结果保留在 Supplementary Material。

这样可以避免 benchmark cherry-picking。

---

# 8. Scalar benchmark 的 gold-standard experiment

设 trainable coordinate 为：

\[
q=\log\lambda.
\]

获得 checkpoint：

\[
(\theta_0,q_0).
\]

---

## 8.1 Frozen-network profile

固定：

\[
\theta=\theta_0
\]

改变：

\[
q=q_0+s.
\]

计算：

\[
\Phi_{\mathrm{frozen}}(s)
=
\frac12
\|
\bar r(\theta_0,q_0+s)
\|^2.
\]

其局部 curvature 应与：

\[
F^{raw}
=
J_q^\top J_q
\]

相对应。

---

## 8.2 SAEPS quadratic prediction

计算：

\[
F^{se},
\qquad
g^{se}.
\]

构造：

\[
\Phi_{\mathrm{SAEPS}}(s)
=
\Phi_0
+
g^{se}s
+
\frac12F^{se}s^2.
\]

---

## 8.3 真正的 nonlinear state-reoptimized profile

对于：

\[
s\in
\{-0.15,-0.10,-0.05,0,
0.05,0.10,0.15\},
\]

固定：

\[
q=q_0+s.
\]

每个点都**独立从 \(\theta_0\) warm start**，重新优化网络：

\[
\theta^\star(s)
=
\arg\min_\theta
\frac12
\|
\bar r(\theta,q_0+s)
\|^2.
\]

得到：

\[
\Phi_{\mathrm{reopt}}(s)
=
\frac12
\|
\bar r(\theta^\star(s),q_0+s)
\|^2.
\]

不得使用前一个 \(s\) 的结果作为下一个 \(s\) 的初始化，以避免 path dependence。

---

# 9. 最核心的一张论文图

同一坐标系绘制：

\[
\Phi_{\mathrm{frozen}}(s),
\]

\[
\Phi_{\mathrm{SAEPS}}(s),
\]

\[
\Phi_{\mathrm{reopt}}(s).
\]

预期逻辑：

\[
F^{raw}
\leftrightarrow
\text{frozen profile},
\]

而

\[
F^{se}
\leftrightarrow
\text{reoptimized profile}.
\]

如果 SAEPS 有效，这张图应该成为论文最有说服力的结果。

---

# 10. Scalar benchmark 定量指标

从 nonlinear profile 在 \(s=0\) 附近拟合：

\[
\Phi_{\mathrm{reopt}}
\approx
a+bs+\frac12H_{\mathrm{prof}}s^2.
\]

定义：

### Curvature error

\[
E_{\mathrm{SAEPS}}
=
\frac{
|F^{se}-H_{\mathrm{prof}}|
}{
|H_{\mathrm{prof}}|+\epsilon
},
\]

以及：

\[
E_{\mathrm{raw}}
=
\frac{
|F^{raw}-H_{\mathrm{prof}}|
}{
|H_{\mathrm{prof}}|+\epsilon
}.
\]

核心比较：

\[
E_{\mathrm{SAEPS}}
<
E_{\mathrm{raw}}.
\]

---

### Profile-derived retained fraction

定义：

\[
\eta_{\mathrm{prof}}
=
\frac{
H_{\mathrm{prof}}
}{
H_{\mathrm{frozen}}+\epsilon
}.
\]

比较：

\[
\eta^{se}
\quad\text{vs.}\quad
\eta_{\mathrm{prof}}.
\]

这比单独展示 \(\eta^{se}\) 更有科学解释力。

---

# 11. Classical identifiability control

对于 scalar physical benchmark，同时使用独立数值 forward solver 建立 observation-only parameter profile。

目的不是建立完整 uncertainty theory，而只是回答：

> 数据本身是否具有局部参数分辨能力？

如果 classical forward profile 已经非常平，则不能把 PINN 中出现的弱参数信息全部解释为 neural-state absorption。

因此至少报告：

- classical profile；
- profile minimum；
- local curvature；
- truth position。

---

# 12. Benchmark C：Two-Parameter Joint Geometry

优先继续使用现有 coupled reaction–diffusion 形式：

\[
u_t
=
D_u u_{xx}
-au+bv+s_u,
\]

\[
v_t
=
D_v v_{xx}
+au-bv+s_v,
\]

joint target：

\[
\lambda
=
(\log a,\log b).
\]

旧稿已经具备该 benchmark 的 manufactured state 和参数设置，因此它适合作为新仓库的两参数基础，而无需额外增加二维 Darcy 的开发成本。

---

# 13. 多参数实验不再逐坐标分类

计算完整：

\[
F^{raw}\in\mathbb R^{2\times2},
\]

\[
F^{se}\in\mathbb R^{2\times2}.
\]

做 eigendecomposition：

\[
F^{se}
=
V\Lambda V^\top.
\]

重点报告：

- \(\lambda_1,\lambda_2\)；
- eigenvectors；
- condition number；
- normalized off-diagonal coupling；
- true parameter-error direction 在 eigenspace 中的投影。

---

# 14. 多参数 nonlinear profile

至少沿以下三个方向运行真正的 state reoptimization：

\[
v_1,
\qquad
v_2,
\qquad
d_{\mathrm{error}}.
\]

对于每个方向：

\[
\lambda(s)
=
\lambda_0+s\,d.
\]

使用和 scalar benchmark 相同的 7 点 profile。

另选择一个 representative confirmation seed，计算一个小型：

\[
5\times5
\]

二维 reoptimized profile grid，用于论文可视化。

这样已经足够验证 joint geometry，不需要每个 seed 都做完整二维网格。

---

# 15. Checkpoint 训练协议必须重新定义

旧稿 main chain 采用固定 600 epochs Adam，并以 residual/state error gate 为主；主 validation 又主要使用 \(\sigma=0\)、full observation。

新仓库不得继续使用：

> “训练 600 epoch = checkpoint ready”

这一逻辑。

---

# 16. 新 checkpoint acceptance gate

checkpoint 必须同时通过四类检查。

## A. Residual gate

记录：

- PDE；
- data；
- IC；
- BC。

---

## B. Optimization stationarity gate

计算 normalized：

\[
S_\theta
=
\frac{
\|J_\theta^\top\bar r\|
}{
\|J_\theta\|\,\|\bar r\|+\epsilon
},
\]

\[
S_\lambda
=
\frac{
\|J_\lambda^\top\bar r\|
}{
\|J_\lambda\|\,\|\bar r\|+\epsilon
}.
\]

实际阈值在 development stage 确定并锁定。

必须完整报告，而不能隐藏 failed checkpoints。

---

## C. State/reference quality gate

仅 synthetic validation 使用。

必须明确标为：

> validation-only gate.

---

## D. Numerical SAEPS gate

所有 CG / Krylov solves 必须收敛。

核心 relative residual：

\[
\frac{
\|(J_\theta^\top J_\theta+\gamma I)z-J_\theta^\top y\|
}{
\|J_\theta^\top y\|+\epsilon
}
\le 10^{-8}.
\]

---

# 17. 推荐训练方式

核心 validation experiments 建议使用：

1. Adam warm-up；
2. 固定 residual/collocation set；
3. deterministic L-BFGS refinement；
4. stationarity check；
5. 保存 checkpoint；
6. 不再改变 checkpoint；
7. 运行 SAEPS；
8. 运行 nonlinear profiles。

原因是核心实验研究的是局部 residual geometry，首先需要消除 stochastic sampling 和明显 optimizer non-convergence 的干扰。

随机 resampling 可以留到 robustness experiment。

---

# 18. \(\gamma\) 不再隐藏成一个“最佳数值”

SAEPS 应被视为：

\[
F^{se}(\gamma).
\]

规定固定 damping grid，例如：

\[
\gamma
=
\gamma_\alpha
\lambda_{\max}(J_\theta^\top J_\theta),
\]

\[
\gamma_\alpha
\in
\{
10^{-12},
10^{-10},
10^{-8},
10^{-6},
10^{-4},
10^{-2}
\}.
\]

必要时补充更大值用于极限行为展示。

不得根据最终结果手工选择最漂亮的 \(\gamma\)。

---

# 19. Small-network exact reference

controlled benchmark 必须提供一个小网络版本，可以显式构造：

\[
J_\theta.
\]

使用 SVD 得到：

\[
P_\perp
=
I-J_\theta J_\theta^\dagger
\]

及：

\[
F_{\mathrm{exact}}
=
J_\lambda^\top P_\perp J_\lambda.
\]

然后比较：

- explicit SVD；
- explicit damped matrix；
- matrix-free CG。

这是 SAEPS implementation unit validation。

---

# 20. 参数 step 的处理

尽量避免让核心结论依赖一个未解释的 parameter ridge \(\rho\)。

对于 \(p\le2\)，建议默认采用 symmetric eigendecomposition + truncated pseudoinverse：

\[
\Delta\lambda^{se}
=
-
(F^{se})^\dagger
g^{se}.
\]

ridge 可以作为 supplementary sensitivity experiment。

如果论文继续保留 \(\rho\)，则必须：

- 明确数值；
- 明确 scaling；
- 做 sensitivity sweep；
- 不允许隐藏默认值。

---

# 21. Development / Confirmation 分离

这是新实验设计的强制要求。

## Development seeds

例如：

\[
\{0,1,2\}.
\]

允许用于：

- debugging；
- architecture adjustment；
- PDE candidate screening；
- optimizer tuning；
- profile interval确定；
- \(\gamma\) grid确定。

---

## Confirmation seeds

例如：

\[
\{10,11,12,13,14\}.
\]

在进入 confirmation 前：

- benchmark 锁定；
- network architecture 锁定；
- observation layout 锁定；
- loss weights 锁定；
- optimizer protocol 锁定；
- thresholds 锁定；
- figure scripts 锁定。

confirmation 阶段不得根据结果重新调实验。

近期相关 inverse-PINN 诊断研究已经采用 locked-seed、architecture-transfer 和 fresh-noise 的确认式验证框架。 新仓库至少应实现 development/confirmation 分离。

---

# 22. 最小 robustness experiment

核心结果完成后，只增加两个 robustness axis。

## Noise

例如：

\[
\sigma
\in
\{0,10^{-3},10^{-2}\}.
\]

## Observation fraction

例如：

\[
f_{\mathrm{obs}}
\in
\{0.25,0.5,1.0\}.
\]

只对：

- Benchmark A 的一个代表 source；
- Benchmark B；

运行。

不需要三个 benchmark 全部做完整 Cartesian product。

---

# 23. 新仓库目录结构

建议：

```text
saeps/
├── README.md
├── pyproject.toml
├── LICENSE
├── .gitignore
│
├── configs/
│   ├── base.yaml
│   ├── benchmarks/
│   │   ├── controlled_source.yaml
│   │   ├── burgers.yaml
│   │   ├── allen_cahn.yaml
│   │   └── crd.yaml
│   └── experiments/
│       ├── validation.yaml
│       ├── profile.yaml
│       └── robustness.yaml
│
├── src/
│   ├── saeps/
│   │   ├── residual.py
│   │   ├── autodiff.py
│   │   ├── operators.py
│   │   ├── elimination.py
│   │   ├── curvature.py
│   │   ├── score.py
│   │   ├── solvers.py
│   │   ├── profile.py
│   │   └── diagnostics.py
│   │
│   ├── benchmarks/
│   │   ├── controlled_source.py
│   │   ├── burgers.py
│   │   ├── allen_cahn.py
│   │   ├── reaction_diffusion.py
│   │   └── classical/
│   │
│   └── utils/
│       ├── seed.py
│       ├── io.py
│       ├── logging.py
│       └── provenance.py
│
├── scripts/
│   ├── 00_smoke_test.py
│   ├── 01_train.py
│   ├── 02_stationarity.py
│   ├── 03_run_saeps.py
│   ├── 04_profile_frozen.py
│   ├── 05_profile_reoptimized.py
│   ├── 06_controlled_geometry.py
│   ├── 07_mult_parameter.py
│   ├── 08_robustness.py
│   └── 09_build_paper_artifacts.py
│
├── tests/
│   ├── test_residual.py
│   ├── test_jvp_vjp.py
│   ├── test_explicit_vs_matrixfree.py
│   ├── test_psd.py
│   ├── test_cg.py
│   └── test_reproducibility.py
│
├── experiments/
│   └── manifests/
│
├── outputs/
│
├── paper_artifacts/
│   ├── data/
│   ├── figures/
│   └── tables/
│
└── docs/
    ├── EXPERIMENT_PLAN.md
    ├── BENCHMARKS.md
    ├── PROVENANCE.md
    └── DECISIONS.md
```

---

# 24. 软件设计原则

## Residual-first API

任何 benchmark 最终统一返回：

\[
\bar r(\theta,\lambda).
\]

SAEPS core 不允许知道具体 PDE。

接口只接受：

- residual function；
- \(\theta\)；
- \(\lambda\)；
- JVP；
- VJP。

这样可以彻底解耦 PDE 与诊断方法。

---

# 25. SAEPS 核心模块只实现一次

核心 API 建议：

```text
apply_A(y, theta, lambda, gamma)
compute_Fse(...)
compute_gse(...)
compute_eta(...)
compute_step(...)
```

所有 benchmark 共用同一套实现。

禁止每个实验复制 SAEPS 代码。

---

# 26. 强制 provenance

每次 run 至少保存：

```text
run_id
git_commit
config_hash
seed
benchmark
architecture
parameter_coordinates
training_points
diagnostic_points
loss_weights
optimizer
learning_rate
checkpoint_epoch
stationarity_theta
stationarity_lambda
gamma
CG_iterations
CG_relative_residual
Fraw
Fse
gse
eta
```

所有结果必须从 machine-readable 文件生成。

---

# 27. 禁止手填论文数字

Paper Table / Figure 必须：

\[
\text{raw run files}
\rightarrow
\text{aggregation script}
\rightarrow
\text{paper artifact}.
\]

禁止：

- Excel 手工复制；
- Python script 中写死 paper values；
- LaTeX 手填实验数字。

当前稿件 Supplementary seed-level 与 aggregate-level retained sensitivity 已出现需要重新核查的一致性问题，因此新仓库必须从架构层面杜绝这一风险。

---

# 28. 工程级验收标准

以下属于软件正确性要求，不属于论文经验阈值。

## Unit Test 1

小模型中 explicit 与 matrix-free：

\[
\frac{
\|F^{se}_{explicit}-F^{se}_{MF}\|_F
}{
\|F^{se}_{explicit}\|_F+\epsilon
}
<10^{-6}.
\]

---

## Unit Test 2

CG relative residual：

\[
\le10^{-8}.
\]

---

## Unit Test 3

Numerical PSD：

\[
\lambda_{\min}(F^{se})
\ge
-\tau_{\mathrm{num}}.
\]

---

## Unit Test 4

理论上应满足：

\[
F^{se}
\preceq F^{raw}
\]

至数值误差。

scalar 情况应检查：

\[
0\le\eta^{se}\le1+\tau_{\mathrm{num}}.
\]

---

## Unit Test 5

相同 configuration + seed 的重复运行应在预定 numerical tolerance 内一致。

---

# 29. Scientific Go / No-Go Criteria

以下仅作为本项目“是否已经形成论文证据链”的预注册标准，不宣称为 SAEPS 的通用理论阈值。

### Go-1

Controlled benchmark 在 confirmation seeds 上应表现出稳定的 tangent-overlap / retained-sensitivity 单调关系。

建议目标：

\[
|\rho_{\mathrm{Spearman}}|>0.9.
\]

---

### Go-2

当 nonlinear profile 显示明显 state adaptation 时，应满足多数 confirmation seeds：

\[
E_{\mathrm{SAEPS}}
<
E_{\mathrm{raw}}.
\]

建议至少：

\[
4/5
\]

confirmation seeds 成立。

---

### Go-3

对于人为构造的 off-optimum scalar checkpoints，SAEPS step 与 nonlinear reoptimized profile minimum 的方向应高度一致。

建议 confirmation sign agreement：

\[
\ge90\%.
\]

这是项目目标，不作为通用分类阈值。

---

### Go-4

两参数 benchmark 中，full-matrix SAEPS 应能够合理解释 nonlinear profiles 的 strong/weak directions。

如果 joint coupling 实际很弱，则如实报告；不得人为制造 off-diagonal coupling。

---

# 30. 最小论文 Figure 设计

## Figure 1

SAEPS geometry schematic。

可选，不是核心实验。

---

## Figure 2

**Controlled tangent geometry calibration**

\[
\text{tangent overlap}
\rightarrow
\eta^{se}.
\]

---

## Figure 3

**最核心 Figure**

Scalar benchmark：

- frozen nonlinear profile；
- SAEPS quadratic；
- state-reoptimized nonlinear profile。

---

## Figure 4

Across-seed：

\[
F^{se}
\text{ vs. }
H_{\mathrm{profile}}
\]

以及：

\[
F^{raw}
\text{ vs. }
H_{\mathrm{profile}}.
\]

---

## Figure 5

Two-parameter benchmark：

沿 \(v_1,v_2\) 的 nonlinear profiles 与 SAEPS predictions。

---

## Supplementary

- \(\gamma\) sweep；
- stationarity；
- CG convergence；
- seed distributions；
- noise/sparsity；
- screening candidates；
- representative 2D profile surface。

---

# 31. 最小论文 Table

## Table 1

Benchmark 与 protocol。

## Table 2

Confirmation-seed summary：

- \(F^{raw}\)；
- \(F^{se}\)；
- \(H_{\mathrm{profile}}\)；
- \(\eta^{se}\)；
- \(\eta_{\mathrm{profile}}\)；
- curvature errors；
- stationarity；
- CG status。

不再用主表给每个参数贴“可靠/不可靠”标签。

---

# 32. 开发任务分阶段

## Phase 0：Repository bootstrap

任务：

- 建 Git 仓库；
- 建 Python package；
- 固定环境；
- CI；
- logging；
- deterministic seed；
- config system；
- provenance。

验收：

```text
python scripts/00_smoke_test.py
```

能从零完成一次 tiny PINN training。

---

## Phase 1：Residual & autodiff infrastructure

任务：

- residual block abstraction；
- weighted residual；
- JVP；
- VJP；
- parameter coordinate transform；
- diagnostic grid。

验收：

有限差分与 autodiff derivative 对比通过。

---

## Phase 2：SAEPS core

任务：

- explicit implementation；
- matrix-free implementation；
- CG；
- Fraw；
- Fse；
- gse；
- eta；
- eigenspectrum；
- step。

验收：

explicit vs matrix-free unit tests 全部通过。

---

## Phase 3：Controlled benchmark

任务：

- manufactured PDE；
- Fourier source library；
- tangent-overlap screening；
- \(q_\parallel,q_\perp\) lock；
- \(\alpha\)-family；
- 3 development seeds；
- 5 confirmation seeds。

**完成这一阶段后再决定是否继续大规模计算。**

---

## Phase 4：Nonlinear profile engine

这是项目最重要的软件模块之一。

实现：

```text
profile_frozen()
profile_reoptimized()
fit_local_quadratic()
compare_curvature()
```

必须支持 arbitrary direction。

---

## Phase 5：Scalar benchmark screening

候选：

- Burgers；
- Allen–Cahn。

开发 seeds 上比较：

- classical profile；
- training convergence；
- stationarity；
- solver stability。

锁定其中一个进入 confirmation。

---

## Phase 6：Scalar confirmation

5 confirmation seeds。

每 seed：

1. train；
2. stationarity；
3. SAEPS；
4. frozen profile；
5. nonlinear reoptimized profile；
6. classical profile；
7. aggregate。

---

## Phase 7：Two-parameter benchmark

实现 CRD joint target：

\[
(\log a,\log b).
\]

运行：

- full Fraw；
- full Fse；
- eigen-analysis；
- directional nonlinear profiles；
- representative 2D grid。

---

## Phase 8：Robustness

只在核心证据成立以后运行：

- noise；
- observation fraction；
- optional architecture transfer。

如果核心结果不成立，不应通过增加 robustness runs 来“救结果”。

---

## Phase 9：Paper artifact pipeline

单一命令：

```text
python scripts/09_build_paper_artifacts.py
```

自动生成：

```text
paper_artifacts/data/
paper_artifacts/figures/
paper_artifacts/tables/
```

论文中的所有数字均来自该 pipeline。

---

# 33. 推荐执行顺序

最重要的是不要一次把整个仓库全部写完。

严格按以下顺序推进：

```text
Repo
 ↓
Tiny explicit SAEPS
 ↓
Matrix-free verification
 ↓
Controlled geometry
 ↓
Nonlinear reoptimization profile
 ↓
Scalar physical benchmark
 ↓
Two-parameter benchmark
 ↓
Robustness
 ↓
Paper
```

如果 **Controlled geometry + nonlinear profile** 两步不能产生清晰结果，应停止扩 benchmark，先检查理论、实现和实验定义。

---

# 34. 建议开发周期

### Week 1

仓库、residual API、autodiff、unit tests。

### Week 2

SAEPS explicit + matrix-free + controlled benchmark。

### Week 3

Nonlinear profile engine，并完成第一张 SAEPS vs reoptimized-profile 图。

### Week 4

Scalar PDE screening 与 confirmation。

### Week 5

Two-parameter CRD。

### Week 6

Robustness、\(\gamma\) audit、stationarity audit。

### Week 7

锁数据、生成 paper figures/tables、开始重写论文。

该周期只是工程规划估计，不作为强制时间要求。

---

# 35. 新论文建议的 Results 结构

## 4.1 Numerical verification of state elimination

证明代码和数学实现一致。

## 4.2 Controlled calibration of tangent-space absorption

证明 SAEPS 能检测连续变化的 state absorption。

## 4.3 SAEPS predicts nonlinear state-profiled curvature

核心 scalar benchmark。

## 4.4 Multi-parameter reduced geometry

完整矩阵实验。

## 4.5 Robustness and regularization dependence

\(\gamma\)、noise、sparsity 等。

---

# 36. 论文叙事也应同步修改

不再以：

> SAEPS discovers three reliability regimes.

作为主线。

建议改成：

> **SAEPS is a local state-profiled approximation to the residual geometry of a trained inverse PINN.**

实验核心证明：

\[
\boxed{
F^{raw}
\rightarrow
\text{frozen-state geometry}
}
\]

而：

\[
\boxed{
F^{se}
\rightarrow
\text{state-reoptimized geometry}.
}
\]

state absorption 是两者差异自然产生的物理/几何解释，而不是预先定义好的 benchmark 标签。

---

# 37. 项目最终成功标准

MVP 可以进入论文写作阶段，当且仅当以下证据链完整：

1. explicit 与 matrix-free SAEPS 数值一致；
2. controlled geometry 中 retained sensitivity 随 tangent overlap 系统变化；
3. 至少一个标准 scalar inverse PDE 中，SAEPS 比 raw sensitivity 更准确预测 nonlinear state-reoptimized profile；
4. 多参数问题中完整 \(F^{se}\) 能解释主要 joint eigendirections；
5. 结果在 locked confirmation seeds 上可复现；
6. stationarity、\(\gamma\)、CG convergence 全部透明报告；
7. 所有 paper values 都能够从 raw outputs 自动重建。

如果第 3 条不成立，应优先重新检查方法假设，而不是继续增加新的 PDE。

---

# 38. 第一原则

新仓库整个开发过程中始终遵守：

> **不再寻找“符合论文故事的模型”，而是设计能够直接检验论文命题的实验。**

只要 nonlinear state-reoptimization 这一 gold standard 建立起来，无论 SAEPS 在某个具体 PDE 上表现为强 absorption、弱 absorption，还是几乎无 absorption，都属于有效科学结果。

这也是新实验体系相比旧版本最关键的变化。