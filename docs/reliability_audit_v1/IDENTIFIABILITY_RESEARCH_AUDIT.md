# Identifiability Research Audit (SAEPS reliability_audit_v1)

**Status: AUDIT ARTIFACT; RI-2 development pilot executed separately; confirmation was not authorized.**

This audit is a new, read-only interpretation layer. It does not replace or rewrite historical SAEPS records. The supplied review package was audited on 2026-09-12 against repository commit `71fd3b025824f59146851f2ebfb5068e8cc9addb`. Its package manifest SHA-256 is `27a7b81e3611a7cce635540f3663584120526c3e0c22464469e4be20c6d7232e`; the two source reports are `6bd8ff2082aa5096556907c779a3ee044cc4d2686252ee38dcbe58d8d41f4e56` and `8404be75996163a667579d92a7ba13ce108a2fdf1847da824a51d8b309852e3b`. Its seven independent NumPy algebra/analytic checks passed. The audit document itself is read-only; subsequent RI-2 development pilots, analytic profiles and the independent physical refinement are recorded as separate versioned artifacts. No confirmation experiment has been authorized.

## Scope and provenance

The review package records the following immutable context:

| Item | Evidence and interpretation |
|---|---|
| Current implementation | `src/saeps/core.py` exposes raw curvature, explicit Tikhonov state elimination, matrix-free CG elimination, retained sensitivity and `eta`. The state solve uses (J_w^T J_w+gamma I). |
| Mathematical object | (F_{raw}=J_p^TJ_p), (F_\gamma=J_p^T[I-J_w(J_w^TJ_w+\gamma I)^{-1}J_w^T]J_p). This is a checkpoint-dependent, residual-space, finite-damping local GN quantity. |
| Historical scalar evidence | V5 Burgers: 12/15 valid and 12/12 paired comparisons favorable; Allen–Cahn: 9/10 valid and 9/9 favorable. These support a bounded comparison to the declared finite-damping reference. |
| Historical limitations | V5 nonlinear profile bridge: 1/5 `PROFILE_VALID`; two-parameter confirmation: 8/10 valid, below its planned availability requirement; SO independent Phase-2 roots: 0/30 valid. These are retained negative/limited evidence, not discarded samples. |
| Independent checks in package | Seven checks passed, including finite-damping positive curvature for a flat unanchored profile, state-coordinate dependence, rank-one physical confounding (k/C), state-amplitude compensation, normalized collocation duplication, and a global (p^2) alias. They are analytic checks, not PINN results. |
| New reliability namespace | RI-0/RI-1 references and the RI-2 development pilot are present under `experiments/reliability_audit_v1/`, `src/saeps/reliability_audit_v1/` and `outputs/reliability_audit_v1/`; confirmation remains unauthorized after the B1 availability gate failed. |

The old `outputs/runs/`, `outputs/posthoc/`, `docs/evidence/`, `paper_artifacts/`, locked configurations, and revision-week records remain historical evidence. Any later implementation must preserve their hashes and denominators.

## What SAEPS computes

Let (r(w,p)) be the weighted residual vector at one trained checkpoint, with neural state (w) and physical parameters (p). The current code computes

\[
 F_{raw}=J_p^T J_p, \qquad
 F_\gamma=J_p^T P_\gamma J_p,
\]
\[
 P_\gamma=I-J_w(J_w^TJ_w+\gamma I)^{-1}J_w^T, \quad \gamma>0.
\]

It therefore measures local curvature remaining after a *finite, Euclidean, damped* state response in the residual discretisation. It is not automatically a Fisher information matrix for physical observations, a profile-likelihood Hessian, a posterior precision, or a global identifiability certificate.

If (J_w=U\,\mathrm{diag}(s_i)V^T), (P_\gamma) has eigenvalues (\gamma/(s_i^2+\gamma)) on the state-sensitive residual directions and 1 on their orthogonal complement. In exact arithmetic, (P_\gamma\succ0) for finite γ and

\[
\ker(F_\gamma)=\ker(J_p),
\]

although numerical effective rank depends on tolerance. Thus finite damping generally shrinks a state-compensable direction instead of making it exactly zero. A positive value can be entirely anchoring/regularisation information.

The independent counterexample (r=w+p-y) makes this distinction explicit. The unanchored profile is identically zero for every (p), while (F_\gamma=\gamma/(1+\gamma)>0). At γ equal to (10^{-6},10^{-2},1,100), the values are approximately (10^{-6},0.00990099,0.5,0.990099), respectively. Exact agreement with the *anchored* reduced Hessian would still not establish data identifiability.

The same issue appears under state reparameterisation. Writing (w=c z) and retaining a fixed γI changes the result with (c); a covariantly transformed state metric restores the simple example. A single scale-normalised γ cannot establish invariance for arbitrary neural reparameterisations. Likewise, diagonal retained ratios η can be misleading: the rank-one matrix \(\begin{bmatrix}1&1\\1&1\end{bmatrix}\) gives both diagonal ratios equal to one while only one parameter combination is identifiable.

Training residual weights also need interpretation. Physics penalties, initial/boundary penalties, state anchors and observation likelihood terms are not interchangeable. Only an independently specified observation model with covariance Σ supports

\[
 I_{obs}=J_y^T\Sigma^{-1}J_y,
\]

where (y=\mathcal H(u(p))) comes from the physical forward model. (F_\gamma^{-1}) must not be called a confidence covariance without an explicit statistical model and calibration study.

## Historical evidence audit

| Evidence group | Planned/valid denominator | What it supports | What it does not support |
|---|---:|---|---|
| V5 Burgers scalar | 15/12 | Finite-γ SAEPS can be closer than frozen-state GN to the declared local finite-γ reference on valid checkpoints. | Physical identifiability, nonlinear profile validity, or universal reliability. |
| V5 Allen–Cahn scalar | 10/9 | One independent PDE replication of the bounded curvature comparison. | Generalisation across PDEs, noise, architectures or physical experiments. |
| V5 nonlinear profile bridge | 5/1 `PROFILE_VALID` | Profile computation is an engineering path with limited usable evidence. | Equivalence of (F_\gamma) and nonlinear reoptimised profiles. |
| V5 two-parameter | 10/8 valid; below planned gate | Some valid coupled matrix records exist. | Confirmation of a stable identifiable subspace or 9/10 availability gate. |
| SO development | 25/21 matrix references; 19/21 historical improvements | A development mechanism/accuracy signal worth preserving as an ablation. | Independent SO confirmation; Phase-2 had 0/30 valid roots. |
| Phase-2 downstream | E2 0/20; E3 0/160; E6-P stopped | Root and low-cost certification bottlenecks are real engineering findings. | A claim that the physical branch or identifiability is absent. |
| Scalability | V5 cost-only to 100001 state parameters | Matrix-free cost can be measured at scale. | Accuracy or reliability at that scale. |

These records should be cited with their original manifests and failure reasons. No failed seed is an exclusion criterion for the new study.

## Literature synthesis and competitor matrix

The review package searched through 2026-09-12 and distinguishes formal publication from preprint status. The matrix below is a scoping map; it is not a claim of exhaustive systematic review.

| Method/literature | Mathematical object and target | State adaptation / combinations | Uncertainty or design | Main limitation and relation to SAEPS |
|---|---|---|---|---|
| Raue et al. (2009), profile likelihood | Nuisance-optimised likelihood profiles for structural/practical identifiability | Explicit nuisance profiling; combinations and flat profiles visible | Intervals and nonlinearity; expensive repeated fits | Foundational reference. SAEPS must be compared to profiles, not presented as a replacement without evidence. [DOI](https://doi.org/10.1093/bioinformatics/btp358) |
| Kharazmi et al. (2021) | PINN parameter/state inference with identifiability and predictability analysis | Joint PINN state/parameter effects considered | Problem-specific uncertainty/observability analysis | “First PINN identifiability” is not a valid novelty claim. [Nature Computational Science](https://www.nature.com/articles/s43588-021-00158-0) |
| Variable projection (Golub–Pereyra lineage; NIST 2012 record) | Exact elimination of separable linear nuisance variables | Exact only for separable linear blocks | Can reduce nonlinear dimension | SAEPS is local nonlinear state elimination, not classical global VarPro. [NIST](https://www.nist.gov/publications/variable-projection-nonlinear-least-squares-problems) |
| Schur-complement/reduced-Hessian PDE optimisation | Reduced derivatives after eliminating PDE/state variables | Adjoint or tangent state response | Often high fidelity but solver/adjoint cost | Supplies theory for state elimination; does not itself establish observation identifiability. |
| Classical sensitivity/FIM | (J_y^T\Sigma^{-1}J_y) and singular subspaces | Nuisance elimination by joint FIM/profile | Local information and experiment design | Strong independent physical reference; SAEPS must use matching observations and noise. |
| Rathore et al. (ICML 2024) | Loss-landscape conditioning and NysNewton-CG for PINN optimisation | Optimisation state, not physical identifiability | Training reliability | Useful for center availability, not a diagnostic competitor. [arXiv](https://arxiv.org/abs/2402.01868) |
| Wang et al. (2025) Gradient Alignment | Gradient conflict and SOAP/second-order preconditioning | Changes optimisation trajectory | Training stability/cost | Optimiser choice must remain separate from reliability claims. [arXiv](https://arxiv.org/abs/2502.00604) |
| PirateNets (Wang et al., JMLR 2024) | Residual-adaptive architecture/initialisation | Changes representation | Better PINN training | Width/architecture robustness is an audit factor, not the main novelty. [JMLR](https://jmlr.org/papers/v25/24-0313.html) |
| PINNacle benchmark (Hao et al., NeurIPS 2024) | Broad PINN training benchmark | No dedicated identifiability object | Benchmarking | Sets a realism bar for training claims. [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2024/hash/8c63299fb2820ef41cb05e2ff11836f5-Abstract-Datasets_and_Benchmarks_Track.html) |
| PINNACLE point selection (Lau et al., 2024) | Adaptive collocation and experimental-point selection | Changes observations/constraints | Experimental design | Must distinguish selecting existing collocation points from purchasing new measurements. [arXiv](https://arxiv.org/abs/2404.07662) |
| FIM-guided PINNs (Naveen Raj & Banerjee, 2026) | FIM-guided parameter identification in nonlinear vibratory systems | FIM may expose coupled directions | Real-time identification and intervals | Closest recent competitor; abstract-level evidence is insufficient for claims about implementation details. [Publisher](https://www.sciencedirect.com/science/article/pii/S0950705125022324) |
| Weak-form practical identifiability (Heitzman-Breen et al., 2026) | Noise/error-linked weak-form parameter criterion | Parameter combinations through sensitivity constraints | Practical error tolerances | ODE-focused, but a strong non-PINN baseline. [Publisher](https://link.springer.com/article/10.1007/s11538-026-01639-x) |
| Flores et al. (UAI 2025) | Error bounds and solution bundles for PINN UQ | Primarily predictive bundles | Coverage and width for solution uncertainty | Field coverage is not physical-parameter coverage. [PMLR](https://proceedings.mlr.press/v286/flores25a.html) |
| E-PINNs (Jacob et al., 2026) | Epistemic PINN wrapper and empirical uncertainty | Depends on pretrained PINN representation | Coverage, width and cost | Parameter calibration and identifiability still need separate validation. [Publisher](https://link.springer.com/article/10.1007/s44379-026-00086-8) |
| Static-snapshot identifiability limits (Gu et al., 2026) | Information limits from observation structure | Shows observation-induced non-identifiability | Diagnostic boundary cases | Supports explicit observation assumptions; preprint. [arXiv](https://arxiv.org/abs/2607.01749) |

### A1–A6 coverage audit

| Review theme | Sources represented in the supplied package | What is covered | Remaining gap before a submission claim |
|---|---|---|---|
| A1 PINN optimisation and conditioning | Rathore et al.; Wang et al.; PirateNets; PINNacle | Loss conditioning, second-order tools, architecture and benchmark failure modes | No new optimiser comparison in RI-2; centre validity remains separate from identifiability. |
| A2 inverse-PINN estimation | Kharazmi et al.; FIM-guided PINNs; weak-form identification | Joint state/parameter estimation, coupled coefficients and sparse/noisy settings | No independent confirmation across PDE families. |
| A3 structural/practical identifiability | Raue et al.; classical sensitivity/FIM; weak-form practical identifiability; static-snapshot limits | Profiles, rank, combinations, noise scale and observation-induced limits | No claim of exhaustive systematic review; parameter-subset/sloppy-model evidence remains scoped. |
| A4 state compensation and reduced geometry | Variable projection; Schur/reduced Hessian; PDE-constrained optimisation | Nuisance elimination, tangent/adjoint geometry and reduced curvature | PINN-reoptimised profile bridge is still unimplemented. |
| A5 uncertainty calibration | Flores et al.; E-PINNs; profile likelihood | Predictive bundles and empirical UQ versus physical-parameter coverage | No repeated-data intervals or bootstrap calibration in this project. |
| A6 observation design | PINNACLE point selection; analytic B3→B6 reference | Sensor/point selection distinction and flux intervention mechanism | No PINN retraining with new measurements; intervention evidence is physical-reference only. |

Additional foundational and neighboring references

| Method/literature | Mathematical object and target | State adaptation / combinations | Uncertainty or design | Main limitation and relation to SAEPS |
|---|---|---|---|---|
| Bellman & Åström (1970) | Structural identifiability from input-output maps | Structural uniqueness, not neural-state elimination | No finite-noise interval by itself | Establishes why local curvature cannot be called structural identifiability. [DOI](https://doi.org/10.1016/0025-5564(70)90132-x) |
| Walter & Pronzato (1997) | Identifiability and parameter estimation theory | Sensitivity and experiment structure | Design criteria | Classical foundation; SAEPS must state its observation assumptions. [Book record](https://books.google.com/books/about/Identification_of_Parametric_Models_from.html?id=SS_LcQAACAAJ) |
| Gutenkunst et al. (2007) | Sloppy sensitivity spectra and practical parameter directions | Coupled combinations visible in FIM eigenspaces | Experimental design implications | Supports subspace reporting; sloppy spectra are not uncertainty calibration. [PLOS](https://doi.org/10.1371/journal.pcbi.0030189) |
| Fröhlich et al. (2014) | Profile likelihood for nonlinear parameter identifiability | Explicit nuisance re-optimisation | Profile-based intervals | Direct R3 precedent; expensive and boundary-sensitive. [PLOS](https://doi.org/10.1371/journal.pcbi.1004015) |
| Raissi et al. (2019) | PINN residual optimisation for forward/inverse PDEs | Joint state/parameter training | No inherent calibration | Foundational PINN objective; does not make residual curvature a data FIM. [JCP](https://doi.org/10.1016/j.jcp.2018.10.045) |
| Karniadakis et al. (2021) | Scientific ML/PINN taxonomy and failure considerations | Representation and physics constraints | Broad UQ/design context | Places inverse PINNs in a wider scientific-ML setting; not a parameter reliability test. [Nature Reviews Physics](https://doi.org/10.1038/s42254-021-00314-5) |
| Yang et al. (2021), B-PINNs | Bayesian posterior over PINN states and coefficients | Joint posterior can expose coupling | Bayesian intervals and posterior checks | Requires likelihood/prior and sampling assumptions absent from current SAEPS. [JCP](https://doi.org/10.1016/j.jcp.2020.109913) |
| Krishnapriyan et al. (2021) | Empirical PINN failure modes and curriculum effects | Training path/representation dependence | Reliability of optimisation | Motivates separate centre-validity gates. [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2021/hash/df438e5206f31600e6ae4af72f2725f-Abstract.html) |
| Wang et al. (2021), PINN NTK analysis | Neural tangent kernel and training conditioning | Parameterisation affects optimisation geometry | Training dynamics, not physical intervals | Useful for representation audits; not an identifiability reference. [arXiv](https://arxiv.org/abs/2007.14527) |
| Efron & Tibshirani (1993) | Nonparametric bootstrap sampling distribution | Resamples observations, not nuisance states | Empirical interval calibration | Supplies R5 language; bootstrap does not repair structural confounding. [Book](https://doi.org/10.1007/978-1-4899-4541-9) |
| Pukelsheim (1993) | Optimal design and information criteria | Designs target parameter subspaces | A-/D-/E-optimality | Supports B3→B6 observation-design reasoning; design gain needs re-estimation evidence. [Book](https://doi.org/10.1137/1.9780898719109.fm) |
| Angelopoulos & Bates (2023) | Conformal predictive sets with finite-sample coverage | Predictive outputs, not nuisance elimination | Marginal/conditional coverage | Coverage of predicted fields is distinct from physical-parameter identifiability. [Foundations and Trends](https://arxiv.org/abs/2107.07511) |

The defensible gap is therefore narrow: a reliability-aware bridge that audits neural-state interference, finite damping and representation dependence against independent physical FIM/profile truth, returns combinations or abstention, and tests whether the diagnosis improves an observation design. “PINN + FIM” or “Schur complement” alone is not novel enough.

## Revised hypotheses

The new study should test, rather than assume, four hypotheses:

* **H1 (false-reliability reduction):** at a predeclared coverage range, state elimination has lower false reliable-declaration risk than frozen-state GN in state-compensation cases.
* **H2 (combination retention):** the diagnostic reports an identifiable combination such as (k/C), rather than declaring both (k) and (C) independently reliable or abstaining on every case.
* **H3 (stability disclosure):** damping paths, coordinate checks and representation checks identify when conclusions are fragile; no invariance is claimed without evidence.
* **H4 (intervention value):** a direction selected from the diagnosis leads, at equal observation cost, to smaller empirical error or narrower independent profiles after new measurements.

Failure of H1–H2 removes broad reliability claims. Failure of H3 narrows the claim to a coordinate- and damping-specific numerical diagnostic. Failure of H4 leaves an identifiability audit paper but does not justify an experimental-design claim.

## Audit conclusion

SAEPS is a meaningful local operator with a reusable matrix-free implementation. The central scientific risk is interpretation: finite-γ curvature can be positive when an unanchored physical profile is flat, and local rank is not structural or global identifiability. The next defensible work is to validate PINN-reoptimised profiles and matched independent-data decisions. The current evidence supports the bounded historical finite-damping comparisons, the analytic heat identifiability references and the analytic physical-model B3→B6 observation-design reference; it does not support a broad SAEPS reliability claim.

