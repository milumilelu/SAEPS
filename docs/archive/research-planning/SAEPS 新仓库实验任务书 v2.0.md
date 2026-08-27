# SAEPS 新仓库实验任务书 v2.0
## 面向 Codex Goal 的 JCP 级最小可发表验证方案

**项目名称：** SAEPS — State-Adapted Residual Elimination for Inverse PINNs  
**执行方式：** Codex Goal 长周期自主开发  
**目标层级：** 按 Journal of Computational Physics 方法论文的实验强度设计  
**项目性质：** 从零建立独立新仓库，不继承旧实验结果作为论文证据  
**版本：** v2.0

---

# 1. 顶层科学目标

本项目不再以“找到 reliable / absorbed / misaligned 三类 PDE”为目标。

唯一核心问题为：

> **SAEPS 的局部 neural-state elimination，能否比 raw fixed-network sensitivity 更准确地预测：当物理参数发生扰动，并允许 PINN 神经状态重新优化以后形成的真实 nonlinear reduced objective 局部几何？**

形式上验证：

\[
F_\lambda^{raw}
=
J_\lambda^\top J_\lambda
\]

与

\[
F_\lambda^{se}
=
J_\lambda^\top
A_\theta^{(\gamma)}
J_\lambda
\]

谁更接近真实 nonlinear state-profiled curvature：

\[
H_{\mathrm{prof}}
=
\nabla_\lambda^2
\left[
\min_\theta
L(\theta,\lambda)
\right].
\]

---

# 2. 论文允许主张的结论

只有实验实际支持时，论文才能主张以下内容。

## Claim A：实现正确性

SAEPS 的 explicit、SVD reference 和 matrix-free 实现在 numerical tolerance 内一致。

## Claim B：state absorption 机制可控

参数 residual direction 与 neural-state tangent space 越重合，retained sensitivity 越低。

## Claim C：SAEPS 比 raw sensitivity 更接近真实 state-reoptimized geometry

在 scalar inverse-PDE 中：

\[
F^{se}
\]

相比

\[
F^{raw}
\]

更准确预测 nonlinear reoptimized profile curvature。

## Claim D：完整多参数矩阵具有意义

对于 multi-parameter inverse problem，

\[
F_\lambda^{se}
\]

的 eigendirections 能预测真实 nonlinear reduced objective 的 strong / weak directions。

---

# 3. 明确禁止的过度结论

MVP 不允许直接声称：

- SAEPS 给出 global identifiability；
- SAEPS 给出 posterior uncertainty；
- \(\eta^{se}\) 是参数固有可靠度；
- 某个固定阈值可普适地区分可靠/不可靠参数；
- score misalignment 是某类 PDE 的固有性质；
- SAEPS 对所有 inverse PINNs 普遍成立。

论文措辞应始终限定为：

> local, checkpoint-dependent, residual-space diagnostic.

---

# 4. Codex Goal 的完成定义

Codex 的任务是：

> **正确完成预注册验证，而不是得到支持 SAEPS 的结果。**

最终允许出现：

```text
SUPPORTED
PARTIALLY_SUPPORTED
NOT_SUPPORTED
```

三种科学结论。

即使得到 NOT_SUPPORTED，只要实验执行符合协议，Codex Goal 仍视为完成。

---

# 5. 总体实验结构

核心实验只保留三组。

| Benchmark | 科学作用 | Confirmation seeds |
|---|---|---:|
| A. Controlled tangent geometry | 验证 state absorption 机制 | **10** |
| B. Scalar physical inverse PDE | SAEPS vs nonlinear profile | **10** |
| C. Two-parameter inverse PDE | 验证完整 matrix geometry | **10** |

额外 robustness：

| 实验 | Seeds |
|---|---:|
| Noise × sparsity | 5 / condition |
| Narrow architecture | 5 |
| Wide architecture | 5 |

---

# 6. Seed 设计

## Development seeds

固定：

```text
0, 1, 2
```

仅允许用于：

- debugging；
- optimizer tuning；
- benchmark feasibility screening；
- profile interval；
- stationarity threshold；
- damping rule；
- architecture selection。

Development 数据不得进入主论文 confirmation statistics。

---

## Confirmation seeds

固定：

```text
10, 11, 12, 13, 14,
15, 16, 17, 18, 19
```

进入 confirmation 后：

- 不得调整 benchmark；
- 不得调整 architecture；
- 不得调整 loss weights；
- 不得调整 sensor layout；
- 不得调整 profile interval；
- 不得调整 scientific threshold；
- 不得重新选择 \(\gamma\) 以改善结论。

---

# 7. Repository 强制治理结构

必须首先创建：

```text
AGENTS.md
GOAL.md
TASKS.md

docs/
├── EXPERIMENT_SPEC.md
├── ACCEPTANCE_CRITERIA.md
├── SCIENTIFIC_GATES.md
├── DECISIONS.md
├── ISSUES.md
├── PROVENANCE.md
└── LOCKED_PROTOCOL.md
```

---

# 8. AGENTS.md 核心原则

必须包含以下约束：

```text
This repository is a scientific validation project.

Your objective is to execute the preregistered protocol faithfully,
not to obtain a favorable scientific result.

Development-stage tuning is allowed only where explicitly permitted.

Once confirmation configuration is locked, it is immutable.

Never remove unfavorable seeds.

Never choose benchmarks based on desirable SAEPS values.

Never manually enter paper-facing numerical values.

A scientifically negative result is a valid successful completion.

Engineering failure should be repaired.
Scientific failure should be reported, not tuned away.
```

---

# 9. 阶段结构

Codex 严格按照：

```text
P0 Repository
 ↓
P1 Numerical core validation
 ↓
P2 Controlled geometry
 ↓
P3 Nonlinear profile engine
 ↓
P4 Scalar PDE screening
 ↓
LOCK
 ↓
P5 Scalar confirmation
 ↓
P6 Multi-parameter confirmation
 ↓
P7 Robustness
 ↓
P8 Computational cost
 ↓
P9 Final audit
```

执行。

---

# 10. P0 — Repository Bootstrap

## 任务

建立：

```text
pyproject.toml
README.md

src/
tests/
configs/
scripts/
outputs/
paper_artifacts/
```

要求保存：

- Python version；
- package versions；
- seed；
- git commit；
- config hash；
- hardware；
- dtype；
- timestamp。

---

## 验收

必须成功运行：

```bash
pytest -q
python scripts/00_smoke_test.py
```

Smoke test 必须：

1. 训练 tiny PINN；
2. 保存 checkpoint；
3. reload；
4. 重算 residual；
5. 与保存前一致。

---

# 11. P1 — SAEPS Core Verification

必须同时实现：

### Explicit Jacobian

\[
J_\theta,\qquad J_\lambda.
\]

### Exact/SVD reference

\[
P_\perp
=
I-J_\theta J_\theta^\dagger.
\]

### Tikhonov explicit

\[
A_\theta^{(\gamma)}
=
I-
J_\theta
(J_\theta^\top J_\theta+\gamma I)^{-1}
J_\theta^\top.
\]

### Matrix-free

使用：

- JVP；
- VJP；
- CG / Krylov solver。

---

# 12. P1 强制数值验收

## A. Operator

随机至少 10 个 \(y\)：

\[
\frac{
\|A_{MF}y-A_{explicit}y\|
}{
\|A_{explicit}y\|+\epsilon
}
<10^{-6}.
\]

## B. Curvature

\[
\frac{
\|F^{se}_{MF}-F^{se}_{explicit}\|_F
}{
\|F^{se}_{explicit}\|_F+\epsilon
}
<10^{-6}.
\]

## C. Symmetry

\[
\frac{
\|F^{se}-(F^{se})^\top\|_F
}{
\|F^{se}\|_F+\epsilon
}
<10^{-8}.
\]

## D. PSD

\[
\lambda_{\min}(F^{se})
\ge
-10^{-8}\lambda_{\max}(F^{se}).
\]

## E. Loewner relation

检查：

\[
F^{raw}-F^{se}\succeq0
\]

至 numerical tolerance。

## F. CG convergence

\[
r_{\mathrm{CG}}\le10^{-8}.
\]

任何一条持续失败，不允许开始科学实验。

---

# 13. P2 — Controlled Tangent Geometry

## PDE

使用简单 manufactured parabolic PDE：

\[
u_t-Du_{xx}+cu
=
\lambda q_\alpha(x,t)+s_\alpha(x,t).
\]

固定：

\[
D,\ c,\ \lambda^\star,\ u^\star.
\]

通过 forcing 保证所有 source family 共享同一 truth state。

---

# 14. Source construction

Development seeds 上建立固定 Fourier library。

定义 tangent overlap：

\[
\omega(q)
=
\frac{
q^\top P_\theta q
}{
q^\top q
}.
\]

选择：

\[
q_\parallel
\]

和

\[
q_\perp.
\]

一旦 development 阶段结束立即锁定。

构造：

\[
q_\alpha
=
\sqrt{1-\alpha}\,q_\parallel
+
\sqrt{\alpha}\,q_\perp,
\]

其中：

\[
\alpha
\in
\{0,0.25,0.5,0.75,1\}.
\]

---

# 15. P2 Confirmation workload

10 seeds × 5 values：

\[
50
\]

组核心 SAEPS evaluations。

---

# 16. P2 Scientific Gate

对每一个 seed 计算：

\[
\rho_i
=
\rho_{\mathrm{Spearman}}
(
\alpha,\eta^{se}
).
\]

要求：

\[
\operatorname{median}_i\rho_i\ge0.9
\]

且至少：

\[
8/10
\]

seeds 显示正确单调趋势。

同时报告：

- all seed values；
- median；
- IQR；
- no hidden exclusion。

---

# 17. P3 — Nonlinear State-Reoptimization Engine

必须实现：

```text
profile_frozen()
profile_reoptimized()
fit_local_quadratic()
estimate_curvature()
estimate_profile_minimum()
compare_curvature()
```

---

# 18. Frozen profile

对于：

\[
q=\log\lambda,
\]

定义：

\[
\Phi_{\mathrm{frozen}}(s)
=
L(\theta_0,q_0+s).
\]

对应：

\[
F^{raw}.
\]

---

# 19. Reoptimized profile

定义：

\[
\Phi_{\mathrm{reopt}}(s)
=
\min_\theta
L(\theta,q_0+s).
\]

每个 profile point：

- 固定 \(q\)；
- 从同一个 \(\theta_0\) 初始化；
- 重新优化 \(\theta\)；
- 不允许 previous-point continuation；
- 使用同一 stopping rule。

---

# 20. Reoptimization stopping rule

必须至少同时满足：

1. deterministic optimizer termination；
2. loss change plateau；
3. normalized \(\theta\)-gradient 达到 development 阶段锁定标准。

不能简单使用“固定训练 N epochs”作为 profile completion criterion。

---

# 21. Profile points

Development 默认：

\[
s
\in
\{-0.15,-0.10,-0.05,0,
0.05,0.10,0.15\}.
\]

如果 development 显示明显超出 quadratic local regime，可统一调整。

一旦 lock 后不得改变。

---

# 22. P3 数值验收

Synthetic test 中：

- profile point 顺序打乱后结果保持一致；
- quadratic fitting 可恢复已知 curvature；
- independent initialization policy 可复现；
- failed optimization 有明确 status；
- 不允许 silently interpolate missing point。

---

# 23. P4 — Scalar Physical PDE Screening

候选只允许两个：

```text
Burgers
Allen-Cahn
```

不得无限增加候选 PDE。

---

# 24. Benchmark screening 标准

只允许依据：

### Numerical feasibility

- forward solver 稳定；
- PINN training 稳定；
- profile reoptimization 稳定。

### Inverse information

classical forward profile 必须存在明确局部 minimum。

### Stationarity

足够 development checkpoints 可以达到联合 stationarity。

### SAEPS numerics

CG 和 Jacobian computations 稳定。

---

# 25. 禁止 screening 依据

不得因为：

- \(\eta^{se}\) 更低；
- SAEPS 比 raw 好得更多；
- Figure 更漂亮；
- 更容易产生某种 regime；

而选择最终 benchmark。

---

# 26. Scalar benchmark lock

完成 development 后生成：

```text
configs/locked/scalar.yaml
```

并记录：

```text
SHA256
git commit
date
decision reason
```

进入 P5 后 immutable。

---

# 27. Checkpoint Acceptance

所有正式 checkpoint 必须报告：

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

还需记录：

- PDE residual；
- observation residual；
- BC/IC residual；
- state error（synthetic only）；
- parameter error（validation only）。

---

# 28. P5 — Scalar Confirmation

必须运行全部：

\[
10
\]

confirmation seeds。

每 seed 执行：

1. training；
2. stationarity gate；
3. SAEPS；
4. frozen profile；
5. nonlinear state-reoptimized profile；
6. independent classical forward profile；
7. local curvature fitting；
8. automatic comparison。

---

# 29. Scalar 核心 quantities

从 nonlinear profile 得到：

\[
H_{\mathrm{profile}}.
\]

定义：

\[
E_{\mathrm{SAEPS}}
=
\frac{
|F^{se}-H_{\mathrm{profile}}|
}{
|H_{\mathrm{profile}}|+\epsilon
},
\]

\[
E_{\mathrm{raw}}
=
\frac{
|F^{raw}-H_{\mathrm{profile}}|
}{
|H_{\mathrm{profile}}|+\epsilon
}.
\]

并定义 paired improvement：

\[
D_i
=
E_{\mathrm{raw},i}
-
E_{\mathrm{SAEPS},i}.
\]

---

# 30. Scalar Primary Scientific Gate

强支持要求：

### Criterion 1

至少：

\[
9/10
\]

有效 confirmation seeds 满足：

\[
D_i>0.
\]

### Criterion 2

\[
\operatorname{median}(D)>0.
\]

### Criterion 3

对 \(D_i\) 做 seed-level paired bootstrap：

\[
95\%\,CI(D).
\]

若：

\[
CI_{lower}>0,
\]

记为：

```text
STRONGLY_SUPPORTED
```

如果 1、2 成立但 CI 跨 0：

```text
SUPPORTED_WITH_UNCERTAINTY
```

如果只有轻微优势：

```text
PARTIALLY_SUPPORTED
```

若 median \(D\le0\)：

```text
NOT_SUPPORTED
```

---

# 31. Profile-retention comparison

另外计算：

\[
\eta_{\mathrm{profile}}
=
\frac{
H_{\mathrm{profile}}
}{
H_{\mathrm{frozen}}+\epsilon
}.
\]

比较：

\[
\eta^{se}
\]

与

\[
\eta_{\mathrm{profile}}.
\]

必须报告：

- scatter；
- correlation；
- absolute error；
- per-seed values。

---

# 32. Classical inverse control

Scalar benchmark 必须使用独立 conventional forward solver。

建立：

\[
\Phi_{\mathrm{classical}}(\lambda).
\]

目的：

区分：

\[
\text{observation-limited identifiability}
\]

与：

\[
\text{PINN state absorption}.
\]

若 classical profile 本身平坦，不允许把低 SAEPS retained signal 单独解释为 PINN-specific state absorption。

---

# 33. P6 — Two-Parameter Benchmark

MVP 推荐使用：

\[
\lambda=(\log a,\log b)
\]

的 coupled reaction-diffusion。

必须作为 joint target 一次分析。

禁止重新回到逐坐标独立标签。

---

# 34. Multi-parameter outputs

必须计算：

\[
F^{raw},
\qquad
F^{se}.
\]

以及：

\[
F^{se}=V\Lambda V^\top.
\]

记录：

- eigenvalues；
- eigenvectors；
- condition number；
- trace；
- determinant（如果 numerically meaningful）；
- normalized off-diagonal coupling。

---

# 35. Multi-parameter nonlinear profiles

对每个 confirmation seed 至少沿：

\[
v_{\max}
\]

与

\[
v_{\min}
\]

运行 nonlinear state-reoptimized profile。

得到：

\[
H_{\mathrm{prof}}(v_{\max}),
\]

\[
H_{\mathrm{prof}}(v_{\min}).
\]

---

# 36. P6 Scientific Gate

至少：

\[
9/10
\]

valid confirmation seeds 中，SAEPS strong/weak ordering 与 nonlinear profile ordering 一致：

\[
\lambda_{\max}(F^{se})
>
\lambda_{\min}(F^{se})
\]

对应：

\[
H_{\mathrm{prof}}(v_{\max})
>
H_{\mathrm{prof}}(v_{\min}).
\]

同时报告 directional curvature ratio error。

---

# 37. Representative 2D profile

预注册一个 representative seed。

使用固定规则，例如：

> first valid confirmation seed in ascending seed order.

不得选择“最好看”的 seed。

计算：

\[
5\times5
\]

二维 reoptimized profile grid。

用于：

- contour；
- SAEPS quadratic ellipse；
- eigendirection visualization。

---

# 38. P7 — Robustness

只在核心 confirmation 完成以后执行。

## Noise

例如：

\[
\sigma
\in
\{0,\;10^{-3},\;10^{-2}\}.
\]

## Observation fraction

\[
f
\in
\{0.25,\;0.5,\;1.0\}.
\]

共：

\[
3\times3=9
\]

conditions。

每 condition：

\[
5
\]

seeds。

因此最大：

\[
45
\]

robustness runs。

---

# 39. Robustness 不设强阳性门槛

目的只是回答：

- effect 是否快速崩溃；
- stationarity 是否恶化；
- SAEPS 与 raw 比较趋势是否仍存在；
- 哪个条件开始失效。

不得因为某 robustness cell 失败而重新修改方法。

---

# 40. Architecture transfer

Nominal architecture：

\[
10\ seeds.
\]

再定义：

- narrow；
- wide。

每种：

\[
5\ seeds.
\]

只运行 scalar benchmark。

---

# 41. Gamma Protocol

固定：

\[
\gamma
=
\gamma_\alpha
\lambda_{\max}(J_\theta^\top J_\theta).
\]

预注册：

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

不允许通过 confirmation 结果选“最好”的 \(\gamma\)。

---

# 42. Nominal gamma 选择

若需要 nominal \(\gamma\)，只能通过 development 阶段预定义算法选择：

例如同时满足：

- CG stable；
- \(\eta^{se}\) 位于局部 plateau；
- adjacent log-scale change 小于固定 tolerance。

选择规则必须在 confirmation 前写入代码。

禁止人工看 Figure 以后选择。

---

# 43. P8 — Computational Cost

JCP 级方法论文建议增加该部分。

必须记录：

- training time；
- SAEPS time；
- frozen profile time；
- reoptimized profile time；
- CG iterations；
- JVP/VJP count；
- peak memory（若容易获得）。

最终报告：

\[
\frac{
T_{\mathrm{reoptimized\ profile}}
}{
T_{\mathrm{SAEPS}}
}.
\]

这是 SAEPS 实际价值的重要组成部分：

> 它若能近似 nonlinear profiling，应说明节省多少计算量。

---

# 44. Paper-facing 核心 Figure

## Figure 1

SAEPS residual geometry schematic。

## Figure 2

Controlled tangent overlap vs retained sensitivity。

10 seeds，显示 median + distribution。

## Figure 3 — 论文核心图

Scalar benchmark：

- frozen nonlinear profile；
- SAEPS quadratic；
- state-reoptimized nonlinear profile；
- classical forward profile 可单独 panel。

## Figure 4

Across-seed：

\[
F^{raw}
\text{ vs. }
H_{\mathrm{profile}}
\]

和

\[
F^{se}
\text{ vs. }
H_{\mathrm{profile}}.
\]

同时显示 paired errors。

## Figure 5

Two-parameter：

- SAEPS eigendirections；
- nonlinear directional profiles；
- representative 2D contour。

## Figure 6

Robustness 或 computational-cost comparison。

---

# 45. 主文 Table

## Table 1

Benchmark and protocol。

## Table 2

Scalar confirmation：

```text
seed
Fraw
Fse
Hprofile
eta_se
eta_profile
Eraw
Ese
stationarity
```

## Table 3

Multi-parameter summary：

```text
seed
eig1
eig2
profile_curv_v1
profile_curv_v2
ordering
```

---

# 46. Supplementary Material

至少包含：

- development screening；
- all confirmation seed results；
- failed runs；
- \(\gamma\) sweep；
- CG convergence；
- stationarity traces；
- noise/sparsity；
- architecture transfer；
- profile-fit sensitivity；
- exact vs matrix-free test；
- computational cost detail。

---

# 47. Result provenance

每个 run 必须保存：

```text
run_id
git_commit
config_hash
seed
split
benchmark
architecture
dtype
hardware
optimizer
training_stop_reason
theta_stationarity
lambda_stationarity
residuals
state_error
parameter_error
gamma
CG_iterations
CG_relative_residual
Fraw
Fse
gse
eta
profile_curvature
profile_fit_quality
status
failure_reason
```

---

# 48. Failure handling

所有预注册 run 最终只能处于：

```text
PASS
CHECKPOINT_INVALID
PROFILE_FAILURE
SOLVER_FAILURE
NUMERICAL_FAILURE
```

不允许不存在。

例如 10 confirmation seeds 中 2 个 checkpoint 不通过，论文必须写：

```text
8/10 checkpoints passed the preregistered validity criteria.
```

而不能只写：

> n = 8.

---

# 49. 不允许手工填写论文数字

唯一允许流程：

```text
raw run files
      ↓
aggregation
      ↓
paper_artifacts/data
      ↓
figures / tables
```

必须自动验证：

\[
\text{reported aggregate}
=
\text{aggregate(raw seed data)}.
\]

此前旧稿 seed-level 与 aggregate-level retained sensitivity 已经出现需要重新核查的一致性问题，因此这一条属于新仓库硬性工程要求。

---

# 50. 自动 repository 验收

最终必须提供：

```bash
python scripts/validate_repository.py
```

检查：

1. unit tests；
2. confirmation seed completeness；
3. locked config hash；
4. config 是否被修改；
5. raw→aggregate consistency；
6. Figure regeneration；
7. Table regeneration；
8. failed-run reporting；
9. scientific gate computation；
10. provenance completeness。

---

# 51. Exit-code 规则

```text
0 = protocol execution complete
1 = engineering execution incomplete
```

**Scientific gate FAIL 不允许返回 1。**

科学结论不支持 SAEPS，不等于 Codex 执行失败。

---

# 52. Final Validation Report

Codex 必须自动生成：

```text
FINAL_VALIDATION_REPORT.md
```

固定包含：

## A. Repository status

## B. Engineering gates

```text
P0 PASS/FAIL
P1 PASS/FAIL
...
P9 PASS/FAIL
```

## C. Confirmation completeness

例如：

```text
Controlled geometry: 50/50 complete
Scalar: 10/10 final status
Multi-parameter: 10/10 final status
```

## D. Scientific results

## E. Bootstrap uncertainty

## F. Failed runs

## G. Protocol deviations

## H. Computational cost

## I. Scientific conclusion

只能为：

```text
SUPPORTED
PARTIALLY_SUPPORTED
NOT_SUPPORTED
```

## J. Recommendation

只能为：

```text
PROCEED_TO_PAPER
PROCEED_WITH_LIMITED_CLAIMS
REVISE_METHOD
INVESTIGATE_NUMERICS
STOP
```

---

# 53. 论文级 Go / No-Go 标准

## GO：可进入 JCP 级论文写作

建议同时满足：

### Numerical validity

P0–P3 全部通过。

### Controlled mechanism

P2 scientific gate PASS。

### Core scalar result

至少：

\[
9/10
\]

paired seeds 中：

\[
E_{\mathrm{SAEPS}}<E_{\mathrm{raw}}.
\]

且：

\[
\operatorname{median}(D)>0.
\]

最好 bootstrap CI 下界也大于 0。

### Multi-parameter

主要 eigendirection ordering 在：

\[
\ge9/10
\]

valid confirmation seeds 成立。

### Robustness

不要求全条件 PASS，但不能只在一个极窄实验条件下存在。

### Cost

SAEPS 必须明显低于 full nonlinear profiling 成本，否则实用价值需要重新论证。

---

# 54. PARTIALLY SUPPORTED

典型情况：

- controlled geometry 很强；
- scalar SAEPS 有平均优势；
- 但 across-seed uncertainty 较大；
- multi-parameter 只有部分支持。

此时仍可能发表，但应降低论文 claim。

---

# 55. NOT SUPPORTED

若出现：

\[
\operatorname{median}
(E_{\mathrm{raw}}-E_{\mathrm{SAEPS}})
\le0,
\]

或者 nonlinear profile 系统性与 SAEPS curvature 不一致，则不得通过换 PDE 重新建立主故事。

优先结论：

```text
REVISE_METHOD
```

---

# 56. 工作量控制原则

JCP 级实验强度来自：

> **evidence depth，而不是 benchmark 数量。**

因此不要再扩成 8–10 个 PDE。

主文保持：

\[
1\ controlled
+
1\ scalar
+
1\ multi\text{-}parameter
\]

即可。

通过：

- 10 confirmation seeds；
- nonlinear gold standard；
- independent conventional solver；
- robustness；
- architecture；
- computational cost；
- full provenance；

建立证据强度。

---

# 57. Codex 执行优先级

若计算资源有限，顺序绝对不能改变：

```text
P1 exact numerical validation
        ↓
P2 controlled geometry
        ↓
P3 nonlinear profile
        ↓
P5 scalar confirmation
        ↓
P6 multi-parameter
        ↓
P8 computational cost
        ↓
P7 robustness
```

如果 P5 核心结果失败：

**停止大规模 robustness。**

没有必要花算力证明一个核心结果尚未成立的方法具有鲁棒性。

---

# 58. Codex Goal 顶层提示词

建议 Codex Goal 使用以下内容：

> Build from scratch a reproducible and auditable SAEPS experimental repository following the preregistered protocol stored in this repository.
>
> The central scientific question is whether SAEPS local neural-state elimination predicts the nonlinear reduced objective obtained when the physical parameter is perturbed and the neural state is actually reoptimized, and whether it does so more accurately than raw fixed-network sensitivity.
>
> Treat `AGENTS.md`, `GOAL.md`, `docs/EXPERIMENT_SPEC.md`, `docs/ACCEPTANCE_CRITERIA.md`, `docs/SCIENTIFIC_GATES.md`, and `docs/LOCKED_PROTOCOL.md` as authoritative.
>
> Work phase by phase. Do not advance past an engineering gate until it passes.
>
> Development-stage tuning is permitted only where explicitly specified.
>
> Once confirmation configurations are locked, never alter them based on confirmation results.
>
> Never remove unfavorable seeds, silently exclude failed runs, choose benchmarks because they produce desirable SAEPS values, change gamma to improve results, or manually enter paper-facing numerical values.
>
> Scientific success is not required for task completion. A negative scientific result is valid.
>
> At every phase:
> 1. inspect the repository;
> 2. identify the next authorized incomplete task;
> 3. implement the minimum required work;
> 4. execute its acceptance checks;
> 5. record raw outputs and provenance;
> 6. document failures;
> 7. update `TASKS.md`;
> 8. commit the completed phase;
> 9. continue only when authorized by the protocol.
>
> If an engineering test fails, debug it.
>
> If a locked scientific experiment fails, report the failure and continue according to protocol; do not tune the experiment until it passes.
>
> Done when:
> - all mandatory engineering phases are complete;
> - all preregistered confirmation seeds have final statuses;
> - raw data, figures, tables and summary statistics are fully traceable;
> - repository validation passes;
> - `FINAL_VALIDATION_REPORT.md` is generated;
> - the report concludes `SUPPORTED`, `PARTIALLY_SUPPORTED`, or `NOT_SUPPORTED`;
> - all results can be regenerated from documented commands.

---

# 59. 最终项目成功标准

新实验体系达到“足以进入论文写作”的最低要求是：

\[
\boxed{
\text{Correct implementation}
}
\]

+

\[
\boxed{
\text{Controlled mechanism validation}
}
\]

+

\[
\boxed{
10\text{-seed nonlinear-profile confirmation}
}
\]

+

\[
\boxed{
\text{Multi-parameter validation}
}
\]

+

\[
\boxed{
\text{Independent classical control}
}
\]

+

\[
\boxed{
\text{Robustness and computational-cost evidence}
}
\]

+

\[
\boxed{
\text{Complete reproducibility}
}
\]

其中真正决定论文价值的是：

\[
\boxed{
F^{se}
\text{ 是否稳定地比 }
F^{raw}
\text{ 更接近真实 state-reoptimized curvature}
}
\]

而不是是否能够制造出三个预期标签。

---

# 60. 项目第一原则

整个仓库必须遵循：

> **设计实验来证伪或支持方法，而不是寻找能够配合论文叙事的实验。**

只要这一原则被 Codex 的任务协议、配置锁定、seed 设计和自动 provenance 强制执行，新仓库产生的结果无论正负，都具有比旧实验体系更高的科学可信度。