# SAEPS-Codex Goal 实验项目任务书与验收规范

**Project:** SAEPS Minimal Publishable Experimental Validation  
**Execution mode:** Codex long-horizon Goal workflow  
**Repository:** 全新仓库，从零构建  
**核心原则:** 可验证、可复现、不可通过结果导向调参修改科学结论

---

# 1. 顶层 Goal

## Goal

从零建立一个独立、可复现、可审计的 SAEPS 实验仓库，并完成最小可发表实验闭环，以检验以下核心科学命题：

> SAEPS 的局部 neural-state elimination 是否比 raw fixed-network sensitivity 更准确地预测“固定物理参数扰动后重新优化神经网络状态”所形成的 nonlinear reduced objective 局部几何。

项目最终必须给出明确结论：

- **SUPPORTED**
- **PARTIALLY SUPPORTED**
- **NOT SUPPORTED**

无论结果属于哪一类，只要实验执行和验证满足本任务书，均视为 Codex Goal 正确完成。

不得为了获得 SUPPORTED 结果而修改已锁定的实验设计。

---

# 2. Codex 顶层完成条件

Codex **只有同时满足以下全部条件，才允许将 Goal 标记为完成**：

1. repository 能从干净环境安装并运行；
2. SAEPS explicit 和 matrix-free 实现通过数值一致性测试；
3. controlled tangent-geometry benchmark 完成；
4. nonlinear state-reoptimized profile engine 完成；
5. 至少一个 scalar physical inverse-PDE benchmark 完成 confirmation experiments；
6. 一个 two-parameter benchmark 完成 joint-geometry experiments；
7. development 与 confirmation 数据严格分离；
8. confirmation configuration 已锁定且有 hash；
9. 所有预注册 confirmation seeds 均被执行或明确记录失败原因；
10. 所有失败实验均保留，不允许删除；
11. 所有 paper-facing 数值均由 raw result 自动聚合产生；
12. 能使用单一命令重新生成最终 figures、tables 和 summary；
13. 自动生成 `FINAL_VALIDATION_REPORT.md`；
14. 报告必须明确说明 scientific Go/No-Go；
15. `git status` 干净，测试通过，最终 commit 可追溯。

**不得以“结果不好”为由将任务标记为未完成。**

---

# 3. Codex 强制行为规则

## 3.1 允许自主执行

Codex 可以自主：

- 创建和修改 repository 内文件；
- 安装项目声明的 Python dependencies；
- 编写测试；
- 运行训练；
- 运行数值实验；
- 调试代码错误；
- 优化工程性能；
- 创建日志和图表；
- 修改 development-stage configuration；
- 根据预先规定的 screening rule 选择 benchmark。

---

## 3.2 必须停止并记录的问题

遇到以下情况，不得自行改变科学问题绕过失败：

- 理论公式与实现无法对应；
- explicit 与 matrix-free 结果持续不一致；
- confirmation experiment 与预期结论相反；
- SAEPS 不优于 raw baseline；
- profile 无法支持局部 quadratic approximation；
- 某 benchmark 无法达到 stationarity；
- numerical instability 无法通过合理数值方法解决；
- confirmation configuration 需要修改。

此时必须：

1. 保存现有结果；
2. 写入 `docs/ISSUES.md`；
3. 判断属于：
   - implementation failure；
   - numerical failure；
   - benchmark failure；
   - scientific failure；
4. 如果属于 scientific failure，不允许继续调参“修复结果”。

---

# 4. 禁止行为

Codex 不得：

- 删除不符合预期的 seed；
- 只报告表现最好的 seed；
- 根据 confirmation 结果重新选择 PDE；
- 根据 confirmation 结果重新选择 source；
- 根据 confirmation 结果重新改变 loss weights；
- 为得到更低/更高 \(\eta^{se}\) 调网络结构；
- 为得到更漂亮的结果改变 \(\gamma\)；
- 手工修改 aggregated paper values；
- 在 LaTeX/Markdown 中硬编码实验结果；
- 将 failed run 从 aggregation 中静默排除；
- 将 synthetic reference truth 用于真实 deployment 指标；
- 将未通过 stationarity gate 的 checkpoint 描述为可靠 SAEPS validation；
- 把相关性写成因果性；
- 把 local reliability 写成 global identifiability。

---

# 5. Repository 必须包含的治理文件

Codex 首先创建：

```text
AGENTS.md
GOAL.md
TASKS.md

docs/
    EXPERIMENT_SPEC.md
    ACCEPTANCE_CRITERIA.md
    SCIENTIFIC_GATES.md
    DECISIONS.md
    ISSUES.md
    PROVENANCE.md
```

其中：

### `GOAL.md`

保存本任务顶层目标。

### `TASKS.md`

保存阶段任务及状态：

```text
NOT_STARTED
IN_PROGRESS
BLOCKED
PASSED
FAILED
```

### `DECISIONS.md`

记录所有影响实验设计的决定：

```text
date
decision
reason
development evidence
affected configs
```

### `ISSUES.md`

记录不能静默处理的失败。

---

# 6. 阶段执行原则

Codex 不应同时开始所有 benchmark。

必须按照：

```text
P0
 ↓
P1
 ↓
P2
 ↓
P3
 ↓
P4
 ↓
P5
 ↓
P6
 ↓
P7
```

逐阶段推进。

只有当前阶段的 **engineering acceptance gate** 通过后才能进入下一阶段。

---

# 7. P0 — Repository Bootstrap

## 目标

建立最小、可复现运行环境。

## 必须实现

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

必须固定：

- Python version；
- dependency versions；
- deterministic seed utility；
- config loader；
- structured logging；
- run ID；
- config hash；
- git commit provenance。

---

## 验收

以下命令必须成功：

```bash
python -m pytest
python scripts/00_smoke_test.py
```

Smoke test 必须：

1. 创建 tiny neural network；
2. 训练一个简单函数/PDE residual；
3. 保存 checkpoint；
4. 保存 run metadata；
5. 再加载 checkpoint；
6. 得到一致结果。

### P0 PASS

全部成功。

### P0 FAIL

环境或基础 infrastructure 不稳定。

不得进入 P1。

---

# 8. P1 — SAEPS Core Numerical Verification

## 实现

统一 residual-first API：

```text
weighted_residual(theta, lambda)
jvp_theta(...)
vjp_theta(...)
jacobian_lambda(...)
apply_A(...)
compute_Fraw(...)
compute_Fse(...)
compute_gse(...)
compute_eta(...)
```

同时实现：

- explicit Jacobian reference；
- explicit SVD elimination；
- Tikhonov explicit elimination；
- matrix-free CG elimination。

---

# 9. P1 数值验收标准

使用 tiny network。

## Test A — explicit vs matrix-free

要求：

\[
\frac{
\|F^{se}_{MF}-F^{se}_{explicit}\|_F
}{
\|F^{se}_{explicit}\|_F+10^{-12}
}
<10^{-6}.
\]

---

## Test B — operator application

随机测试至少 10 个 \(y\)：

\[
A^{MF}y
\]

与 explicit \(Ay\) relative error：

\[
<10^{-6}.
\]

---

## Test C — CG

每个正式 SAEPS solve：

\[
r_{\mathrm{CG}}
\le 10^{-8}.
\]

---

## Test D — symmetry

\[
\frac{
\|F^{se}-(F^{se})^\top\|_F
}{
\|F^{se}\|_F+\epsilon
}
<10^{-8}.
\]

---

## Test E — PSD

允许 numerical tolerance：

\[
\lambda_{\min}(F^{se})\ge-10^{-8}\lambda_{\max}(F^{se}).
\]

---

## Test F — Loewner ordering

验证：

\[
F^{raw}-F^{se}\succeq0
\]

至 numerical tolerance。

---

## Test G — scalar bound

scalar case：

\[
-10^{-8}
\le
\eta^{se}
\le
1+10^{-8}.
\]

---

## P1 PASS

全部 numerical tests 通过。

否则不得开始 PDE experiments。

---

# 10. P2 — Controlled Tangent-Geometry Benchmark

## 科学目的

直接控制 parameter residual direction 与 neural-state tangent space 的关系。

不得依赖随机寻找“state-absorbed PDE”。

---

## Development 阶段

只使用：

```text
development seeds = [0, 1, 2]
```

建立 Fourier source library。

根据明确的 tangent-overlap metric：

\[
\omega(q)
=
\frac{q^\top P_\theta q}{q^\top q}
\]

选择：

\[
q_\parallel,\qquad q_\perp.
\]

一旦选择完成：

```text
configs/locked/controlled_geometry.yaml
```

生成 SHA256 hash。

之后不得修改。

---

## Confirmation

使用：

```text
confirmation seeds = [10, 11, 12, 13, 14]
```

测试：

\[
\alpha
\in
\{0,0.25,0.5,0.75,1\}.
\]

总共：

\[
5\times5=25
\]

组 confirmation evaluations。

必须全部运行。

---

# 11. P2 工程验收

要求：

- 25 个预注册实验都有 manifest；
- 每个 run 均保存 \(\eta^{se}\)；
- failed runs 不删除；
- aggregation script 自动运行；
- Figure 自动生成。

满足即 P2 工程 PASS。

---

# 12. P2 科学判据

预注册：

\[
\rho_{\mathrm{Spearman}}
(
\text{transverse fraction},
\eta^{se}
)
\ge0.9.
\]

并且至少：

\[
4/5
\]

confirmation seeds 中表现为单调或近单调趋势。

### 满足

记录：

```text
SCIENTIFIC_GATE_P2 = PASS
```

### 不满足

记录：

```text
SCIENTIFIC_GATE_P2 = FAIL
```

**不得重新选择 source 后重新计算 confirmation。**

P2 scientific FAIL 不等于 Codex task failure。

---

# 13. P3 — Nonlinear Profile Engine

这是整个项目最重要的软件模块。

必须实现：

```text
profile_frozen()
profile_reoptimized()
fit_local_quadratic()
estimate_profile_curvature()
compare_profiles()
```

---

## Frozen profile

\[
\Phi_{\mathrm{frozen}}(s)
=
L(\theta_0,q_0+s).
\]

---

## Reoptimized profile

\[
\Phi_{\mathrm{reopt}}(s)
=
\min_\theta
L(\theta,q_0+s).
\]

每个 \(s\) 必须：

- 从同一个 \(\theta_0\) warm start；
- 不使用前一个 profile point 的结果；
- 使用相同 optimizer policy；
- 使用相同 stopping rule。

---

# 14. P3 验收标准

构造一个 synthetic problem，确保 known quadratic/local behavior。

要求：

- profile 点全部生成；
- optimization metadata 全保存；
- curvature fitting 有测试；
- profile point 顺序改变不应改变结果超过 tolerance；
- failed reoptimization 点明确标记；
- plot pipeline 工作。

P3 PASS 后才允许进入 physical PDE。

---

# 15. P4 — Scalar PDE Development Screening

候选仅限预注册候选：

```text
Burgers
Allen-Cahn
```

允许 development seeds：

```text
[0, 1, 2]
```

---

## Screening 只允许依据

1. classical forward solver 是否稳定；
2. classical parameter profile 是否存在明确局部曲率；
3. PINN 是否稳定训练；
4. stationarity 是否可达到；
5. SAEPS solver 是否稳定；
6. nonlinear profile 是否可以可靠运行。

不得使用：

> 哪个模型更容易产生论文希望看到的 \(\eta^{se}\)

作为选择标准。

---

# 16. Scalar benchmark 选择规则

对每个 candidate 计算预定义 feasibility score。

优先选择：

1. 所有硬性 numerical gates 通过；
2. stationarity passing seeds 更多；
3. classical profile curvature 明确；
4. reoptimization failure rate 更低。

若仍并列：

按事先规定的 benchmark name alphabetical order 决定。

必须写入：

```text
docs/DECISIONS.md
```

之后 lock：

```text
configs/locked/scalar_benchmark.yaml
```

---

# 17. Checkpoint Stationarity Gate

正式 SAEPS checkpoint 必须报告：

\[
S_\theta
=
\frac{
\|J_\theta^\top\bar r\|_2
}{
\|J_\theta\|\,\|\bar r\|_2+\epsilon
},
\]

\[
S_\lambda
=
\frac{
\|J_\lambda^\top\bar r\|_2
}{
\|J_\lambda\|\,\|\bar r\|_2+\epsilon
}.
\]

具体 acceptance threshold 必须在 development 阶段确定并写入 locked config。

confirmation 后不得修改。

未通过 stationarity：

```text
CHECKPOINT_INVALID
```

不得偷偷增加训练直到该 seed 通过，除非 protocol 预先规定统一追加训练过程。

---

# 18. P5 — Scalar Confirmation Experiment

使用：

```text
seeds = [10, 11, 12, 13, 14]
```

每个 seed 必须执行：

1. PINN training；
2. stationarity gate；
3. SAEPS；
4. frozen profile；
5. nonlinear reoptimized profile；
6. classical forward profile；
7. profile curvature fitting；
8. automatic comparison。

---

# 19. Scalar Profile Points

默认：

\[
s
\in
\{-0.15,-0.10,-0.05,0,0.05,0.10,0.15\}.
\]

如果 development 证明该范围明显超出 local regime，可以在 lock 之前统一改变。

confirmation 后不得改变 profile interval。

---

# 20. Scalar 核心指标

计算：

\[
E_{\mathrm{SAEPS}}
=
\frac{
|F^{se}-H_{\mathrm{profile}}|
}{
|H_{\mathrm{profile}}|+\epsilon
},
\]

以及：

\[
E_{\mathrm{raw}}
=
\frac{
|F^{raw}-H_{\mathrm{profile}}|
}{
|H_{\mathrm{profile}}|+\epsilon
}.
\]

同时计算：

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
\quad\text{与}\quad
\eta_{\mathrm{profile}}.
\]

---

# 21. P5 工程验收

要求：

- 所有 5 个 confirmation seeds 都有最终状态；
- 不允许只 aggregate PASS seed 而不说明 denominator；
- profile 原始数据完整；
- 自动输出 frozen / SAEPS / reoptimized profile Figure；
- 自动输出 seed-level 表格。

满足则 P5 engineering PASS。

---

# 22. P5 Scientific Gate

论文核心判据预注册为：

至少：

\[
4/5
\]

有效 confirmation seeds 满足：

\[
E_{\mathrm{SAEPS}}
<
E_{\mathrm{raw}}.
\]

同时 median：

\[
E_{\mathrm{SAEPS}}
<
E_{\mathrm{raw}}.
\]

若满足：

```text
SCIENTIFIC_GATE_P5 = PASS
```

否则：

```text
SCIENTIFIC_GATE_P5 = FAIL
```

**失败后不得换 PDE 重跑 confirmation。**

---

# 23. P6 — Two-Parameter Benchmark

使用固定 joint inverse problem，例如：

\[
\lambda=(\log a,\log b).
\]

计算完整：

\[
F^{raw},
\qquad
F^{se}.
\]

不允许只计算 diagonal。

---

## 必须输出

- full matrices；
- eigenvalues；
- eigenvectors；
- condition number；
- normalized off-diagonal coupling；
- strongest direction；
- weakest direction。

---

# 24. Directional nonlinear validation

至少沿：

\[
v_{\max},
\qquad
v_{\min}
\]

运行 state-reoptimized profiles。

另对一个预注册 representative seed 运行：

\[
5\times5
\]

二维 profile grid。

---

## P6 工程验收

全部自动输出：

```text
matrix_summary.json
eigen_summary.json
directional_profiles.csv
profile_2d.csv
```

并生成 Figure。

---

## P6 Scientific Gate

不规定“必须强耦合”。

只检查：

> SAEPS predicted eigendirection ordering 是否与 reoptimized directional curvature ordering 一致。

若：

\[
H_{\mathrm{prof}}(v_{\max})
>
H_{\mathrm{prof}}(v_{\min})
\]

与 SAEPS eigenvalue ordering 一致的 confirmation seeds 达到：

\[
\ge4/5,
\]

记 PASS。

否则记 FAIL。

---

# 25. P7 — Minimal Robustness

只有 P0–P6 全部 engineering PASS 后执行。

不是为了拯救失败结果。

---

## Noise

\[
\sigma
\in
\{0,10^{-3},10^{-2}\}.
\]

## Observation fraction

\[
f
\in
\{0.25,0.5,1.0\}.
\]

只对 scalar benchmark 运行。

建议 3 seeds。

---

## 验收

必须完整报告：

- successful runs；
- failed runs；
- SAEPS errors；
- raw errors；
- stationarity；
- profile quality。

不要求 robustness 一定成功。

---

# 26. Gamma Protocol

不得挑选“效果最好”的 \(\gamma\)。

固定：

\[
\gamma
=
\gamma_\alpha
\lambda_{\max}(J_\theta^\top J_\theta).
\]

Development 阶段预定义：

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

最终必须报告完整 sweep。

如果需要一个 nominal value：

只能依据预先定义的 numerical stability / plateau rule 自动选择。

selection rule 必须在 confirmation 前 lock。

---

# 27. Results Provenance

每个 run 至少保存：

```text
run_id
timestamp
git_commit
config_hash
seed
benchmark
split
architecture
optimizer
training_stop_reason
theta_stationarity
lambda_stationarity
residual_metrics
state_metrics
gamma
cg_iterations
cg_relative_residual
Fraw
Fse
gse
eta
profile_points
profile_curvature
status
failure_reason
```

---

# 28. Aggregation 强制规则

所有 aggregation 必须读取 run manifests。

禁止：

```python
values = [0.91, 0.83, 0.72]
```

这种手工 paper 数值。

必须：

```text
outputs/runs/
      ↓
aggregate_results.py
      ↓
paper_artifacts/data/
      ↓
build_figures.py
build_tables.py
```

---

# 29. 自动一致性检查

build pipeline 必须自动 assert：

```text
reported median
==
median(seed-level source data)
```

允许 floating-point tolerance。

Table 与 Figure 使用同一 aggregation source。

---

# 30. 最终自动验收命令

仓库最终必须支持类似：

```bash
python scripts/validate_repository.py
```

该命令检查：

1. tests 是否通过；
2. expected confirmation runs 是否完整；
3. config hashes 是否锁定；
4. 是否存在修改过的 confirmation config；
5. 是否存在缺失 seed；
6. 是否存在 orphan results；
7. table aggregation 是否一致；
8. figures 是否可重新生成；
9. scientific gates 状态。

最终退出码：

```text
0 = repository scientifically audited and complete
1 = engineering validation incomplete
```

注意：

**scientific gate FAIL 不应导致 exit code 1。**

科学结论失败不是软件执行失败。

---

# 31. 最终报告

Codex 必须生成：

```text
FINAL_VALIDATION_REPORT.md
```

固定结构：

## 1. Goal

## 2. Repository status

## 3. Engineering acceptance

表格：

```text
P0 PASS/FAIL
P1 PASS/FAIL
...
P7 PASS/FAIL
```

## 4. Scientific gates

```text
Controlled geometry: PASS/FAIL
Scalar nonlinear profile: PASS/FAIL
Joint geometry: PASS/FAIL
```

## 5. Deviations from preregistered plan

必须逐项列出。

## 6. Failed runs

不得省略。

## 7. Main numerical results

只能引用自动生成数据。

## 8. Scientific conclusion

只能选择：

```text
SUPPORTED
PARTIALLY SUPPORTED
NOT SUPPORTED
```

## 9. Recommended next action

例如：

```text
PROCEED_TO_PAPER
REVISE_METHOD
INVESTIGATE_NUMERICS
STOP
```

---

# 32. 论文 Go / No-Go

## PROCEED_TO_PAPER

建议要求：

- P0–P7 engineering 全部 PASS；
- P1 numerical validation PASS；
- controlled geometry scientific gate PASS；
- scalar nonlinear profile scientific gate PASS；
- joint geometry scientific gate PASS 或至少没有明显反证；
- confirmation 无重大 protocol violation。

---

## PARTIAL / METHOD REVISION

如果：

- controlled benchmark PASS；
- scalar SAEPS 并未稳定优于 raw；

则说明数学实现可能正确，但论文核心经验主张不足。

结论：

```text
REVISE_METHOD
```

不得继续换 benchmark 寻找成功案例。

---

## STOP

如果：

- explicit 与 matrix-free 长期不一致；
- state-reoptimized profile 系统性反驳 \(F^{se}\)；
- SAEPS 对 damping 极端敏感且无稳定区间；
- 主要结论只在 development seeds 成立；

则输出：

```text
NOT_SUPPORTED
STOP
```

---

# 33. 建议写入 AGENTS.md 的执行原则

```text
This repository is a scientific validation project.

Your objective is to execute the preregistered experiment faithfully,
not to obtain a desired scientific result.

Never tune confirmation experiments to improve the conclusion.

Development-stage tuning is allowed only where explicitly permitted.

Once a configuration is locked, treat it as immutable.

A negative scientific result is a valid successful completion.

Never drop failed seeds silently.

Never manually enter paper-facing numerical results.

Before advancing phases, run the phase acceptance checks.

If an engineering gate fails, diagnose and repair it.

If a scientific gate fails after the experiment has been executed
correctly, record the failure and continue according to the protocol;
do not alter the experiment to force a pass.

All final claims must be traceable to machine-readable experimental
outputs.
```

---

# 34. 可直接用于 Codex Goal 的顶层指令

```text
Goal:
Build from scratch an auditable and reproducible experimental repository
for validating SAEPS in inverse PINNs.

The central scientific question is whether SAEPS local neural-state
elimination predicts the nonlinear reduced objective obtained when the
physical parameter is perturbed and the neural state is actually
reoptimized.

Follow GOAL.md, EXPERIMENT_SPEC.md, ACCEPTANCE_CRITERIA.md,
SCIENTIFIC_GATES.md, and AGENTS.md as the authoritative protocol.

Work phase-by-phase from P0 through P7. Do not advance past an
engineering gate until it passes.

Scientific success is NOT a requirement for task completion.
A scientifically negative result is valid and must be reported faithfully.

Do not tune locked confirmation experiments, remove unfavorable seeds,
select benchmarks based on desirable SAEPS values, manually enter
paper-facing results, or change preregistered thresholds after seeing
confirmation results.

At every phase:
1. inspect the current repository state;
2. identify the next incomplete task;
3. implement the minimum work required;
4. run the required validation;
5. record results and failures;
6. update TASKS.md;
7. continue if the next phase is authorized by the protocol.

Stop and document the issue rather than altering the scientific protocol
when a scientific gate fails.

Done when:
- all required engineering phases have been executed;
- all mandatory experiments have final statuses;
- confirmation configs and seeds are auditable;
- all automated tests and repository validation checks pass;
- figures and tables regenerate from raw machine-readable outputs;
- FINAL_VALIDATION_REPORT.md exists;
- the report gives one of SUPPORTED, PARTIALLY SUPPORTED, or NOT SUPPORTED;
- the repository is reproducible from documented commands.
```

---

# 35. Codex 工作方式的核心原则

该项目不要让 Codex 追求：

```text
make the paper work
```

而应让它追求：

```text
complete the validation protocol correctly
```

两者差别非常重要。

最好的科研 Agent 不应该被奖励“获得阳性结果”，而应该被奖励：

- protocol compliance；
- numerical correctness；
- provenance；
- reproducibility；
- honest failure reporting。

只有这样，最终跑出来的实验结果才真正具有论文价值。