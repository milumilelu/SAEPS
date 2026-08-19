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

## I-002 — Controlled checkpoint diagnostic stationarity mismatch

```text
date: 2026-08-19
issue_id: I-002
phase: P2 development
classification: numerical failure
description: The first committed P2 development run optimized seeded random training points but produced diagnostic theta-stationarity values 0.0461 to 0.1180, above the draft 0.01 confirmation gate.
evidence: Development run p2-development-s0-20260819T071251.094966+0000-9afa0dda4d34 on commit be1e6d93b444f2e6217d6f34abdb9f3b10bfe71c.
affected_runs: p2-development-s0-20260819T071251.094966+0000-9afa0dda4d34
protocol_impact: No confirmation run was started and the generated phase lock was not committed.
resolution_or_status: RESOLVED by using the task-book-compatible fixed tensor grid for both training and diagnostics and increasing development optimization. Seeds 0,1,2 then gave pilot S_theta 0.00212, 0.00832, 0.00212 without relaxing the 0.01 gate.
```

## I-003 — Initial gamma plateau selector had no eligible pair

```text
date: 2026-08-19
issue_id: I-003
phase: P2 development
classification: numerical failure
description: The rule requiring both endpoints of a 5% adjacent plateau pair to pass CG found no pair. CG eligibility was [false,true,true,true,true,true]; the first two eligible points differed by 12.3% under the then-used matrix-free eta statistic.
evidence: scripts/02_develop_controlled.py exited nonzero on committed implementation db1d108 before creating a development result or lock.
affected_runs: No run ID was issued because failure preceded provenance/result creation.
protocol_impact: No confirmation run was started and no phase lock was created.
resolution_or_status: RESOLVED in development by separating the dense explicit plateau diagnostic from matrix-free CG eligibility. The locked selector is the smallest CG-eligible point whose explicit eta changes by at most the unchanged 5% tolerance from the preceding smaller gamma.
```

## I-004 — P2 scientific gate not supported on locked denominator

```text
date: 2026-08-19
issue_id: I-004
phase: P2 confirmation
classification: scientific failure
description: Only 5/10 confirmation checkpoints passed the locked S_theta<=0.01 gate. Those five were all monotonic with Spearman approximately 1, but the preregistered 8/10 monotonic requirement was not met.
evidence: docs/evidence/P2_ACCEPTANCE.md; run p2-confirmation-s10-20260819T072235.025972+0000-7059ee357d5a.
affected_runs: Seeds 10,11,12,13,16 each have five CHECKPOINT_INVALID records; all 50 planned records remain in the manifest.
protocol_impact: SG-1=FAIL. P2 engineering gate remains PASSED, so P3 may proceed. Final claims must retain this negative result.
resolution_or_status: OPEN scientific result. No threshold, source, gamma, seed, or alpha will be changed and confirmation will not be rerun.
```

## I-005 — P4 development screening audit and fit-rule corrections

```text
date: 2026-08-19
issue_id: I-005
phase: P4 development
classification: implementation failure
description: Early screening attempts failed before preserving evidence, emitted a non-JSON -Infinity clarity sentinel, applied synthetic profile thresholds to real PINNs, and incorrectly counted quadratic-fit failures as reoptimization failures.
evidence: Development-only failed attempts preceding p4-screening-s0-20260819T080159.676328+0000-56ebdbadfb52; no confirmation seed was run.
affected_runs: Failed/unaccepted P4 development directories remain under outputs/runs/p4_screening.
protocol_impact: None on confirmation. All corrections were made using seeds 0,1,2 before global LOCK.
resolution_or_status: RESOLVED. Failed development now serializes legal nulls; real-PINN profile thresholds/window are uniform; 42/42 optimization statuses are separated from fit quality; final clean screening evidence is preserved.
```

## I-006 — P5 confirmation has inadequate valid profile coverage

```text
date: 2026-08-19
issue_id: I-006
phase: P5 confirmation
classification: scientific failure
description: Only seed 18 produced a valid paired curvature comparison. Seed 10 failed the locked checkpoint gate; seeds 11-17 and 19 completed every optimization point but failed locked quadratic R2.
evidence: docs/evidence/P5_ACCEPTANCE.md and p5-scalar-s10-20260819T082303.440919+0000-ecf337e72926.
affected_runs: 1 CHECKPOINT_INVALID, 8 PROFILE_FAILURE, 1 PASS out of 10 planned.
protocol_impact: SG-2 is only PARTIALLY_SUPPORTED. P7 proceeds because the locked protocol-stop trigger is NOT_SUPPORTED, but final recommendation must emphasize unresolved profile/numerical limitations.
resolution_or_status: OPEN locked scientific/numerical result. No confirmation rerun or lock modification is permitted.
```

## I-007 — P6 has no valid directional profile pair

```text
date: 2026-08-19
issue_id: I-007
phase: P6 confirmation
classification: scientific failure
description: P6 produced 4 checkpoint-invalid, 4 solver-failure and 2 profile-failure seeds, leaving zero valid eigendirection pairs and no eligible seed for the 5x5 grid.
evidence: docs/evidence/P6_ACCEPTANCE.md and p6-multi-s10-20260819T082908.416321+0000-e44ef183ef75.
affected_runs: all 10 locked P6 confirmation seeds.
protocol_impact: SG-3=FAIL. The first-valid grid is NOT_APPLICABLE because selecting an invalid seed is forbidden. Final evidence is numerically limited.
resolution_or_status: OPEN locked result. No CG/profile threshold changes and no rerun are permitted.
```

## I-008 — P7 failures concentrate under sparsity and wide architecture

```text
date: 2026-08-19
issue_id: I-008
phase: P7 robustness
classification: descriptive numerical limitation
description: Of 55 new runs, 10 failed the locked CG tolerance and 2 failed the locked checkpoint gate. The noise=0.01/fraction=0.25 cell retained only 2/5 valid runs; wide architecture retained 3/5.
evidence: docs/evidence/P7_ACCEPTANCE.md and p7-robustness-s10-20260819T084233.286983+0000-fa8846c72a36.
affected_runs: 12/55 new P7 records; every failed record remains in the manifest with its final status and reason.
protocol_impact: P7 engineering remains PASSED because all planned runs completed with legal statuses. P7 has no positive scientific threshold and cannot repair SG-1, SG-2 or SG-3.
resolution_or_status: OPEN descriptive result. No locked threshold, gamma or method setting was changed and no P7 run will be repeated.
```

## I-009 — P8 speedup is modest and profile fits remain fragile

```text
date: 2026-08-19
issue_id: I-009
phase: P8 computational cost
classification: descriptive practical/numerical limitation
description: The paired median reoptimized-profile/SAEPS time ratio is 2.0483, not an order-of-magnitude gain. All 21 reoptimization points completed, but only 1/3 reoptimized profile fits passed locked fit quality.
evidence: docs/evidence/P8_ACCEPTANCE.md and p8-cost-s0-20260819T085547.064222+0000-b80f00209a91.
affected_runs: three cost-only development seeds [0,1,2].
protocol_impact: P8 engineering remains PASSED and is descriptive. The result limits practical speed claims and reinforces the P5 profile-quality concern.
resolution_or_status: OPEN descriptive result. No post hoc cost threshold was introduced and no timing run will be repeated.
```

## I-010 — v3 common-base refinement first development attempt failed

```text
date: 2026-08-19
issue_id: I-010
phase: V3 foundation development
classification: numerical failure
description: The first seed-20 common-base refinement reduced mean loss from 0.0366474 to 0.0237451 but failed both the registered plateau and normalized-gradient stopping thresholds after 20 outer steps. Its Adam warmup plus repeated LBFGS path ended with normalized gradient 0.0012525, larger than the incoming checkpoint value 0.0006206.
evidence: outputs/runs/v3_foundation/v3-foundation-s20-20260819T114025.011649+0000-9f1cb97b7363.
affected_runs: The failed development run is retained with PROFILE_FAILURE and no downstream curvature calculation.
protocol_impact: None on v2 and no v3 confirmation was authorized. This exposed an over-strict and counterproductive development optimizer setting before any v3 lock.
resolution_or_status: DEVELOPMENT CORRECTION. Remove the Adam warmup for fixed-parameter base refinement, use direct LBFGS from the already-trained checkpoint, and use a combined 0.002 plateau / 0.002 normalized-gradient rule. This remains stricter than the v2 locked profile gradient threshold of 0.005 and is applied before any successful foundation result is observed.
```

## I-011 — v3 foundation exposes nonpositive exact state Hessians and unusable profiles

```text
date: 2026-08-19
issue_id: I-011
phase: V3 foundation development
classification: scientific failure
description: After the corrected common-base refinement passed its registered engineering stopping rule, the exact unregularized and gamma-matched state Hessian blocks had respectively 18 and 16 eigenvalues at or below the positive-definiteness tolerance. Their minimum eigenvalues were -1.6379580 and -1.6348888, so neither exact Schur reduction is valid. All eight unregularized profile points and six of eight gamma-matched points failed the registered optimizer rule, leaving no multiscale curvature estimates.
evidence: outputs/runs/v3_foundation/v3-foundation-s20-20260819T114157.433693+0000-00bb43b42152.
affected_runs: v3 foundation seed 20 only; this is development evidence and is excluded from v2 and any future confirmation statistics.
protocol_impact: The five requested diagnostics are executable, but they refute treating the present checkpoint as a locally convex state-profiled reference. v3 confirmation readiness is not established.
resolution_or_status: OPEN scientific result. Preserve the negative result and correct only the full-Hessian top-level status aggregation so invalid child reductions report NUMERICAL_FAILURE. Do not relax profile or Hessian thresholds and do not tune for a favorable curvature result.
```

## I-012 — Fresh-clone audit exposed platform-dependent raw hashes

```text
date: 2026-08-19
issue_id: I-012
phase: V3 foundation acceptance / fresh-clone audit
classification: implementation failure
description: The first clean clone reproduced the tracked numeric content but failed the v2 snapshot before repository validation. Historical raw JSON files were CRLF in the source worktree while Git checked them out as LF under .gitattributes; the snapshot and several historical manifests had recorded physical CRLF byte hashes.
evidence: fresh clone C:/Users/RZF/AppData/Local/Temp/saeps-fresh-clone-ae778484b217498ebe56130b74cc4007; first mismatch was outputs/runs/p1/p1-core-s20260819-20260819T065537.942753+0000-828593bb8854/result.json.
affected_runs: No numeric run content changed. The defect affected cross-platform verification of text-file bytes only.
protocol_impact: Fresh-clone auditability was not yet achieved; v2 scientific results and locked hashes were unaffected.
resolution_or_status: RESOLVED by versioning snapshot schema 2 with canonical-LF byte counts/hashes and allowing historical run/artifact manifests to match only raw, canonical-LF, or canonical-CRLF byte variants. A content change other than newline encoding still fails verification.
```

## I-013 — v3.1 first saddle-escape budget ended while descent remained

```text
date: 2026-08-19
issue_id: I-013
phase: V3.1 state-minimum development
classification: numerical failure
description: The first seed-20 run reduced center mean loss from 0.0366474 to 0.00391424 and passed the common 1e-4 objective-gradient gate, but failed the exact Hessian gate with lambda_min=-1.9064e-5, tau=7.9877e-7 and four negative directions. All 12 registered negative-direction probes found actual lower-loss points, so the fixed cycle budget—not absence of an escape direction—caused termination.
evidence: outputs/runs/v3_1_state_minimum/v3-1-state-min-s20-20260819T122121.398764+0000-d11519b48fd2.
affected_runs: seed 20 development attempt only. No profile, Krylov comparison, seed 21–24 or confirmation run was started.
protocol_impact: The strict center gate correctly stopped the chain. No scientific threshold is changed.
resolution_or_status: DEVELOPMENT CORRECTION. Increase only the exact-Hessian saddle-escape cycle budget from 12 to 50 because every observed cycle retained a verified descent direction. Gradient tolerance, Hessian tau, profile convergence and solver gates remain unchanged. This is not an L-BFGS-iteration-only remedy.
```
