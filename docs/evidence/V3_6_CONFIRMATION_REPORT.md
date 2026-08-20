# v3.6 Scalar Confirmation Report

**Scientific status:** `NOT_SUPPORTED`  
**Execution status:** `PERMANENTLY_CLOSED_IMPLEMENTATION_FAILURE`  
**Planned / valid / invalid:** `15 / 0 / 15`

## Locked adjudication

All four frozen primary conditions are false. There are no valid pairs, no planned wins, no median D and no computable sign test. The locked result is therefore `NOT_SUPPORTED` because the minimum-valid-pair condition failed.

This result does **not** show that SAEPS is worse than raw curvature. The comparative hypothesis was not tested because no valid paired estimand was produced.

## Terminal statuses

- `PASS`: 0
- `CHECKPOINT_INVALID`: 1
- `SOLVER_FAILURE`: 14
- `NUMERICAL_FAILURE`: 0
- `PROFILE_FAILURE`: 0

## Mandatory implementation finding

The read-only audit isolates a protocol-implementation defect on all 14 solver-failed seeds. The explicit augmented reference combined the parameter-curvature RHS with an excluded residual/score RHS and bound the maximum residual across both to the gate. For every affected seed, the parameter reference, selected two-pass scaled-LSQR residual and curvature agreement pass their frozen curvature thresholds; only the excluded score RHS exceeds the direct-reference threshold.

Because v3.6 is one-shot and the raw records do not contain all primary quantities for these failed seeds, no corrected v3.6 reaggregation or rerun is permitted. The failure classification is `implementation failure / numerical availability failure`, not comparative scientific failure.

## Permanent closure

Seeds 30--44 have exactly one terminal result each. The run is permanently closed. Any correction must use a new named `POST_CONFIRMATION_DEVELOPMENT` version with new seeds and a new untouched confirmation cohort.

Machine evidence: `docs/evidence/v3_6_confirmation.json`; raw manifest hash: `3c7061a963710d28579661ae5792e9e55642119a6777e7d04097d5c16b544aa9`.
