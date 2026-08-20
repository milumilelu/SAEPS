# DECISIONS.md

所有影响实验设计的决定按以下模板追加，禁止覆盖历史记录。

```text
date:
decision_id:
decision:
reason:
development_evidence:
affected_configs:
authorizing_protocol:
```

## D-000 — Adopt v2.0

```text
date: 2026-08-19
decision_id: D-000
decision: Adopt SAEPS-JCP-EXEC-v2.0 as the active execution contract.
reason: User supplied SAEPS 新仓库实验任务书 v2.0 and requested protocol synchronization.
development_evidence: Not applicable; governance update only.
affected_configs: None; no confirmation config exists.
authorizing_protocol: docs/protocol_amendments/AMENDMENT_002_V2_PROTOCOL.md
```

## D-001 — Lock P2 controlled geometry

```text
date: 2026-08-19
decision_id: D-001
decision: Lock q_parallel=sin(3*pi*x)sin(2*pi*t), q_perpendicular=sin(4*pi*x), the fixed tensor-grid tanh 2x8x1 protocol, checkpoint gates, and nominal gamma_alpha=1e-10 for P2 confirmation.
reason: Deterministic development rules selected maximum median tangent overlap and minimum median overlap among empirically orthogonal Fourier candidates. The gamma selector chose the first CG-eligible point within the unchanged 5% explicit plateau tolerance from the preceding smaller gamma.
development_evidence: docs/evidence/P2_DEVELOPMENT.md and p2-development-s0-20260819T072005.205758+0000-bc9e08a3bcd1.
affected_configs: configs/locked/controlled_geometry.yaml (SHA256 32003edbcfbe03c6bf357ffce25051ba9b279263a15d2e80b4c762087ec0c30e).
authorizing_protocol: SAEPS-JCP-EXEC-v2.0 sections 8 and 11.
```

## D-002 — Carry P3 profile rules into global lock

```text
date: 2026-08-19
decision_id: D-002
decision: Adopt the seven default offsets, independent theta0 initialization, combined LBFGS/plateau/gradient stopping rule, and quadratic fit-quality gates from configs/p3_profile.yaml for the forthcoming global protocol lock.
reason: The synthetic optimization test recovered known frozen/reoptimized curvature and minimum, was invariant to point order, reproduced exactly, and rejected failed/missing points.
development_evidence: docs/evidence/P3_ACCEPTANCE.md.
affected_configs: configs/p3_profile.yaml; future configs/locked/scalar.yaml.
authorizing_protocol: SAEPS-JCP-EXEC-v2.0 sections 12 and P3 acceptance criteria.
```

## D-003 — Select Burgers and create the global confirmation lock

```text
date: 2026-08-19
decision_id: D-003
decision: Select Burgers for scalar confirmation and freeze scalar, CRD multi-parameter, robustness, bootstrap, profile, gamma and artifact protocols.
reason: Both scalar candidates passed hard gates and 3/3 stationarity. Burgers first won at the preregistered classical curvature-clarity criterion (median R2 0.999846 vs 0.998425). No forbidden SAEPS/result metric was consulted.
development_evidence: docs/evidence/P4_SCREENING.md and docs/evidence/P6_DEVELOPMENT.md.
affected_configs: configs/locked/scalar.yaml, multi.yaml, robustness.yaml and their SHA256 sidecars.
authorizing_protocol: SAEPS-JCP-EXEC-v2.0 sections 4.2, 8, 13 and subsequent locked confirmation phases.
```

## D-004 — Open isolated v3 foundation development

```text
date: 2026-08-19
decision_id: D-004
decision: Preserve v2 unchanged and create a development-only v3 namespace for five foundation corrections.
reason: The v2 negative audit exposed regularization, Gauss-Newton/exact-Hessian, base-state, curvature-estimation and external-reproducibility gaps. The user explicitly authorized a separate v3 rather than retuning v2.
development_evidence: v2 FINAL_VALIDATION_REPORT.md and user-authorized review response; no v3 result was inspected before this decision.
affected_configs: configs/v3/foundation_development.yaml only; configs/locked/* remain unchanged.
authorizing_protocol: docs/protocol_amendments/AMENDMENT_005_V3_FOUNDATION.md and docs/v3/EXECUTION_CONTRACT.md.
```

## D-005 — Require a true state local minimum before v3 curvature comparison

```text
date: 2026-08-19
decision_id: D-005
decision: Open an isolated v3.1 seed-20 development workflow with unified 1e-4 objective-gradient tolerance, exact state-Hessian gate, negative-direction probes, trust-region saddle escape and Jacobi-PCG diagnostics.
reason: v3.0 located the failure at nonlinear state optimization and second-order geometry: the nominal center passed a loose first-order rule while exact state Hessians remained indefinite and profiles failed. Increasing L-BFGS iterations alone cannot establish a local minimum.
development_evidence: docs/evidence/V3_FOUNDATION_ACCEPTANCE.md; no v3.1 run was inspected before this decision.
affected_configs: configs/v3_1/seed20_development.yaml only; v2 locked and v3.0 configurations remain unchanged.
authorizing_protocol: docs/protocol_amendments/AMENDMENT_006_V3_1_STATE_MINIMUM.md and docs/v3_1/EXECUTION_CONTRACT.md.
```

## D-006 — Make gamma-matched profiling the v3.2 primary chain

```text
date: 2026-08-19
decision_id: D-006
decision: Open isolated v3.2 seed-20 development with gamma-matched profile as primary and unregularized profile as a nonbinding gamma-to-zero diagnostic.
reason: v3.1 successfully established numerical local-minimum candidates at the center and all unregularized points, but the unregularized curvature lacked a stable h-to-zero limit. That result diagnoses unregularized weight-geometry instability and must not preempt the finite-gamma SAEPS validation actually defined by the method.
development_evidence: docs/evidence/V3_1_SEED20_ACCEPTANCE.md; no v3.2 result was inspected before this decision.
affected_configs: configs/v3_2/seed20_gamma_primary.yaml only; v2, v3.0 and v3.1 remain unchanged.
authorizing_protocol: docs/protocol_amendments/AMENDMENT_007_V3_2_GAMMA_PRIMARY.md and docs/v3_2/EXECUTION_CONTRACT.md.
```

## D-007 — Open v3.3 numerical-decomposition development

```text
date: 2026-08-19
decision_id: D-007
decision: Open isolated v3.3 seed-20 development and retain a nonbinding four-node decomposition even when a registered solver or profile gate fails.
reason: v3.2 simultaneously exposed gamma-profile convergence/accuracy failure and normal-equation Krylov failure, while the exact gamma reduction passed. Suppressing the comparison after either failure prevents attribution among solver, Gauss--Newton and nonlinear-profile errors.
development_evidence: docs/evidence/V3_2_SEED20_ACCEPTANCE.md; the v3.3 solver and error definitions were registered before any v3.3 run.
affected_configs: configs/v3_3/seed20_numerical_decomposition.yaml only; v2 through v3.2 remain unchanged.
authorizing_protocol: docs/protocol_amendments/AMENDMENT_008_V3_3_NUMERICAL_DECOMPOSITION.md and docs/v3_3/EXECUTION_CONTRACT.md.
```

## D-008 — Freeze v3.4 curvature-validation hierarchy before seeds 21–24

```text
date: 2026-08-20
decision_id: D-008
decision: Separate curvature, score and preconditioner solver gates; use the exact gamma Schur complement as the small-network local gold standard; and classify profile scales with a numerical-resolution certificate rather than requiring the smallest h to pass.
reason: V3.3 showed 1e-9 to 1e-10 agreement among parameter-curvature solvers despite auxiliary residual-RHS failures, only 1.1724% GN-to-exact error, and dominant instability at the finest nonlinear-profile scale. The mathematical objects and validation roles must therefore be separated.
development_evidence: docs/evidence/V3_3_SEED20_ACCEPTANCE.md and the user-supplied v3.3 review. No seed 21–24 v3.4 result was observed before this decision.
affected_configs: configs/v3_4/curvature_validation.yaml only; v2 through v3.3 remain unchanged.
authorizing_protocol: docs/protocol_amendments/AMENDMENT_009_V3_4_CURVATURE_VALIDATION.md and docs/v3_4/EXECUTION_CONTRACT.md.
```

## D-009 — Open v3.5 second-order diagnostics and new-seed engineering

```text
date: 2026-08-20
decision_id: D-009
decision: Explain cross-seed GN error through exact residual-Hessian block/Shapley decomposition before changing SAEPS, and isolate center/solver engineering on new seeds 25–29.
reason: V3.4 preserved strong raw-to-reduced absorption but found GN-to-exact errors of 1.17%, 8.24%, 9.33% and 4.97%, plus independent center and scalable-solver failures. These mechanisms must be measured separately.
development_evidence: docs/evidence/V3_4_ACCEPTANCE.md; no seed 25–29 result was observed before this decision.
affected_configs: configs/v3_5/diagnostic_engineering.yaml only; v2 through v3.4 remain unchanged.
authorizing_protocol: docs/protocol_amendments/AMENDMENT_010_V3_5_SECOND_ORDER_ENGINEERING.md and docs/v3_5/EXECUTION_CONTRACT.md.
```

## D-010 — Lock v3.6 untouched scalar-curvature confirmation

```text
date: 2026-08-20
decision_id: D-010
decision: Close development and lock seeds 30--44 for a one-shot scalar-curvature confirmation using the frozen baseline-then-rescue center, two-pass scaled-LSQR refinement, exact finite-gamma reduced-Hessian gold standard and paired D=Eraw-Esaeps primary estimand.
reason: V3.5 established on development data that the scientifically relevant question is comparative improvement over raw fixed-state curvature, while absolute 5% SAEPS accuracy is not uniform. The new primary rule returns to that original comparative question without erasing the negative 5% finding.
development_evidence: docs/evidence/V3_5_ACCEPTANCE.md; seeds 30--44 were not run or inspected before this lock.
affected_configs: configs/v3_6/locked_scalar_confirmation.yaml; all earlier locks and results remain unchanged.
authorizing_protocol: docs/protocol_amendments/AMENDMENT_011_V3_6_CONFIRMATION_LOCK.md and docs/v3_6/LOCKED_PROTOCOL.md. This decision locks but does not authorize execution.
```
