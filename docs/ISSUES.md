# ISSUES.md

问题不得删除，按以下模板追加：

```text
date:
issue_id:
phase:
classification: implementation failure | numerical failure | benchmark failure | scientific failure
description:
evidence:
affected_runs:
protocol_impact:
resolution_or_status:
```

## I-001 — Development validation parameter cancellation

```text
date: 2026-08-19
issue_id: I-001
phase: P1
classification: implementation failure
description: The first development-only tiny residual constructed its reference PDE right-hand side with the current parameter, algebraically cancelling the second parameter sensitivity.
evidence: The discarded result had eta=[0.1938771073059169, 0.0] and a zero second row/column in both exact and Tikhonov curvature.
affected_runs: p1-core-s20260819-20260819T065537.942753+0000-828593bb8854
protocol_impact: None. The run preceded the P1 implementation commit and was excluded from acceptance evidence.
resolution_or_status: RESOLVED before commit c4becc79f1e6d0968f55c27ae90c36898798e5af by fixing the reference right-hand side at the true physical parameters. The clean acceptance run has two nonzero eta values.
```
