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
