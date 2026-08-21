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

## D-011 — Authorize the one-shot v3.6 execution without changing its lock

```text
date: 2026-08-20
decision_id: D-011
decision: Authorize exactly one execution of locked seeds 30--44 after the clean pre-confirmation audit passes; do not authorize any rerun or protocol modification.
reason: The user supplied SAEPS Master Research Program v4.0 as the task book and the active goal explicitly requires execution, adjudication and permanent freezing of v3.6 before any later research branch.
development_evidence: docs/evidence/PRE_CONFIRMATION_AUDIT.json status PASSED; no v3.6 output existed at authorization.
affected_configs: configs/v3_6/EXECUTION_AUTHORIZATION.json only. configs/v3_6/locked_scalar_confirmation.yaml remains byte-identical to lock commit 4eb28f5.
authorizing_protocol: SAEPS Master Research Program v4.0 Phase A and docs/v3_6/LOCKED_PROTOCOL.md.
```

## D-012 — Permanently close v3.6 as NOT_SUPPORTED with implementation failure

```text
date: 2026-08-20
decision_id: D-012
decision: Preserve the sole v3.6 cohort unchanged, adjudicate NOT_SUPPORTED from 0/15 valid pairs, and permanently prohibit any v3.6 rerun or corrected reaggregation.
reason: All planned seeds have terminal results, but an implementation defect bound the excluded score RHS into the curvature-only direct-reference gate. Fourteen seeds were therefore marked SOLVER_FAILURE and seed37 was center-invalid. Required comparative quantities were not retained for failed seeds.
development_evidence: Not development; immutable confirmation evidence in docs/evidence/v3_6_confirmation.json and raw manifest hash 3c7061a963710d28579661ae5792e9e55642119a6777e7d04097d5c16b544aa9.
affected_configs: No locked config changed. v3.6 is permanently closed; future work must be a new POST_CONFIRMATION_DEVELOPMENT version with new seeds.
authorizing_protocol: SAEPS Master Research Program v4.0 Branch B-minus and docs/v3_6/LOCKED_PROTOCOL.md.
```

## D-013 — Open v4.1 post-confirmation execution-semantic development

```text
date: 2026-08-20
decision_id: D-013
decision: Repair only execution semantics on development seeds 45--49, freeze executable code/config/tests, then evaluate held-out development seeds 50--54.
reason: V3.6 failed because an excluded score RHS contaminated a curvature-only gate. Read-only evidence shows the intended curvature-specific reference and solver criteria passed 14/14 center-valid runs, so changing SAEPS, center, gamma, solver, gold standard or D would be unjustified.
development_evidence: docs/evidence/v3_6_confirmation.json and docs/v4_1_POST_CONFIRMATION_DEVELOPMENT.md.
affected_configs: configs/v4_1/post_confirmation_development.yaml only; v3.6 remains immutable and closed.
authorizing_protocol: docs/protocol_amendments/AMENDMENT_012_V4_1_EXECUTION_SEMANTIC_REPAIR.md.
```

## D-014 — Freeze the v4.1 executable before held-out development

```text
date: 2026-08-20
decision_id: D-014
decision: Freeze v4.1 config, runner, separated numerical references, validator, semantic gate graph and regression test at commit 09a31c6 before seeds 50--54.
reason: Engineering seeds 45--49 produced 4/5 binding-valid chains; all four center-valid seeds demonstrated the required score-fail/curvature-pass separation and complete core-quantity recording. Seed49 center failure is retained without threshold change.
development_evidence: docs/evidence/v4_1_engineering_integration_validation.json.
affected_configs: configs/v4_1/EXECUTABLE_FREEZE.json; confirmation seeds 55--69 remain inactive.
authorizing_protocol: docs/v4_1_POST_CONFIRMATION_DEVELOPMENT.md sections 4--5 and Amendment 012.
```

## D-015 — Accept v4.1 held-out execution-semantic repair

```text
date: 2026-08-20
decision_id: D-015
decision: Accept v4.1 as PASSED development engineering and permit creation, but not execution, of a separate v4.2 confirmation lock on seeds 55--69.
reason: Under the frozen executable, held-out seeds 50--54 pass center, parameter-only reference, curvature solver, exact gold and finite-primary nodes 5/5. Score diagnostics fail 5/5 yet remain nonbinding as preregistered, and all computable quantities are retained.
development_evidence: docs/evidence/v4_1_heldout_development_validation.json and docs/evidence/V4_1_ACCEPTANCE.md.
affected_configs: Future configs/v4_2 lock only; v3.6 and v4.1 outputs remain immutable.
authorizing_protocol: docs/v4_2_CORRECTED_CONFIRMATION.md section 1.
```

## D-016 — Create the v4.2 corrected untouched confirmation lock

```text
date: 2026-08-20
decision_id: D-016
decision: Lock a new one-shot scalar-curvature confirmation on untouched seeds 55--69 using the v4.1 repaired executable and unchanged v3.6 scientific definitions.
reason: V4.1 frozen held-out seeds 50--54 passed the complete binding chain 5/5 and demonstrated that score failure is nonbinding. A new cohort is required because v3.6 is permanently closed.
development_evidence: docs/evidence/V4_1_ACCEPTANCE.md and docs/evidence/v4_1_heldout_development_validation.json.
affected_configs: configs/v4_2/locked_corrected_confirmation.yaml; v3.6 and v4.1 remain unchanged.
authorizing_protocol: docs/v4_2_CORRECTED_CONFIRMATION.md and Amendment 013. Execution still requires clean preflight and a separate authorization record.
```

## D-017 — Authorize one-shot v4.2 execution after full preflight

```text
date: 2026-08-20
decision_id: D-017
decision: Authorize exactly one execution of untouched seeds 55--69 under the immutable v4.2 protocol and executable lock.
reason: V4.1 held-out full-chain gate passed 5/5 and the v4.2 preflight passed config, executable, source, seed, zero-prior-run, test and v3.6-protection checks.
development_evidence: docs/evidence/V4_2_PRE_CONFIRMATION_AUDIT.json and docs/evidence/V4_1_ACCEPTANCE.md.
affected_configs: configs/v4_2/EXECUTION_AUTHORIZATION.json only; locked config and executable bytes remain unchanged.
authorizing_protocol: user v4.1 task and docs/v4_2_CORRECTED_CONFIRMATION.md sections 3--4.
```

## D-018 — Permanently close v4.2 as SUPPORTED

```text
date: 2026-08-20
decision_id: D-018
decision: Adjudicate v4.2 SUPPORTED and permanently close seeds 55--69 with no rerun or result mutation.
reason: Twelve of fifteen planned seeds are valid strict wins, median D is positive, and the exact one-sided sign-test p-value is 0.000244140625. All four locked primary conditions pass. Three center-invalid seeds remain planned non-wins.
development_evidence: Not development; untouched confirmation evidence in docs/evidence/v4_2_confirmation.json and outputs/runs/v4_2_corrected_confirmation.
affected_configs: No locked config or executable changed. A reporting-only schema adapter is disclosed in I-024; independent raw-to-aggregate validation passes.
authorizing_protocol: docs/v4_2_CORRECTED_CONFIRMATION.md and Amendment 013.
```

## D-019 — Open the v4.3 supported research branch

```text
date: 2026-08-21
decision_id: D-019
decision: Preserve all historical protocols and open the v4.0 SUPPORTED branch, beginning with fixed Allen-Cahn external-replication development seeds 70--74; reserve but do not activate later confirmation and extension seeds.
reason: V4.2 passed all four frozen primary conditions on Burgers, but this result does not establish cross-PDE, nonlinear-profile, multi-parameter or practical-scale validity required by the master research program.
development_evidence: No new development result. Decision is based only on permanently frozen v4.2 evidence and the four user-supplied task books.
affected_configs: Future configs/v4_3 development files only. V2, v3.6, v4.1 and v4.2 locks/results remain immutable.
authorizing_protocol: Amendment 014 and docs/v4_3_SUPPORTED_BRANCH_EXECUTION_CONTRACT.md.
```

## D-020 — Select width 8 for Allen--Cahn engineering validation

```text
date: 2026-08-21
decision_id: D-020
decision: Select hidden width 8 as the Allen-Cahn engineering candidate and run it on engineering seeds 71--72 before any held-out freeze.
reason: Under the preregistered fallback order 16 -> 12 -> 8, width16 and width12 failed the unchanged exact center gate on screening seed70. Width8 passed the exact center gate and its validation-only state RMSE 0.02050 passed the preregistered 0.15 feasibility threshold. Its complete numerical chain also passed.
development_evidence: outputs/runs/v4_3_allen_cahn_development/seed_70; engineering/seed_70; engineering_v2/seed_70; architecture_w12/seed_70; architecture_w8/seed_70.
forbidden_evidence_not_used: D, E_SAEPS, E_raw, eta, I_GN and profile curvature were not read or used for architecture selection.
affected_configs: configs/v4_3/allen_cahn_development.yaml selected_width only; confirmation remains unauthorized.
authorizing_protocol: docs/v4_3_SUPPORTED_BRANCH_EXECUTION_CONTRACT.md section 4 and Amendment 014.
```

## D-021 — Accept Allen--Cahn engineering and prepare held-out freeze

```text
date: 2026-08-21
decision_id: D-021
decision: Accept width-8 Allen-Cahn engineering on seeds 70--72 and permit creation of an executable freeze for held-out development seeds 73--74; confirmation remains unauthorized.
reason: All three selected-width records pass center, parameter-only reference, curvature solver, exact finite-gamma gold, finite-primary and directional-HVP agreement nodes. The actual runner-to-validator schema integration passes. Score failure is correctly nonbinding. The nonlinear-profile bridge passes only 1/3 and remains an explicit nonbinding limitation.
development_evidence: docs/evidence/v4_3_allen_engineering_validation.json and docs/evidence/V4_3_ALLEN_ENGINEERING.md.
forbidden_evidence_not_used: Comparative D/E/eta values were excluded from validation and decision inputs.
affected_configs: Future configs/v4_3/ALLEN_EXECUTABLE_FREEZE.json only; seeds 73--74 remain inactive until the freeze is committed.
authorizing_protocol: docs/v4_3_SUPPORTED_BRANCH_EXECUTION_CONTRACT.md section 4.3.
```

## D-022 — Freeze Allen--Cahn executable for held-out development

```text
date: 2026-08-21
decision_id: D-022
decision: Freeze the width-8 Allen-Cahn development config, runner, center engine, directional indicator, validator, tests and semantic gate graph at commit 6490977, then activate held-out development seeds 73--74 only.
reason: Engineering seeds 70--72 pass the complete binding curvature chain 3/3 and the real raw-schema integration test passes. Profile bridge instability remains nonbinding and is frozen rather than tuned away.
development_evidence: docs/evidence/v4_3_allen_engineering_validation.json.
affected_configs: configs/v4_3/ALLEN_EXECUTABLE_FREEZE.json. Confirmation seeds 75--84 remain inactive and unauthorized.
authorizing_protocol: docs/v4_3_SUPPORTED_BRANCH_EXECUTION_CONTRACT.md section 4.3 and Amendment 014.
```

## D-023 — Accept frozen Allen--Cahn held-out development

```text
date: 2026-08-21
decision_id: D-023
decision: Accept held-out development seeds 73--74 under the frozen width-8 executable and permit drafting, but not execution, of a separate untouched confirmation lock for seeds 75--84.
reason: Both held-out seeds pass every binding curvature node and directional-HVP agreement. Score failures remain nonbinding. Gamma-matched nonlinear profiles pass 1/2 and remain a separately reported unstable bridge. Frozen file hashes and raw record hashes validate.
development_evidence: docs/evidence/v4_3_allen_heldout_validation.json and docs/evidence/V4_3_ALLEN_HELDOUT.md.
forbidden_evidence_not_used: No D, E or eta quantity entered held-out acceptance.
affected_configs: Future Allen-Cahn confirmation lock only; confirmation seeds remain inactive pending protocol/executable lock, tests and clean preflight.
authorizing_protocol: docs/v4_3_SUPPORTED_BRANCH_EXECUTION_CONTRACT.md sections 4.3 and 5.
```

## D-024 — Lock v4.4 Allen--Cahn external confirmation

```text
date: 2026-08-21
decision_id: D-024
decision: Lock untouched Allen-Cahn seeds 75--84, width-8 executable, exact finite-gamma primary D endpoint, 8/10 planned-win rule, exact sign test, nonbinding profile bridge and frozen indicator; do not yet authorize execution.
reason: Frozen held-out development passes the binding curvature chain 2/2 and raw-schema integration is established. The 80% planned-denominator rule matches the v4.2 confirmation proportion and was specified before any seed 75--84 was run or inspected.
development_evidence: docs/evidence/v4_3_allen_heldout_validation.json.
affected_configs: configs/v4_4/locked_allen_cahn_confirmation.yaml and LOCK_RECORD.json only. All earlier results remain immutable.
authorizing_protocol: Amendment 015 and docs/v4_4_ALLEN_CONFIRMATION_PROTOCOL.md.
```

## D-025 — Authorize one-shot v4.4 Allen--Cahn execution

```text
date: 2026-08-21
decision_id: D-025
decision: Authorize exactly one execution of locked Allen-Cahn seeds 75--84; prohibit rerun and protocol mutation.
reason: The clean preflight passed locked config, exact seeds, source/executable hashes, zero-prior-run, real raw-schema compatibility, 64 tests, frozen held-out validation and permanent v3.6/v4.2 protection.
development_evidence: docs/evidence/V4_4_PRE_CONFIRMATION_AUDIT.json; no seed 75--84 output existed at authorization.
affected_configs: configs/v4_4/EXECUTION_AUTHORIZATION.json only. Locked config and executable remain byte-identical.
authorizing_protocol: Amendment 015 and docs/v4_4_ALLEN_CONFIRMATION_PROTOCOL.md.
```

## D-026 — Adjudicate v4.4 SUPPORTED and permanently close seeds 75--84

```text
date: 2026-08-21
decision_id: D-026
decision: Adjudicate the untouched Allen--Cahn v4.4 comparative curvature claim SUPPORTED and permanently close seeds 75--84 with no rerun or result mutation.
reason: Nine of ten planned seeds are valid strict wins, median D is 20.0064951395, and the exact one-sided sign-test p-value is 0.001953125. All four locked primary conditions pass. Seed81 is center-invalid and remains a planned non-win.
secondary_limitations: E_SAEPS median is 27.8567% with 0/9 within 5%; the gamma-matched nonlinear profile bridge passes only 1/10. Therefore exact-surrogate accuracy and nonlinear-profile agreement are not established.
execution_deviation: I-026 records a post-summary directory-path packaging failure. Recovery did not rerun any seed or change any scientific object, and independent frozen-aggregate reproduction passes.
development_evidence: Not development; untouched confirmation evidence in docs/evidence/v4_4_allen_confirmation.json and outputs/runs/v4_4_allen_cahn_confirmation.
affected_configs: No locked config or executable changed. V3.6 and v4.2 remain permanently closed and unchanged.
authorizing_protocol: Amendment 015 and docs/v4_4_ALLEN_CONFIRMATION_PROTOCOL.md.
```

## D-027 — Open v4.5 controlled-mechanism development

```text
date: 2026-08-21
decision_id: D-027
decision: Activate only controlled-mechanism engineering seeds 85--87; reserve held-out seeds 88--89 and untouched confirmation seeds 90--99 behind their own gates.
reason: V4.4 completed the preceding ordered external-replication node. Historical P2 failed because only 5/10 centers were valid, while every valid seed was monotonic. Fresh development may engineer center availability but may not change the controlled scientific objects or select using eta/monotonicity/Spearman.
development_evidence: No v4.5 numerical result exists at this decision.
affected_configs: configs/v4_5/controlled_mechanism_development.yaml only; the P2 lock and all historical outputs remain immutable.
authorizing_protocol: Amendment 016 and docs/v4_5_CONTROLLED_MECHANISM_DEVELOPMENT.md.
```

## D-028 — Accept v4.5 engineering_v2 for executable freeze

```text
date: 2026-08-21
decision_id: D-028
decision: Accept engineering_v2 seeds85--87 and permit creation of an executable freeze for held-out development seeds88--89; confirmation remains inactive.
reason: All three exact state-local-minimum gates and all fifteen parameter-curvature solver/explicit-agreement evaluations pass. The v1 2/3 center denominator is retained. The v2 iteration candidate was selected solely from first-order center convergence without negative curvature.
development_evidence: docs/evidence/v4_5_controlled_engineering.json and immutable raw records under outputs/runs/v4_5_controlled_mechanism.
forbidden_evidence_not_used: Eta, monotonicity, Spearman correlation and figure appearance were excluded from validation and decision inputs.
affected_configs: Future configs/v4_5/CONTROLLED_EXECUTABLE_FREEZE.json only; seeds88--99 remain inactive until their respective gates.
authorizing_protocol: Amendment 016 and docs/v4_5_CONTROLLED_MECHANISM_DEVELOPMENT.md.
```
