# E7 profile rescue probe report

These probes are development-only and leave the locked E7 output unchanged.

| Seed | Budget | Step | Maximum branch gradient | Relative Schur difference |
|---:|---:|---:|---:|---:|
| 916101 | 30000 | 0.01 | 4.329e-09 | 0.0001 |
| 916101 | 30000 | 0.003 | 7.099e-09 | 0.0014 |
| 916101 | 30000 | 0.001 | 9.395e-09 | 0.0010 |
| 916102 | 30000 | 0.01 | 4.313e-08 | 0.0261 |
| 916102 | 30000 | 0.003 | 1.670e-08 | 0.0090 |
| 916102 | 30000 | 0.001 | 3.765e-08 | 0.0204 |
| 916103 | 30000 | 0.01 | 9.784e-09 | 0.0009 |
| 916103 | 30000 | 0.003 | 1.134e-08 | 0.1441 |
| 916103 | 30000 | 0.001 | 9.321e-09 | 0.0037 |
| 916103 | 100000 | 0.003 | 6.631e-09 | 0.1553 |

The 30000-step probes show that the original 1000-step budget was a real numerical limitation: seeds 916101 and 916102 reach sub-3-percent reference differences at the tested scales. The 916103 h=0.003 probe remains at 14.4% after 30000 steps and 15.5% after 100000 steps, even though both branch gradients are below 1e-8 in the longer run. This rules out a pure threshold explanation and points to finite-displacement branch, basin, or model-nonlinearity effects.

The result supports a rescue protocol with separate solver stopping and profile-error certification. It does not support changing the historical 0/21 stationarity or 1/5 profile-valid verdict.

Source records are listed in `outputs/posthoc/paper_strengthening/e7_rescue_probe_summary.json`.
