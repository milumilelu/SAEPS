# Identifiability Experiment Protocol (reliability_audit_v1)

**Protocol status: DEVELOPMENT PILOT EXECUTED / CONFIRMATION NOT AUTHORIZED.** The protocol remains a design for future confirmation; RI-0/RI-1 and the 24-case RI-2 development pilot are recorded separately. It creates a new namespace and leaves all historical SAEPS outputs and locked configurations untouched.

## Objective and estimands

For a specified equation, observation design, noise model and parameter domain, determine which physical directions are supported after neural-state adaptation, which are weak/confounded, and which additional observations improve recovery. The primary estimands are empirical false reliable-declaration risk at fixed coverage, identifiable-combination error, profile agreement, and intervention benefit. A curvature-matrix error alone is not a primary estimand.

Use (p) for physical parameters and (w) for neural state/unknown initial-condition nuisance variables. Report separately:

\[
F_{raw}=J_p^TJ_p,\quad F_\gamma=J_p^T[I-J_w(J_w^TJ_w+\gamma I)^{-1}J_w^T]J_p,
\]
\[
I_{obs}=J_y^T\Sigma^{-1}J_y,
\]

and nonlinear profile likelihoods. The latter two are independent physical references when generated without the PINN residual objective.

## Ground-truth benchmark registry

Use the dimensionless heat equation

\[
C T_t=kT_{xx},\quad x\in[0,1],\quad T(0,t)=T(1,t)=0,
\quad T(x,0)=a\sin(\pi x),
\]

with default (k=0.6,C=1.2,a=1), hence α=(k/C=0.5). Positive parameters use fixed coordinates ξ=(\log(p/p_{ref})). The default spatial points are (x=[0.2,0.4,0.7]); default multi-time points are (t=[0.02,0.08,0.2,0.4]). These are starting values to be frozen before confirmation, not post-hoc choices.

| ID | Unknowns and nuisance | Observations | Analytic truth and purpose |
|---|---|---|---|
| B1 strong scalar | (k) unknown; (C,a) known | Multi-time temperature | One well-conditioned physical direction. |
| B2 weak scalar | (k) unknown; (C,a) known | Early times (t=[10^{-5},4\times10^{-5},7\times10^{-5},10^{-4}]), same point count, controlled Gaussian noise | Structurally identifiable but practically weak; distinguish weak information from invalid optimisation. |
| B3 physical confounding | (k,C) unknown; (a) known | Multi-time temperature | Only α=(k/C) is identifiable. In log coordinates the null direction is ((1,1)), strong direction ((1,-1)). |
| B4 state/initial-amplitude compensation | (k) unknown, (C) known; (a) unknown nuisance | One nonzero-time temperature snapshot at (t^*=0.2) | (a) can compensate (k); the profiled (k) objective is flat/weak. Never provide true (a) as a training label. |
| B5 time recovery | Same unknowns as B4 | Add one distinct nondegenerate time snapshot | Joint ((a,k)) sensitivity should become rank 2; tests whether time excitation resolves compensation. |
| B6 measurement recovery | (k,C) unknown; (a) known | Temperature plus calibrated (q=-kT_x), with separate (q) scale/noise | Temperature rank 1 becomes rank 2 under stated assumptions; tests measurement-type intervention. |

Before PINN training, verify analytic Jacobian rank, singular values, null directions and profile shape for every frozen design. Replicated collocation points with normalised weights are not new independent information.

## Independent references

1. **Analytic forward/sensitivity (R1):** generate (T), (q), derivatives and Gaussian observation likelihood directly from the closed form.
2. **Independent physical solver (R2):** implement a finite-difference or spectral solver with two predeclared refinements. Require the change in observed quantities between the final two levels to be below 1% of the declared noise scale; record actual values.
3. **Profile/variable projection (R3):** scan at least 31 predeclared parameter locations; reoptimise nuisance variables and report open/closed, boundary, branch and multimodality status. Do not turn a search boundary into a confidence interval.
4. **Repeated data (R4):** independently generate observations and re-estimate parameters. The data realisation, not network initialisation, is the primary statistical unit.
5. **Bootstrap (R5, optional pilot; required for interval claims):** resample observations and refit. Initialisation ensembles are not bootstrap replicates.

## Development and confirmation split

Development is for implementation, tolerances, gamma scale, thresholds and failure codes only. Freeze code/configuration hashes, designs, seeds, budgets, gates and exclusion rules before confirmation.

* **Pilot:** B1–B4, noise ρ=1%, 3 independent `data_seed` values per benchmark and 2 independent `optimizer_seed` values per data realisation: 24 base fits. Data and optimiser RNG streams must be separate.
* **Preferred confirmation:** B1–B4 × ρ∈{1%,5%} × 20 independent data realisations × 2 initialisations = 320 base fits. B5/B6 intervention follows only after H1/H2 pass.
* **Resource-limited confirmation:** freeze in advance to the 1% condition (160 base fits) and narrow the noise claim accordingly. Zero-noise runs are analytic/numerical checks and do not enter coverage estimates.
* **Seed registries:** use separate integer lists for data, noise and network initialisation. Never replace a failed planned seed.

## Methods compared

All methods use the same checkpoint, parameter coordinates and residual/observation definition where applicable.

* RAW frozen-state GN;
* current finite-γ SAEPS-GN, with a frozen gamma path;
* VP0/SVD unregularised projection where rank and solve checks pass;
* independent physical observation FIM, with nuisance variables treated consistently with the benchmark;
* nonlinear physical profile likelihood and, separately, PINN reoptimised profiles;
* SAEPS-SO only on `PROFILE_ELIGIBLE`/SPD-valid records as a secondary ablation;
* optional data bootstrap on a declared small subset.

Optimisers such as Adam/L-BFGS, NNCG or SOAP are training tools. They are not reliability baselines and may not be selected using test truth.

## Gamma, scale and coordinate policy

Use the locked gamma path gamma = gamma_alpha * lambda_max(J_w^T J_w), with gamma_alpha in [10^{-12},10^{-10},10^{-8},10^{-6},10^{-4},10^{-2}]. If a gamma fails its numerical solve, mark it unavailable rather than removing it. Do not select a gamma per test instance using parameter error.

Report full matrices, eigenvalues, effective rank and subspaces along the path. Compare repeated/near-repeated eigenspaces by principal angles or projector distance. Report (F_\gamma-F_0) when a stable F0 exists; interpret it as damping/anchor dependence, not as a new identifiability theorem. Check physical-coordinate transformations (including log versus linear), function-preserving state reparameterisations, collocation duplication with normalised weights, loss-weight scaling and at least two widths/initialisations.

## Decision outputs and metrics

The decision layer may output `SUPPORTED_COMBINATION`, `WEAK_OR_CONFOUNDED`, `UNRESOLVED_NUMERICAL`, `UNRESOLVED_MODEL_OR_SCALE`, or `INVALID_CHECKPOINT`. A scalar η is only a relative retained-sensitivity score. Near-zero eigenvalues within the declared numerical error margin are `UNRESOLVED`.

Primary metrics:

* log-parameter error and RMSE for estimable parameters;
* identifiable-combination error (e.g. log α) and principal angle to the analytic physical subspace;
* reliable-decision coverage = accepted targets / all planned targets, retaining failures and abstentions in the denominator;
* false reliable rate among accepted targets whose absolute log error exceeds δ=log(1.10), plus errors / all planned targets; 5% and 20% tolerances are sensitivity analyses;
* risk-versus-coverage curves, so all-abstain cannot appear optimal;
* profile closure, boundary truncation, multimodality and local/profile disagreement;
* interval empirical coverage and width only when a declared statistical interval exists;
* full and marginal cost: training, diagnostics, JVP/VJP/HVP, linear iterations, profile, reference solver, bootstrap, failures, memory and wall time.

The main paired comparison is the data-realisation-level difference in false reliable risk at matched coverage between RAW and SAEPS. Report counts, planned denominator, valid denominator and uncertainty; do not treat two initialisations on one dataset as two independent physical experiments.

## Validity, exclusions and failure handling

Every planned run receives a terminal record. Keep `COMPLETED`, `INTERRUPTED`, `NOT_STARTED` and `PROTOCOL_STOP` distinct from numerical and scientific decisions. Numerical statuses are `PASS`, `FAIL` or null. At minimum classify failures as implementation, training/centre, linear or spectral solve, reference unavailable, and model/information insufficiency. A computable GN matrix at a nonstationary checkpoint is not automatically profile-eligible. SO requires its own SPD/stationarity conditions.

Do not silently retry, replace seeds, clip negative curvature, widen search bounds after seeing results, or convert a boundary profile to a finite interval. Use JSON null for unavailable values. Preserve checkpoint, config, code, environment and source hashes. Test truth may evaluate a decision but cannot tune the decision.

## Stop/go gates

* **G1 analytic sanity:** B1–B6 ranks, null directions and profiles match the known physical model. Failure stops PINN expansion.
* **G2 incremental value:** on B4, SAEPS reduces false reliable declarations relative to RAW at matched coverage without achieving this solely by universal abstention.
* **G3 stability:** conclusions do not show unexplained flips across frozen width, initialisation, coordinate and gamma audits.
* **G4 nonlinear relevance:** claims beyond local geometry require independent profile or repeated-data agreement.
* **G5 paper value:** at least one of fewer false declarations, useful combinations, intervention benefit, calibrated intervals, or a clear low-cost diagnostic advantage is demonstrated with independent data.

If a gate fails, record `PROTOCOL_STOP` and retain all runs. A scientific failure narrows the paper; it is not an engineering failure. Do not launch a large campaign while G1 or the pilot availability threshold (at least 5/6 pilot fits per benchmark fit-qualified, subject to the frozen rule) is unmet.

## Required run-manifest minimum

Each manifest must include protocol/code/config/source hashes; benchmark; data/noise/initialisation seeds; physical and nuisance parameters; observation type and covariance; coordinate and residual weights; gamma and scale definition; execution/numerical/fit/profile/decision statuses; failure reason; raw paths for (F_{raw},F_\gamma,I_{obs}), profiles and estimates; rank/tolerance/subspace errors; parameter and combination errors; training/diagnostic/reference time; memory; JVP/VJP/HVP and solver iterations; checkpoint hash. All aggregates must be reproducible from these manifests, with failed and not-started denominators visible.


