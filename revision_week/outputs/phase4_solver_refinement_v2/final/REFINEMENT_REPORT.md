# Phase 4 Solver Refinement — Round 1 Report

Development-only; never confirmation evidence. Authority: the Phase 4 execution rules; the frozen protocol is recorded with its SHA256 in this directory.

**Corrections (independent review PHASE4_REVIEW_20260910).** This is the corrected protocol-v3 round. The alpha=1e-10 selection, the raw-local-minimum statements and the full-closure claim of the earlier v1/v2 round are withdrawn; finding-by-finding verification and actions are in REVIEW_CORRECTIONS_20260910.md, and acceptance is evidence-based in VALIDATION.json. No earlier result file was rewritten.

## 1. Scope, denominators and isolation

- Planned denominator: 12 positions (6 fixed centers × routes raw/proximal). No center replaced; failed and not-started positions are retained in REFINEMENT_FAILURES.json; smoke runs live outside this denominator under preflight/smoke.
- Historical files changed during the phase: 0 (acceptance requires 0); full audit in HISTORICAL_HASH_AUDIT.json.
- Environment lock recorded in preflight/environment.json; solver: scipy.optimize.least_squares method=trf x_scale='jac' loss='linear' ftol/xtol/gtol=1e-14 chunk_nfev=50.
- Route P gamma rule: gamma_i = alpha * lambda_max(J_theta(theta0)^T J_theta(theta0)) evaluated once at the archived theta0, fixed lambda0, before any Route P solve — frozen per center in gamma_computation.json before its solve.

## 2. Task table

| center | route | terminal | binding g | raw loss before | raw loss after | dRel | theta disp (rel) | K8 | K10 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| burgers_1006 | raw | RESOURCE_LIMIT | 1.418e-04 | 5.620903e+00 | 9.512853e-01 | -8.308e-01 | 9.940e-01 | N | N | wall_budget_exhausted |
| burgers_1006 | proximal | PASS | 2.332e-11 | 5.620903e+00 | 3.635467e+00 | -3.532e-01 | 4.896e-01 | Y | Y | PASS |
| burgers_1007 | raw | CURVATURE_STABILITY_UNRESOLVED | 6.355e-08 | 2.727924e+00 | 9.170220e-01 | -6.638e-01 | 8.888e-01 | Y | N | 1e-10 polish state not reached within the frozen stage budget |
| burgers_1007 | proximal | CURVATURE_STABILITY_UNRESOLVED | 7.489e-12 | 2.727924e+00 | 9.971419e-01 | -6.345e-01 | 3.548e-01 | Y | Y | 1e-10 polish state not reached within the frozen stage budget |
| allen_cahn_1016 | raw | CURVATURE_UNSTABLE | 2.022e-11 | 3.493114e-01 | 2.898544e-01 | -1.702e-01 | 9.994e-01 | Y | Y | K10 vs K8 relative drift exceeds 0.05 |
| allen_cahn_1016 | proximal | PASS | 1.669e-12 | 3.493114e-01 | 3.263789e-01 | -6.565e-02 | 1.836e-01 | Y | Y | PASS |
| allen_cahn_1017 | raw | CURVATURE_STABILITY_UNRESOLVED | 1.576e-07 | 5.120079e-01 | 2.761374e-01 | -4.607e-01 | 9.417e-01 | Y | N | 1e-10 polish state not reached within the frozen stage budget |
| allen_cahn_1017 | proximal | CURVATURE_STABILITY_UNRESOLVED | 1.072e-11 | 5.120079e-01 | 3.398766e-01 | -3.362e-01 | 3.934e-01 | Y | Y | 1e-10 polish state not reached within the frozen stage budget |
| multi_1026 | raw | RESOURCE_LIMIT | 7.205e-06 | 2.100470e-01 | 1.338106e-01 | -3.629e-01 | 9.762e-01 | N | N | wall_budget_exhausted |
| multi_1026 | proximal | CURVATURE_STABILITY_UNRESOLVED | 9.348e-13 | 2.100470e-01 | 1.839160e-01 | -1.244e-01 | 1.167e-01 | Y | Y | 1e-10 polish state not reached within the frozen stage budget |
| multi_1027 | raw | RESOURCE_LIMIT | 3.564e-06 | 3.378628e-02 | 9.140170e-03 | -7.295e-01 | 9.764e-01 | N | N | wall_budget_exhausted |
| multi_1027 | proximal | CURVATURE_STABILITY_UNRESOLVED | 6.441e-13 | 3.378628e-02 | 2.091768e-02 | -3.809e-01 | 2.058e-01 | Y | Y | 1e-10 polish state not reached within the frozen stage budget |

## 3. Answers to the required report questions

1. Route R versus the past L-BFGS / full-Newton reachability: 0/6 centers reached REFERENCE_CAPABLE within the frozen 600s task wall and 24000 nfev pool, while the Phase 3 archived-state continuation (route A, 1800s) reached the binding 1e-8 gate on 0 of these 6 centers and routes B/C all exhausted their budgets. Gradient trajectories are in tasks/*/trajectory.jsonl.
2. Route R failure attribution by terminal status: {'RESOURCE_LIMIT': ['burgers_1006', 'multi_1026', 'multi_1027'], 'CURVATURE_STABILITY_UNRESOLVED': ['burgers_1007', 'allen_cahn_1017'], 'CURVATURE_UNSTABLE': ['allen_cahn_1016']}; scipy stop messages are in tasks/*/claim.json (stages.K8.scipy_stop) and Newton-state displacement diagnostics (eta_state, eta_E) in diagnostics_after.json.
3. Route P at nominal alpha: 2/6 centers REFERENCE_CAPABLE (Route R: 0/6).
4. Route P physical-fit preservation: raw-total relative change within [-6.345e-01, -6.565e-02] against the frozen +5% gate; worst training-block relative increase 2.743e-01 against the frozen +10% gate; validation metric is UNAVAILABLE and was never fabricated.
5. Alpha requirement: this round ran the nominal alpha=1e-8 (gamma_i = alpha * lambda_max(J_theta(theta0)^T J_theta(theta0)) evaluated once at the archived theta0, fixed lambda0, before any Route P solve) with a binding-gradient reach on 6/6 centres. Any alpha grid result appears in GRID_DECISION.json; the earlier 1e-10 selection was withdrawn because two of its supporting centre pairs were not separable, and selection is made only by the frozen rule over admissible evidence.
6. Raw versus damped/proximal stability conclusions per state: [('burgers_1006', 'spd_unresolved', 'numerically_SPD'), ('burgers_1006', 'not_SPD', 'numerically_SPD'), ('burgers_1007', 'spd_unresolved', 'numerically_SPD'), ('burgers_1007', 'numerically_SPD', 'numerically_SPD'), ('allen_cahn_1016', 'spd_unresolved', 'numerically_SPD'), ('allen_cahn_1016', 'not_SPD', 'numerically_SPD'), ('allen_cahn_1017', 'spd_unresolved', 'numerically_SPD'), ('allen_cahn_1017', 'not_SPD', 'numerically_SPD'), ('multi_1026', 'not_SPD', 'numerically_SPD'), ('multi_1026', 'not_SPD', 'numerically_SPD'), ('multi_1027', 'not_SPD', 'numerically_SPD'), ('multi_1027', 'not_SPD', 'numerically_SPD')]. A task is REFERENCE_CAPABLE only when the route stability matrix (A_fd for R, H_prox for P) is resolvably positive. RAW_LOCAL_MINIMUM additionally requires raw objective stationarity, so a proximal stationary point is never presented as a raw local minimum; raw Hessian positive definiteness is a separate diagnostic (raw_hessian_spd).
7. Curvature stability is evaluated per task in curvature_K8.json and curvature_K10.json, and only over an admissible pair: the two states must differ and both must come from genuine continued refinement. A pair that is not separable at the declared resolution is UNRESOLVED, never STABLE. The joint Hessian is the frozen binding metric (the reduced curvature F_star is a non-binding diagnostic, so joint-K stability is not claimed to imply reduced-parameter curvature stability).
8. The 1e-12 polish state was reached on 3/12 positions; it is a non-binding diagnostic, it never drives the verdict, and the binding verdict is taken at the deepest admissible milestone (K10 preferred).
9. Network parameter displacement: relative ||theta_final - theta0|| / max(||theta0||, 1) per task in the table above; theta displacement and the proximal term are diagnostics only.
10. Whether a solver-only holdout is worthwhile is decided mechanically by REFINEMENT_DECISION.json (branch A extends, branch B starts the alpha grid, branch D stops and turns to mechanism diagnostics).
11. A new independent SO confirmation design is permitted only after the solver reachability gate passes; this round performs no SO/GN comparison and claims nothing about SO superiority.

## 4. Cost ledger (measured only)

- Aggregate worker wall seconds: 1648.8; aggregate nfev: 49149; aggregate njev: 37666.
- Per-task wall seconds, nfev/njev and sampled peak RSS are in REFINEMENT_COST_LEDGER.json.

## 5. Paper-facing boundary

This phase must not be used to claim: SO independently confirmed; SO generally superior; proximal method improves parameter recovery; global identifiability established. If Route R succeeds, the paper may say that part of the earlier reachability problem came from generic optimizers not exploiting the residual sum-of-squares structure. If Route P succeeds where Route R fails, the analysis object has changed from fully-free raw state re-optimization to a fixed-reference local reduced geometry, and the paper must state that change explicitly.

## 6. Validation

- Unified Objective recomputation at theta_final within 1e-9 relative tolerance: True.
- Repository-level acceptance via scripts/validate_repository.py is recorded in VALIDATION.json context; a scientific FAIL never becomes an engineering failure.
