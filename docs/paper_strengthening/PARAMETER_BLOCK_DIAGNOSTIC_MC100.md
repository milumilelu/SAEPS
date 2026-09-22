# Parameter-block diagnostic on MC100

The 100-refit cohort shows why the exact parameter-block correction does not improve coverage in this E3 setting.

| Quantity | Mean | Median |
|---|---:|---:|
| raw fixed-state GN curvature | 14.792 | 14.784 |
| exact fixed-state parameter block | 14.789 | 14.785 |
| SAEPS state-eliminated curvature | 0.885 | 0.856 |

The exact parameter-block/raw ratio is 0.99981 on average (median 0.99984), whereas the SAEPS/raw ratio is only 0.0599 on average (median 0.0580). Thus the parameter-block correction leaves the dominant fixed-state curvature essentially unchanged; its 20% coverage is expected to match raw coverage. The failure is not a PSD or numerical-calibration problem in this scalar cohort. It is a structural limitation: correcting the exact parameter Hessian block does not remove state adaptation.

This result supports reporting parameter-block as a negative control rather than as a competing successful correction.
