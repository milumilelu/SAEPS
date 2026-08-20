# v4.2 Corrected Untouched Confirmation Report

**Scientific status:** `SUPPORTED`  
**Planned / valid / invalid:** `15 / 12 / 3`  
**Strict wins in planned denominator:** `12/15`

## Locked primary adjudication

All four conditions pass: minimum valid pairs `True`, planned wins `True`, positive median D `True`, and exact one-sided sign test `True`. Median D is `27.6363190428` and the exact one-sided p-value is `0.000244140625`.

The v4.2 comparative claim is therefore `SUPPORTED`: on all 12 valid seeds, SAEPS is closer than raw fixed-state curvature to the exact finite-gamma reduced Hessian. Seeds 57, 61 and 63 are center-invalid and remain planned non-wins.

## Secondary absolute accuracy

E_SAEPS median is `7.503229%`, IQR `4.156146%`, and range `1.420540%` to `20.705106%`. `3/12` valid seeds are within 5%. Thus SAEPS is strongly better than raw but is not a uniformly 5%-accurate exact-Hessian surrogate.

The frozen GN indicator has accuracy `0.750`, Spearman `0.622378`, and median absolute calibration error `0.024830`. This is secondary evidence, not a recalibrated primary claim.

## Execution audit

All 15 seed computations were performed once. After seed 69, final aggregation encountered a missing non-scientific `failure_stage` schema field. The recovery added that field only in memory from independent node statuses, invoked the frozen aggregator, and recomputed no seed or primary quantity. Independent raw-to-aggregate validation passes. This deviation is retained in the machine audit.

V3.6 remains `NOT_SUPPORTED` and unchanged; v4.2 does not rewrite it. V4.2 is permanently closed and cannot be rerun.

Raw manifest hash: `2c8166bcf973188cb3cfbd7f106a6a70b16e5b687e3b30de14ffffd9dee26b0e`.
