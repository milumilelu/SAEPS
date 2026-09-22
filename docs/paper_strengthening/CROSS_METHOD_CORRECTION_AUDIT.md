# Cross-method correction audit

## Purpose

This audit supplements the Route A evidence without changing the data-generating process. It compares three layers using the same 30 E3 noisy-data refits:

1. raw fixed-state curvature with the original model-based Wald variance;
2. raw fixed-state curvature with joint sandwich variance;
3. SAEPS state-eliminated curvature with the same joint sandwich variance.

The comparison separates variance calibration from curvature correction. It is not yet a fully independent direct-profile benchmark, because both sandwich rows use the same joint local Jacobian.

## Results

| Construction | Coverage | Interpretation |
|---|---:|---|
| raw + model-based variance | 0/30 = 0.0% | severe overconfidence from fixed-state curvature and missing nuisance variance |
| raw + joint sandwich variance | 5/30 = 16.7% | nuisance variance alone does not repair curvature overstatement |
| SAEPS + joint sandwich variance | 23/30 = 76.7% | state elimination removes the dominant curvature component in this benchmark |

The raw interval remains severely undercovered after sandwich calibration. Therefore, the improvement from 0% to 76.7% cannot be explained by variance calibration alone; it requires the state-eliminated curvature used by SAEPS.

## Relation to the two-source decomposition

The audit supports the following decomposition:

- the raw-to-sandwich comparison isolates the effect of accounting for nuisance-state noise propagation;
- the sandwich-raw-to-sandwich-SAEPS comparison isolates the additional effect of replacing fixed-state curvature with state-eliminated curvature;
- the remaining SAEPS failures are concentrated in high-bias refits, as documented in `ROUTE_A_BIAS_DECOMPOSITION.md`.

## Limitation

This is a cross-construction audit, not a fully independent method validation. A direct reoptimized profile curvature or bootstrap refitting variance is still needed for a stronger claim that the decomposition is independent of SAEPS and the local Jacobian approximation.

## Paper-ready wording

> Joint sandwich calibration alone did not resolve the undercoverage of fixed-state intervals: raw coverage increased only from 0% under the model-based variance to 16.7%. Replacing the fixed-state curvature by the state-eliminated curvature while retaining the same sandwich construction increased coverage to 76.7%. This matched-variance comparison indicates that the dominant correction is geometric state elimination rather than variance inflation alone.
