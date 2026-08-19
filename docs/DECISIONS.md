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
