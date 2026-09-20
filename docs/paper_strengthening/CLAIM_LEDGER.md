# Q2 补强 Claim Ledger

**Namespace:** `paper_strengthening_v1`
**阶段:** `S0 PASSED / DEVELOPMENT_ONLY`
**日期:** 2026-09-20
**说明:** 本台账冻结当前稿件可使用的主张边界；它不授权新的 confirmation。

| ID | 当前主张 | 证据 | 统计单位/分母 | 允许措辞 | 禁止措辞 | 状态 |
|---|---|---|---|---|---|---|
| C1 | SAEPS 计算有限阻尼 residual-space Gauss–Newton state-elimination curvature | P1 core tests；integrated manuscript Method | numerical operator checks | finite-damping local diagnostic | new Schur theory、universal method | SUPPORTED_WITHIN_SCOPE |
| C2 | SAEPS 在声明的 scalar synthetic inverse-PINN 条件下比 raw fixed-state GN 更接近 exact finite-γ Hessian reference | P5 scalar records；12/15 Burgers、9/10 Allen–Cahn valid | checkpoint 内 paired comparison；invalid 保留在 planned denominator | exact-reference error reduction under declared setup | parameter reliability、global identifiability | PARTIALLY_SUPPORTED |
| C3 | state-freezing error 是当前 scalar cohort 中主要误差来源 | post-hoc exact decomposition；21 reconstructed centers | valid reconstructed centers | observed mechanism in tested cohorts | causal explanation、general law | SUPPORTED_WITHIN_SCOPE |
| C4 | SAEPS 等价于实际 nonlinear reoptimized profile curvature | V5 profile bridge；5 planned、5 evaluable、1 valid | profile seed | only if a new independent profile gate passes | nonlinear profile equivalence | NOT_SUPPORTED |
| C5 | SAEPS 可稳定预测 two-parameter joint geometry | P6；8/10 valid，低于 9/10 availability gate | planned checkpoint | availability-limited descriptive extension | confirmatory two-parameter claim | NOT_SUPPORTED |
| C6 | 非仿射参数、架构扩展和 stress anchors 中观察到相同方向 | E3/E6/E4–E8 archived evidence | declared seeds/centres only | descriptive extension under tested conditions | broad transfer、universal robustness | DESCRIPTIVE_ONLY |
| C7 | matrix-free SAEPS operator 在约 (10^5) state parameters 下可运行 | P8 scaling records | tested dimensions and stronger damping | operator feasibility at tested dimensions | production speedup、large-network accuracy | DESCRIPTIVE_ONLY |
| C8 | 论文可声称 SAEPS 提供 uncertainty、confidence interval 或 posterior information | no qualifying calibration evidence | none | omit | uncertainty、confidence、posterior | PROHIBITED |

## 当前主标题主张

在 S3 新 profile gate 通过前，采用收缩版本：

> SAEPS is a finite-damping, checkpoint-dependent local Gauss–Newton state-elimination diagnostic whose exact-reference error is evaluated under declared synthetic inverse-PINN conditions.

若新 profile gate 通过，才可将主张扩展为 nonlinear profile prediction，并必须同步更新本表、摘要和 `docs/ISSUES.md`。
