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

## I-014 — v3.1 seed-20 local minima do not yield convergent unregularized curvature

```text
date: 2026-08-19
issue_id: I-014
phase: V3.1 state-minimum development
classification: scientific failure
description: The center and all eight unregularized profile points passed the common 1e-4 objective-gradient and exact state-Hessian gates. Nevertheless, symmetric profile curvature changed 19.2297 -> 16.0247 -> 8.71031 -> -1.45182 over h=[0.05,0.025,0.0125,0.00625]. The two binding finest relative changes were 0.839743 and 6.999596, both above 0.05.
evidence: outputs/runs/v3_1_state_minimum/v3-1-state-min-s20-20260819T122328.472834+0000-629b7eb8ec88 and docs/evidence/V3_1_SEED20_ACCEPTANCE.md.
affected_runs: seed 20 development only.
protocol_impact: Full-chain gate FAIL. Gamma-matched profile, Krylov gate, exact reduced-Hessian comparison, seeds 21-24 and confirmation were not run.
resolution_or_status: OPEN scientific result. Do not tune profile tolerances or h values using this result. A new user-authorized development amendment would be required to distinguish branch switching, finite optimization accuracy and genuine lack of twice-differentiable reduced geometry.
```

## I-015 — v3.2 gamma profile is locally positive but fails finest accuracy/convergence

```text
date: 2026-08-19
issue_id: I-015
phase: V3.2 gamma-primary development
classification: scientific failure
description: Both nominal and strict gamma-matched continuation profiles had 8/8 numerical local-minimum candidates with positive state-Hessian minima near 2.04e-4. Strict curvature was 35.8240, 35.7741, 35.4660 and 33.4943 over the four h scales. The finest adjacent change was 5.8868%, above the registered 5% gate, and the nominal/strict difference at h=0.00625 was 21.4971%.
evidence: outputs/runs/v3_2_gamma_primary/v3-2-gamma-primary-s20-20260819T133259.913719+0000-defb083d1a75 and docs/evidence/V3_2_SEED20_ACCEPTANCE.md.
affected_runs: seed 20 development only.
protocol_impact: Gamma-matched primary profile FAIL. The exact gamma reduction passed, but primary comparison is forbidden and seeds 21-24 remain inactive.
resolution_or_status: OPEN. Do not relax the 5% gates, discard the finest scale or choose nominal/strict accuracy post hoc. A new protocol is required for branch/accuracy/function-space investigation.
```

## I-016 — v3.2 standard CG and Jacobi-PCG both fail the seed-20 solver gate

```text
date: 2026-08-19
issue_id: I-016
phase: V3.2 gamma-primary development
classification: numerical failure
description: Standard matrix-free CG failed within 500 iterations with verified residual about 1.20e-7 on at least one solve. Exact-development Jacobi-PCG also failed: its two verified residuals were about 1.40e-5 and 0.2905 after 500 iterations. The diagonal preconditioner degraded the residual right-hand-side solve.
evidence: the krylov_gate record in v3-2-gamma-primary-s20-20260819T133259.913719+0000-defb083d1a75.
affected_runs: seed 20 development only.
protocol_impact: Solver gate FAIL independently of the gamma-profile failure. This confirms that the v2 CG robustness issue is not resolved by simple Jacobi scaling.
resolution_or_status: OPEN. Do not raise iteration limits or residual tolerances using this result. A separately preregistered Krylov/preconditioner development study is required.
```

## I-017 — v3.3 full-RHS solver gates fail while parameter curvature agrees

```text
date: 2026-08-19
issue_id: I-017
phase: V3.3 numerical-decomposition development
classification: numerical failure
description: Standard CG, Jacobi-PCG, augmented LSQR and the strict direct audit do not all pass their registered full-RHS gates. However, the parameter-column CG solve passes at relative residual 5.78e-11 and its curvature differs from explicit direct by only 2.58e-9. Augmented LSQR differs from explicit by 2.15e-10. Failures are driven mainly by the auxiliary residual RHS; Jacobi-PCG remains materially less accurate.
evidence: outputs/runs/v3_3_numerical_decomposition/v3-3-num-decomp-s20-20260819T142127.327595+0000-3b23a23db90f and docs/evidence/V3_3_SEED20_ACCEPTANCE.md.
affected_runs: seed 20 v3.3 development only.
protocol_impact: Registered chain remains FAIL and no paper-facing comparison is emitted. The nonbinding decomposition establishes that standard-CG solver error does not explain the seed-20 parameter-curvature discrepancy.
resolution_or_status: OPEN. Preserve full-RHS failures. Future solver work should distinguish parameter-curvature and score/residual RHS objectives and investigate augmented Krylov stopping without changing these observed gates post hoc.
```

## I-018 — v3.3 locates the largest seed-20 discrepancy at the profile layer

```text
date: 2026-08-19
issue_id: I-018
phase: V3.3 numerical-decomposition development
classification: scientific failure
description: Explicit GN differs from the valid exact gamma reduction by 1.172%, whereas exact gamma differs from the strict finest profile curvature by 7.045%. The total explicit-GN to profile discrepancy is 8.300%. The profile endpoint still fails registered multiscale and optimization-accuracy gates.
evidence: docs/evidence/V3_3_SEED20_ACCEPTANCE.md and the accepted v3.3 raw run.
affected_runs: seed 20 v3.3 development only.
protocol_impact: The decomposition favors nonlinear/profile error over GN or parameter-curvature solver error as the dominant observed segment, but cannot validate a scientific equality because Hprofile is not converged.
resolution_or_status: OPEN. Continue branch/optimization/function-space diagnosis only under a new amendment; do not reinterpret this nonbinding diagnostic as paper evidence or activate additional seeds.
```

## I-019 — First v3.4 seeds 22–24 attempts have dirty provenance

```text
date: 2026-08-20
issue_id: I-019
phase: V3.4 curvature-validation development
classification: implementation failure
description: Seeds 21–24 were first launched sequentially in one shell after a clean seed20 acceptance commit. Seed21 correctly recorded a clean worktree, but its untracked output made provenance.git_dirty=true for the first attempts of seeds 22–24.
evidence: first-attempt run IDs v3-4-curvature-s22-20260819T161010.489555+0000-627a3d606103, v3-4-curvature-s23-20260819T161346.185202+0000-89a746206c9b, and v3-4-curvature-s24-20260819T161609.839251+0000-2d27d5327755.
affected_runs: the three named first attempts only; seed21 is clean and remains accepted.
protocol_impact: Numeric attempts are retained but are ineligible for formal v3.4 aggregation. No config, threshold, seed, optimizer, or scientific rule changes.
resolution_or_status: RESOLVED operationally by committing all attempts, then rerunning seeds 22, 23 and 24 one at a time from a clean worktree and committing each before starting the next seed. Acceptance selects only clean-provenance runs by a rule independent of numeric outcomes.
```

## I-020 — v3.4 seed20 local agreement does not generalize to 21–24

```text
date: 2026-08-20
issue_id: I-020
phase: V3.4 curvature-validation development
classification: scientific failure
description: None of four frozen evaluation seeds passes the complete v3.4 readiness chain. Seed21 fails the common-center numerical-minimum gate. Among seeds 22–24, only seed24 passes the 5% local GN-to-exact gate; errors are 8.24%, 9.33%, and 4.97%. Curvature solver passes 2/3 and finite-radius validation passes 1/3 center-valid evaluation seeds.
evidence: docs/evidence/V3_4_ACCEPTANCE.md and docs/evidence/v3_4_validation.json.
affected_runs: accepted clean-provenance v3.4 seeds 20–24; dirty first attempts remain excluded by I-019.
protocol_impact: Development generalization is NOT_ESTABLISHED. Confirmation seeds 30–44 remain forbidden. Seed20 cannot be presented as representative cross-seed evidence.
resolution_or_status: OPEN scientific result. Do not relax 5% gates, increase solver iterations, select favorable scales, or rerun seeds. Any next investigation requires a new development amendment and must retain this negative denominator.
```

## I-021 — v3.5 engineering improves but does not eliminate center/solver limitations

```text
date: 2026-08-20
issue_id: I-021
phase: V3.5 second-order engineering development
classification: numerical failure
description: The baseline center passes 2/5 new seeds and the frozen rescue raises validity to 4/5, leaving seed27 invalid. Two-pass scaled-LSQR refinement passes 4/4 valid centers but costs 1500 iterations plus 65 exact-development setup JVPs per seed.
evidence: docs/evidence/V3_5_ENGINEERING_SELECTION.md and docs/evidence/V3_5_ACCEPTANCE.md.
affected_runs: engineering seeds 25–27 and held-out development seeds 28–29.
protocol_impact: Engineering generalization is improved and held-out 2/2, but neither perfect center robustness nor practical large-network scalability is established.
resolution_or_status: OPEN limitation. Do not relax center/solver thresholds. Any future confirmation lock must retain invalid planned seeds and report setup/iteration cost.
```

## I-022 — v3.5 first-order trust indicator is promising but development-selected

```text
date: 2026-08-20
issue_id: I-022
phase: V3.5 second-order diagnostic development
classification: scientific limitation
description: Among six preregistered candidates, the first-order reduced-correction ratio has Spearman 0.8095, 8/8 same-5% classification and median calibration error 0.0345 across valid development seeds. Individual block norm ratios perform poorly because signed Shapley contributions cancel.
evidence: docs/evidence/v3_5_validation.json.
affected_runs: eight valid development seeds across retrospective, engineering and held-out roles.
protocol_impact: The indicator may be frozen for future confirmation reporting, but cannot be described as validated or recalibrated using confirmation results.
resolution_or_status: OPEN scientific validation requirement. Confirmation remains unauthorized.
```

## I-023 — v3.6 curvature-only confirmation was invalidated by an excluded score-RHS gate

```text
date: 2026-08-20
issue_id: I-023
phase: V3.6 one-shot scalar confirmation
classification: implementation failure
description: The one-shot runner reused an explicit augmented-reference status defined as the maximum normal residual over both the parameter-curvature RHS and residual/score RHS. V3.6 scope is curvature only. All 14 solver-failed seeds pass the parameter-reference residual, selected two-pass scaled-LSQR residual, objective identity and curvature-agreement thresholds; only the excluded score RHS exceeds the direct 1e-10 threshold. Seed37 independently fails the frozen center.
evidence: docs/evidence/v3_6_confirmation.json, docs/evidence/V3_6_CONFIRMATION_REPORT.md and outputs/runs/v3_6_scalar_confirmation.
affected_runs: the sole and permanent v3.6 seeds 30--44 cohort; 14 SOLVER_FAILURE and 1 CHECKPOINT_INVALID, 0 valid pairs.
protocol_impact: The locked automatic result is NOT_SUPPORTED for insufficient valid pairs. The comparative SAEPS-versus-raw hypothesis and frozen GN indicator were not tested. Raw records lack all primary quantities for the solver-failed seeds, so a corrected v3.6 reaggregation is impossible without forbidden recomputation/rerun.
resolution_or_status: PERMANENTLY CLOSED. Do not rerun, edit or continue v3.6. Open only a new POST_CONFIRMATION_DEVELOPMENT version on new seeds, separate curvature and score gates, and require an untouched future confirmation cohort for any corrected method.
```

## I-024 — v4.2 post-seed aggregation required a non-scientific schema adapter

```text
date: 2026-08-20
issue_id: I-024
phase: V4.2 corrected untouched confirmation
classification: implementation failure
description: All 15 one-shot seed records were written, but the frozen aggregator expected a reporting-only failure_stage key absent from the v4.1 independent-status raw schema. Aggregation therefore stopped after seed69. Raw records contained every primary quantity for valid seeds and complete independent statuses for invalid seeds.
evidence: outputs/runs/v4_2_corrected_confirmation, docs/evidence/v4_2_confirmation.json and scripts/36_finalize_interrupted_v4_2_from_raw.py.
affected_runs: no seed computation; aggregation only. Seeds 55--69 were not rerun.
protocol_impact: A fail-closed recovery derived failure_stage only in memory from frozen independent statuses and invoked the byte-locked aggregator. No raw record, primary value, threshold, seed or scientific formula changed. Independent raw-to-aggregate reproduction passes and yields SUPPORTED under all four locked conditions.
resolution_or_status: RESOLVED WITH RECORDED DEVIATION. V4.2 remains one-shot and permanently closed. Future runners must integration-test raw schema against the aggregator before lock.
```

## I-025 — Allen--Cahn seed70 rejects direct reuse of the Burgers center policy

```text
date: 2026-08-21
issue_id: I-025
phase: V4.3 Allen-Cahn external-replication development
classification: numerical failure
description: The first real Allen-Cahn development attempt completed stable training but the byte-inherited Burgers baseline-then-enhanced center policy failed the exact second-order gate. Baseline used 51 cycles and enhanced rescue used 91 cycles; the final enhanced minimum state-Hessian eigenvalue was -3.0705e-6 versus tau 5.6283e-8, while the normalized objective gradient was 4.2850e-7.
evidence: outputs/runs/v4_3_allen_cahn_development/seed_70.
affected_runs: Allen-Cahn development seed70 initial frozen-policy attempt only.
protocol_impact: Confirms the v4.0 warning that Burgers numerical settings cannot be assumed valid cross-PDE. The failed attempt is retained. Center engineering is restricted to seeds 70--72 and may use only exact center validity/loss, never D or SAEPS advantage; seeds 73--74 are held out until an executable freeze.
resolution_or_status: OPEN DEVELOPMENT. Evaluate deterministic damped-GN/multistart center engineering without relaxing the exact first- or second-order thresholds.
```

## I-026 — v4.4 post-seed packaging used an incorrect result directory

```text
date: 2026-08-21
issue_id: I-026
phase: V4.4 Allen-Cahn external confirmation
classification: implementation failure
description: All ten one-shot seed computations and the frozen aggregate summary were written successfully, after which the execution wrapper attempted to hash records/seed_N/result.json although the frozen seed runner had written architecture_w8/seed_N/result.json.
evidence: outputs/runs/v4_4_allen_cahn_confirmation, the terminal FileNotFoundError, and scripts/44_finalize_interrupted_v4_4_from_raw.py.
affected_runs: no seed computation; top-level manifest and failed-seed packaging only. Seeds 75--84 were each computed exactly once and must not be rerun.
protocol_impact: The existing summary was produced by the frozen aggregator before the exception. Recovery may only hash the existing raw files at their actual paths, generate missing packaging artifacts, and independently reproduce the aggregate. No raw record, scientific value, threshold, status rule, seed or locked executable may change.
resolution_or_status: RESOLVED WITH RECORDED DEVIATION. Raw outputs were committed unchanged before recovery. The one-shot finalizer generated only the missing packaging artifacts from actual raw paths; independent frozen-aggregate reproduction and all raw hashes pass. Seeds 75--84 are permanently closed.
```

## I-027 — v4.5 seed85 first attempt exposed non-fail-soft full-SAEPS CG failure

```text
date: 2026-08-21
issue_id: I-027
phase: V4.5 controlled-mechanism engineering
classification: implementation failure / numerical failure
description: The first seed85 development attempt completed center work but called the legacy full SAEPS routine, which binds both the parameter-curvature and residual-score solves. It raised CGConvergenceError at 271 iterations with relative residual 3.376e-8 before any raw record was written. Controlled eta requires only the parameter RHS, and v4.1 already established that score RHS must not bind curvature validity.
evidence: retained terminal traceback from scripts/47_run_v4_5_controlled_engineering.py --seed 85 at commit 09f7a59; no output directory was created.
affected_runs: seed85 initial engineering attempt only; no scientific record or metric was accepted.
protocol_impact: No gamma, threshold, source, alpha or scientific rule changes. Before repeating seed85, the development runner must become parameter-RHS-only and fail-soft, with preregistered standard-CG then scaled-LSQR refinement candidates evaluated against the unchanged residual and explicit-reference gates.
resolution_or_status: RESOLVED. The parameter-only standard-CG then scaled-LSQR chain was committed before the accepted seed85 attempt. Seeds85--86 pass all five alpha solver gates; the score RHS is absent and nonbinding as required.
```

## I-028 — v4.5 engineering v1 center gate passes 2/3

```text
date: 2026-08-21
issue_id: I-028
phase: V4.5 controlled-mechanism engineering
classification: numerical failure
description: Under the first registered enhanced-center settings, seeds85 and 86 pass the exact center and all five alpha solver gates, while seed87 remains CHECKPOINT_INVALID. Seed87's two best enhanced starts have no negative Hessian direction but normalized objective gradients 6.146e-6 and 2.540e-6 versus the unchanged 1e-6 gate after exhausting 80 damped-GN iterations.
evidence: outputs/runs/v4_5_controlled_mechanism/engineering/seed_85 through seed_87.
affected_runs: v4.5 engineering v1 seeds85--87; denominator is 2/3 and the registered 3/3 gate fails.
protocol_impact: Held-out seeds88--89 remain forbidden. Development selection explicitly permits center-validity engineering and forbids eta/monotonicity/Spearman. Since the failure is first-order convergence without detected negative curvature, register a 160-iteration GN candidate without changing any tolerance, then evaluate all three engineering seeds in a separate revision rather than selectively repeating seed87.
resolution_or_status: RESOLVED FOR ENGINEERING. Engineering_v2 reran all three seeds under the committed 160-iteration candidate and passes 3/3 exact centers plus 15/15 alpha solver evaluations. The failed v1 denominator remains immutable. Held-out validation is still required.
```

## I-029 — v4.5 controlled confirmation fails planned-denominator center availability

```text
date: 2026-08-21
issue_id: I-029
phase: V4.5 controlled-mechanism confirmation
classification: scientific failure / benchmark numerical availability limitation
description: Untouched seeds90--99 yield 6/10 binding-valid centers. All six valid seeds are monotonic with median Spearman 1.0, but four center-invalid seeds remain planned failures. The frozen 10/10 center and 8/10 planned-monotonic conditions both fail.
evidence: outputs/runs/v4_5_controlled_confirmation and docs/evidence/v4_5_controlled_confirmation.json.
affected_runs: sole permanent v4.5 confirmation cohort seeds90--99.
protocol_impact: Scientific status is NOT_SUPPORTED. The mechanism may be claimed only conditional on a valid local state minimum; unconditional planned-denominator reproducibility is not established. No seed may be replaced or rerun.
resolution_or_status: PERMANENTLY CLOSED. Continue the v4 program with this negative evidence retained and the final paper claim narrowed.
```

## I-030 — v4.6 width-12 screening seed100 remains a high-dimensional saddle

```text
date: 2026-08-21
issue_id: I-030
phase: V4.6 two-parameter development
classification: benchmark numerical failure
description: Width-12 screening seed100 fails the exact state-local-minimum gate. All three enhanced starts pass the 1e-6 gradient gate after 160 damped-GN iterations, but retain 14--18 negative state-Hessian eigenvalues after 40 registered escape cycles.
evidence: outputs/runs/v4_6_two_parameter/engineering/seed_100.
affected_runs: v4.6 width-12 screening seed100 only.
protocol_impact: No matrix comparison was formed. Development may test a precommitted smaller-architecture fallback using only center validity, validation-only state RMSE, solver/exact availability and coupling; D and comparative errors remain forbidden selection inputs.
resolution_or_status: OPEN ARCHITECTURE DEVELOPMENT. Width8 also fails the exact center gate, although its best candidate reduces the negative-direction count to 3 and validation-only state RMSE is 0.00151. Preserve width12 and width8, then test the final preregistered width6 fallback on seed100 before activating seeds101--104.
```
