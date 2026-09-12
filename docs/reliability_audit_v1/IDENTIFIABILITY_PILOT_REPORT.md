# Identifiability Pilot Report (RI-2)

**Status: COMPLETED AS DEVELOPMENT PILOT; CONFIRMATION STOPPED.** The 24 predeclared heat-equation PINN cases (B1–B4 × three data seeds × two optimizer seeds, noise σ=0.01) were executed once under the new namespace. All 24 produced computable `F_raw`, finite-γ `F_gamma`, and independent observation-FIM artifacts. No seed was retried or replaced.

The machine-readable aggregate is `outputs/reliability_audit_v1/pilot/ri2_full_v3/PILOT_RESULTS.json`. Fit-qualified counts are:

| benchmark | planned | computable | fit-qualified | profile-eligible |
|---|---:|---:|---:|---:|
| B1 strong scalar | 6 | 6 | 2 | 0 |
| B2 early-time weak | 6 | 6 | 6 | 0 |
| B3 k/C confounding | 6 | 6 | 6 | 0 |
| B4 state/amplitude compensation | 6 | 6 | 6 | 0 |
| **total** | **24** | **24** | **20** | **0** |

The frozen development availability rule requires at least 5/6 fit-qualified cases for each benchmark. B1 reaches only 2/6, so the rule fails and no confirmation cohort or intervention study is authorized. This is an engineering/availability stop, not evidence that SAEPS succeeds or fails as a reliability diagnostic.

The pilot also shows why fit qualification and identifiability must remain separate. The B3 fits are numerically qualified while the median estimates collapse near the lower search bound (`k≈1.22e−4`, `C≈1.67e−4`), despite the analytic reference proving that temperature-only data identify only `k/C`. B2 retains structural rank one but has a much smaller analytic sensitivity singular value than B1. These observations are descriptive development evidence; they are not confirmation statistics or calibrated uncertainty results.

Profiles were intentionally not implemented in this pilot (`PROFILE_ELIGIBLE=0/24`), so no nonlinear profile claim is made. The current decision is `PROTOCOL_STOP_PENDING_PROFILE_AND_B1_AVAILABILITY`: implement an independently validated profile engine and improve or replace the declared training representation in a new development version before any confirmation. Historical SAEPS outputs remain untouched.
