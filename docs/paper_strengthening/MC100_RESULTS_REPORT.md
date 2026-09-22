# 100-replicate Monte Carlo results

## Main result

The expanded E3 development cohort contains 100/100 valid refits and no solver failures.

| Construction | Covered | Coverage | Wilson 95% interval |
|---|---:|---:|---:|
| raw + joint sandwich | 20/100 | 20.0% | [13.3%, 28.9%] |
| SAEPS + joint sandwich | 70/100 | 70.0% | [60.4%, 78.1%] |
| parameter-block + joint sandwich | 20/100 | 20.0% | [13.3%, 28.9%] |

The raw deficit is therefore not a 30-replicate sampling accident. SAEPS improves coverage by 50 percentage points, but does not reach the nominal 95% level.

## Bias-stratified result

Using the known synthetic truth only as a diagnostic stratifier:

| Absolute parameter error | n | raw | SAEPS | parameter-block |
|---|---:|---:|---:|---:|
| <= 0.02 | 25 | 80.0% | 100.0% | 80.0% |
| 0.02–0.05 | 32 | 0.0% | 96.9% | 0.0% |
| > 0.05 | 43 | 0.0% | 32.6% | 0.0% |

The mean estimate is 1.2015 for a truth of 1.2; the mean bias is small, but the distribution has a substantial high-error tail. That tail dominates the remaining SAEPS undercoverage. The result is consistent with a mixture of mostly well-behaved refits and a high-bias subpopulation, rather than a single constant global bias.

## Interpretation

The 100-replicate result strengthens the two-source decomposition:

1. fixed-state curvature creates severe undercoverage even after sandwich variance calibration;
2. state elimination corrects most of that geometric component for low and intermediate bias refits;
3. high-bias refits remain undercovered, so curvature correction alone cannot provide finite-sample 95% calibration.

The experiment remains development-only and does not alter locked confirmation.
