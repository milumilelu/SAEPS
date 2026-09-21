# Parameter-block correction posthoc audit

This development-only audit reuses saved curvature blocks and performs no training.
It reports signed errors relative to the exact finite-damping reduced Hessian.

| Source / group | rows | median E_raw | median E_SAEPS | median E_block | block improves SAEPS | block improves raw |
|---|---:|---:|---:|---:|---:|---:|
| E6_architecture::base_2_16_1 | 6 | 16.7966 | 0.000922445 | 0.000106776 | 6/6 | 6/6 |
| E6_architecture::deep_2_16_16_1 | 6 | 17.2655 | 0.000432235 | 7.96563e-05 | 5/6 | 6/6 |
| E6_architecture::wide_2_32_1 | 6 | 16.9314 | 0.000608728 | 0.000209218 | 5/6 | 6/6 |
| exact_fixed_state_v3::Allen-Cahn | 9 | 20.3728 | 0.278567 | 0.0454731 | 9/9 | 9/9 |
| exact_fixed_state_v3::Burgers | 12 | 27.7268 | 0.0750323 | 0.0884922 | 5/12 | 12/12 |

All 39/39 rows satisfy F_block = F_se_GN + H_ll_exact - G_ll to the 1e-10 absolute check.
The exact-block source contains 25 planned files; 4 are excluded by their saved invalid status and remain listed in parameter_block_summary.json.

The signed rows retain cases where the correction worsens absolute error. No row is removed because of that outcome, and no nonlinear-profile or covariance claim is inferred.
