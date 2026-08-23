# V5.4 Residual-Dimension Scalability Report

- Engineering status: `PASSED`
- Terminal/pass records: `27/27` of 27
- Role: cost-only evidence; no scientific claim gate.
- Residuals: constructed from actual PDE/data/initial/boundary points; no synthetic padding.
- Peak memory: unavailable because native CPU tensor peak memory is not reliably instrumented.
- Complexity exponent: not fitted or claimed, as preregistered.

| n_theta | m | PASS | wall s median [min,max] | solve s median | CG iter median | max verified residual |
|---:|---:|---:|---:|---:|---:|---:|
| 1001 | 213 | 3/3 | 0.353524 [0.316829,0.356988] | 0.353524 | 19 | 5.404e-11 |
| 1001 | 853 | 3/3 | 0.431057 [0.418985,0.446984] | 0.431056 | 20 | 8.041e-12 |
| 1001 | 3413 | 3/3 | 0.650188 [0.64707,0.665758] | 0.650188 | 20 | 1.200e-11 |
| 10001 | 213 | 3/3 | 0.436132 [0.428651,0.436465] | 0.436132 | 15 | 1.895e-12 |
| 10001 | 853 | 3/3 | 0.926875 [0.90971,0.943333] | 0.926874 | 15 | 1.439e-12 |
| 10001 | 3413 | 3/3 | 3.9367 [3.85218,3.95314] | 3.9367 | 15 | 1.436e-11 |
| 100001 | 213 | 3/3 | 1.88744 [1.81598,1.90462] | 1.88744 | 11 | 7.241e-11 |
| 100001 | 853 | 3/3 | 8.31442 [8.26773,8.42439] | 8.31441 | 11 | 6.480e-11 |
| 100001 | 3413 | 3/3 | 40.9669 [40.4007,41.4298] | 40.9669 | 11 | 7.819e-11 |
