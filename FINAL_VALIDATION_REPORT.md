# FINAL_VALIDATION_REPORT.md

> **HISTORICAL v2 EVIDENCE — not the current paper-facing conclusion.** See [`V5_FINAL_JCP_AUDIT_REPORT.md`](V5_FINAL_JCP_AUDIT_REPORT.md) for the V5 final audit. The historical results below are preserved unchanged.

> **Historical scope notice:** This is the immutable-style final report for the completed v2 protocol and does not include later v3/v4 experiments. The current adjudicated state is v4.2 `SUPPORTED` for Burgers scalar exact-curvature comparison, with external replication, fresh controlled-mechanism closure, two-parameter exact geometry and scalability still outstanding. See `docs/v4_3_SUPPORTED_BRANCH_EXECUTION_CONTRACT.md`. This notice changes no v2 result or artifact.

## Repository status

Protocol `SAEPS-JCP-EXEC-v2.0`; global lock active at `ad794ca2908c8935d0e21702fab7914ff944cce7`. Artifact build: `PASSED`. Repository validator: `PASSED`.

## Engineering gates

| Phase | Engineering result | Scientific result |
|---|---|---|
| P0 | PASSED | N/A |
| P1 | PASSED | numerical core verified |
| P2 | PASSED | FAIL |
| P3 | PASSED | profile engine verified |
| P4 | PASSED | Burgers selected and protocol LOCKED |
| P5 | PASSED | PARTIALLY_SUPPORTED |
| P6 | PASSED | FAIL |
| P7 | PASSED / FULL | DESCRIPTIVE_ONLY |
| P8 | PASSED | DESCRIPTIVE_ONLY |
| P9 | PASSED | N/A |

## Confirmation completeness

- P2: 50/50 evaluations; 5/10 valid seeds; binding monotonic count 5/10.
- P5: 10/10 final records; 1/10 valid paired profiles; paired wins 1/10.
- P6: 10/10 final records; 0/10 valid directional pairs; ordering 0/10.
- P7: 55/55 new robustness/architecture runs.
- P8: 3/3 cost-only development runs.

## Scientific results and uncertainty

SG-1 failed because only 5/10 planned seeds passed the locked validity gate and monotonic requirement, despite near-unit Spearman correlation among the five valid seeds. SG-2 is partially supported by one valid positive pair: median D = 19.207146039181342; the bootstrap interval [19.207146039181342, 19.207146039181342] is degenerate because n=1 and is not strong evidence. SG-3 failed with zero valid directional profile pairs. P7 showed positive median elimination effects in every reported valid condition, but 12/55 new runs were invalid or failed and the evidence is descriptive only.

## Failed runs and deviations

P5 retained 9/10 invalid/failed records. P6 retained 10/10 invalid/failed records. P7 status counts are {'CHECKPOINT_INVALID': 2, 'PASS': 43, 'SOLVER_FAILURE': 10}. All failures are present in manifests and `paper_artifacts/data/supplementary/failed_runs.csv`. Protocol Amendments 001–004 are preserved; Amendments 003 and 004 are artifact-only and did not rerun scientific measurements.

## Computational cost

Median wall times (seconds): training 3.7658553999935975, SAEPS 5.220969800007879, frozen profile 0.004964000007021241, reoptimized profile 9.124859600007767. Median paired `T_reoptimized_profile/T_SAEPS` = 2.048278475698233. The observed acceleration is modest rather than order-of-magnitude. Peak native CPU tensor memory was unavailable and is explicitly null.

## Scientific conclusion

`PARTIALLY_SUPPORTED`

The numerical core is verified and limited valid scalar evidence favors SAEPS over raw sensitivity, but the preregistered controlled gate failed, only one scalar profile pair was valid, and no multi-parameter directional pair was valid. This supports only a limited, numerically qualified conclusion.

## Recommendation

`INVESTIGATE_NUMERICS`

Resolve stationarity, CG convergence and nonlinear-profile fit stability under a new protocol version before making broad method claims. Do not rerun or retune the locked v2.0 confirmation split.
