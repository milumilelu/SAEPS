# V5.5 Baseline Consolidation

- Engineering status: `PASSED`
- New training: `0`
- Inherited profile-bridge scientific status: `NOT_SUPPORTED`
- PROFILE_VALID: `1/5`
- Claim boundary: nonlinear-profile equivalence is not supported and must not be claimed.

The objective curves compare the fixed-state quadratic, the SAEPS-GN quadratic, and the actually reoptimized finite-gamma profile at identical offsets. Reported profile mean losses are multiplied by each record's residual count to match the total-objective curvature units.

| Seed | Profile valid | F_raw | F_se_GN | H_red_exact,gamma | H_profile,gamma (h=0.005) |
|---:|---|---:|---:|---:|---:|
| 200 | false | 88.5804 | 6.53587 | 4.95845 | 1.02115 |
| 201 | false | 120.718 | 7.78272 | 6.48696 | -4.78898 |
| 202 | false | 110.074 | 5.95983 | 4.39664 | 5.596 |
| 203 | false | 117.072 | 6.70497 | 5.82192 | 5.22891 |
| 204 | true | 123.156 | 7.94042 | 6.41227 | 6.75768 |

Finest-scale profile curvatures for invalid seeds are nonbinding diagnostics, not reference values. Only seed204 passes the frozen profile-validity rules.
