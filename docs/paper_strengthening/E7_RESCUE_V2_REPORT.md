# E7 corrected profile rescue v2

This is a new development-only rescue cohort. The locked E7 output and V5 profile bridge are unchanged.

- planned centres: 3
- planned profile points: 9
- profile points passing the full stationarity/Hessian/start-agreement certificate: 5/9
- centres passing the fixed three-scale h^2 profile certificate: 0/3
- independent start records: 36; positive-Hessian records: 26; strict raw fallbacks: 15

| Centre | Valid points | h² intercept | R² | Intercept relative error | Profile certificate |
|---:|---:|---:|---:|---:|:---:|
| 916101 | 3/3 | 1.47505 | 0.404 | 0.122 | FAIL |
| 916102 | 2/3 | — | — | — | FAIL (INSUFFICIENT_VALID_POINTS) |
| 916103 | 0/3 | — | — | — | FAIL (INSUFFICIENT_VALID_POINTS) |

The corrected numerical path removes the old raw-vs-normalised tolerance mismatch and certifies the objective error where the damped state Hessian is positive. It does not restore the profile claim: 916101 has three numerically certified points but an h² extrapolation R² of about 0.40 and a 12% intercept discrepancy; 916102 has an independent-start/basin failure at one scale; 916103 has no fully certified point because the displaced solves do not reach a positive-Hessian stationary branch from both starts.

This result is evidence about the failure mechanism and the limits of finite-displacement interpretation. It does not reclassify the original 0/21 stationarity or 1/5 profile verdict.

Machine-readable lineage: `outputs/posthoc/paper_strengthening/e7_rescue_v2_summary.json`.
