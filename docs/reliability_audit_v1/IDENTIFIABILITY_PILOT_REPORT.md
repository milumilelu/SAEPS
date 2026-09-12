# Identifiability Pilot Report (RI-2)

**Status: DEVELOPMENT PILOTS COMPLETED; CONFIRMATION NOT AUTHORIZED.** Three versioned 24-case pilots are retained. `ri2_full_v3` is the original single-stream pilot (20/24 fit-qualified; B1 2/6). `ri2_full_v5` is an intermediate corrected development version with an explicit separate noise RNG stream and B4 initial amplitude treated as a nuisance coordinate in the eliminated state block. No case was silently replaced.

The current machine-readable aggregate is `outputs/reliability_audit_v1/pilot/ri2_full_v6/PILOT_RESULTS.json`; v3, v5 and v6 are all retained as versioned attempts. It contains 24/24 computable cases and 23/24 fit-qualified cases; the terminal status is `PASS` for 23 and `CHECKPOINT_INVALID` for one fit-gate failure:

| benchmark | planned | computable | fit-qualified | profile-eligible |
|---|---:|---:|---:|---:|
| B1 strong scalar | 6 | 6 | 5 | 0 |
| B2 early-time weak | 6 | 6 | 6 | 0 |
| B3 k/C confounding | 6 | 6 | 6 | 0 |
| B4 state/amplitude compensation | 6 | 6 | 6 | 0 |
| **total** | **24** | **24** | **23** | **0** |

The corrected pilot passes the predeclared 5/6 availability rule. Independent analytic profiles now cover all B1–B6 with 31 scan points: B1/B2/B5/B6 are informative, while B3 and B4 are flat under their known confounding structures. The independent finite-difference physical reference also passes its refinement gate (64-to-128 discrepancy approximately 1.58e-4, below the declared 0.01 noise scale).

A separate fixed six-point gamma-path and abstaining decision analysis is stored in `outputs/reliability_audit_v1/pilot/ri2_full_v6/reliability_analysis/RI2_RELIABILITY_ANALYSIS.json`. It uses no parameter-error tuning. The current fixed rule labels all fit-qualified B2–B4 cases weak/confounded and does not establish a reliable-declaration advantage over RAW; the risk/coverage curve is descriptive and has high false-reliable risk at its non-abstaining candidates. Therefore G2 is not met and confirmation remains stopped.

A small representation/weight audit is stored in `outputs/reliability_audit_v1/pilot/ri3_representation/REPRESENTATION_AUDIT.json`; the B3 finite-γ eigenspectrum changes by orders of magnitude across widths and data-loss weights, so G3 invariance is not passed. An analytic physical bootstrap reference is stored in `outputs/reliability_audit_v1/pilot/ri1/BOOTSTRAP_REFERENCE.json` (B2 is visibly broad), but it is not PINN interval calibration. The pilot does not implement PINN-reoptimised nonlinear profiles, repeated-data PINN estimates, B5/B6 PINN intervention, or a matched RAW-versus-SAEPS risk study. No claim is made that finite-γ curvature is observation information, that SO is superior, or that individual B3 coefficients are separately identifiable. The next defensible development step is to validate a profile-capable checkpoint workflow and only then decide whether a new confirmation protocol is scientifically justified. Historical SAEPS outputs remain untouched.
