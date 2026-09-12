# Q2 Paper Strategy: Reliability-Aware Identifiability for Inverse PINNs

**Status: PROPOSED / NOT EXECUTED.** This is a decision and writing plan, not evidence that a paper-level contribution has been established. Journal quartiles and scopes must be checked again at submission.

## Recommended positioning

The strongest candidate is a constrained paper on **reliability-aware identifiable subspaces under neural-state adaptation**. The central message would be:

> A finite-damping state-eliminated curvature is a local, checkpoint-dependent diagnostic. Its reliability must be tested against independent observation information and nonlinear profiles; when evidence is insufficient, the method should report a combination or abstain and can be evaluated for observation-design value.

This framing makes the positive and negative cases scientifically useful. It does not claim global identifiability, universal thresholds, posterior uncertainty, causal effects, or reliability for all inverse PINNs.

Potential titles, to be selected only after confirmation, are:

* *Reliability-Aware Identifiability Diagnostics for Inverse Physics-Informed Neural Networks*;
* *Identifiable Parameter Subspaces in Inverse PINNs under Neural-State Adaptation*;
* *Diagnosing and Resolving Parameter Non-Identifiability in Inverse PINNs through State-Eliminated Sensitivity Analysis* (only if B5/B6 intervention succeeds).

## Contribution decision tree

| Candidate contribution | Minimum evidence required | If evidence fails |
|---|---|---|
| SAEPS-GN reliability diagnostic | Lower false reliable risk than RAW on independent B4-like data at matched coverage; analytic B1–B6 sanity; stable gamma/representation audit | Narrow to a local numerical diagnostic; remove reliability generalisation. |
| Identifiable-subspace output | Correctly reports (k/C), refuses separate (k,C), and recovers B5/B6 subspaces with independent profiles | Report only a failure-analysis/benchmark paper; do not market parameter-wise scores. |
| SAEPS-SO | Independent gain in classification, profile agreement, calibration, or cost/accuracy, on eligible centres | Keep as secondary ablation; do not make it the method headline. |
| Low-cost certification | Validated error/risk relation against independent references and complete cost ledger | Remove “certified” and confidence language. |
| Observation design | Same-budget new measurements reduce actual error/profile width after re-estimation, not only eigenvalue | Omit intervention claim; retain diagnostic result if G1–G3 pass. |
| Calibrated intervals | Repeated independent datasets with explicit likelihood/interval construction and empirical coverage | Report scores/decision states, not confidence intervals. |

## Claims currently supported by historical evidence

The existing record supports only bounded statements:

1. The implementation computes a finite-γ state-eliminated residual-space GN curvature and has an explicit/matrix-free numerical verification history.
2. On the declared valid V5 Burgers and Allen–Cahn checkpoints, SAEPS was closer than frozen-state GN to the declared finite-damping local reference under paired comparisons (Burgers: 12/15 planned, 12 valid; Allen–Cahn: 9/10 planned, 9 valid).
3. Matrix-free state elimination provides a practical cost path, including cost-only measurements up to 100001 state parameters.
4. Historical nonlinear-profile, two-parameter, SO-independent-centre and low-cost-certification limitations are material and must be reported.

These claims do **not** establish physical parameter identifiability, uncertainty calibration, global uniqueness, nonlinear-profile equivalence, or broad reliability.

## Claims not supported and prohibited wording

Do not write “SAEPS proves parameter reliability,” “SAEPS estimates posterior covariance,” “all inverse-PINN parameters are identifiable,” “finite-γ curvature is measurement information,” or “SO is generally superior.” Do not turn a local eigenvalue into a confidence interval, or a failed stationarity gate into a physical non-identifiability result. A report of (k/C) as identifiable must be accompanied by the statement that (k) and (C) are not separately identified under temperature-only observations in B3.

## Required evidence package before submission

The paper should not enter full drafting until the new namespace contains:

* immutable analytic B1–B6 rank/profile checks;
* independent analytic and discretised physical references;
* a pilot with all planned fit and failure states;
* frozen development/confirmation hashes and seed registries;
* RAW, SAEPS-GN, VP0/SVD, physical FIM and nonlinear profile baselines;
* matched-coverage risk/coverage results on independent data realisations;
* subspace/combination errors and gamma/coordinate/architecture stability;
* intervention results only if the diagnosis selected observations without seeing their new measurements;
* raw-to-aggregate lineage, cost accounting and retained failures.

The preferred confirmation is 320 base fits (B1–B4, two noise levels, 20 data realisations, two initialisations), or a pre-frozen 160-fit 1% noise version with correspondingly narrower claims. The statistical unit is the data realisation. A large number of network initialisations on one dataset is not equivalent evidence.

## Proposed figures and tables

1. **Analytic counterexamples:** flat profile versus finite-γ curvature; state-coordinate and global-alias checks.
2. **Ground-truth geometry:** B1/B2 profiles and information scales; B3 (k/C) subspace; B4 compensation and B5 recovery.
3. **Measurement intervention:** B3 temperature-only versus temperature+flux, with profiles and empirical recovery at equal cost.
4. **Gamma and representation audit:** eigenvalue paths, effective rank and principal-angle stability; mark unresolved regions.
5. **Risk/coverage:** RAW versus SAEPS decision curves with all-abstain and denominator annotations.
6. **Cost/availability:** marginal and end-to-end costs, profile cost, solver counts and every failure category.

Tables should include the benchmark registry, competitor definitions, planned/valid/failed/not-started denominators, combination errors, profile status, exact decision reasons, and a machine-readable claim ledger. Every paper-facing scalar must be regenerated from raw manifests.

## Novelty and reviewer-risk assessment

**Risk: “This is just FIM/Schur/variable projection.”** Explain the precise finite-damping residual-space object, show the flat-profile counterexample, and validate against an independent physical FIM/profile rather than claiming elimination itself is new.

**Risk: “Identifiability was already studied in PINNs.”** Cite Kharazmi et al. and recent FIM-guided PINNs; state that the contribution is the reliability audit, neural-state interference analysis, combination-aware abstention and intervention test, if those pass.

**Risk: “The network or optimiser caused the result.”** Separate training validity from identifiability, report centre failures, use common checkpoints and perform width/initialisation/coordinate checks. Do not hide invalid centres.

**Risk: “Finite damping injects prior information.”** Report the gamma path and (F_\gamma-F_0), disclose the state metric and residual weights, and avoid calling the result observation information without a likelihood reference.

**Risk: “Noisy intervals are uncalibrated.”** Use repeated data and explicit interval construction; otherwise call outputs scores or decision states and omit confidence language.

**Risk: “Observation design only improved a matrix.”** Require new noisy measurements, re-estimation and profile contraction at matched cost. If that fails, remove the intervention headline.

**Risk: “Q2 novelty is overstated.”** Make the negative B3/B4 cases central, include strong baselines and retain the possibility of a narrower numerical-analysis paper. A clean negative result is preferable to an unsupported universal claim.

## Candidate venues

Subject to current scope and quartile verification, plausible venues are *Journal of Computational Physics*, *Inverse Problems*, *SIAM Journal on Scientific Computing*, *Computer Methods in Applied Mechanics and Engineering*, and *Machine Learning: Science and Technology*. A narrower numerical-analysis outcome may fit *SIAM Journal on Matrix Analysis and Applications* or *Numerical Algorithms*; a reliability/UQ outcome may fit *Computer Methods and Programs in Biomedicine* only when the application and calibration evidence genuinely match its scope. Do not select a venue by nominal quartile before the contribution and evidence are fixed.

## Go / revise / stop recommendation

Proceed to a full Q2 submission only if G1–G5 in the protocol are met and the claim ledger has no unsupported headline claim. Proceed with limited claims if the method correctly exposes combinations and failures but intervention or calibration is absent. Revise the method if SAEPS adds no decision value beyond physical FIM/profile or if decisions flip under ordinary representation changes. Stop broad reliability expansion if it can avoid errors only by universal abstention, if independent references contradict its decisions, or if valid centres remain too scarce for the planned denominator.
