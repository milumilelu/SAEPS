# E7 profile resolution posthoc audit

This report reuses the corrected rescue output and does not rerun or retrain any point.

| h | planned | reference within 10% | full point certificate | branch comparable | gradient gate | positive Hessian | objective bound | median relative difference |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.01 | 3 | 3/3 | 2/3 | 2/3 | 2/3 | 2/3 | 2/3 | 0.0129172 |
| 0.003 | 3 | 1/3 | 1/3 | 1/3 | 1/3 | 1/3 | 1/3 | 0.175566 |
| 0.001 | 3 | 0/3 | 2/3 | 2/3 | 2/3 | 2/3 | 2/3 | 1.22655 |

The table separates numerical agreement with the local Schur reference from the stricter point certificate. At h=0.01 all three saved branches are within 10% of the reference, but only two have the complete certificate; the smaller steps show larger discrepancies and/or basin and positive-Hessian failures. This is a resolution and branch-control observation, not a convergence proof or a GN-causality result.
