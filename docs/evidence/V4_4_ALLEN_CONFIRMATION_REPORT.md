# v4.4 Allen--Cahn External Confirmation Report

**Scientific status:** `SUPPORTED`  
**Planned / valid / invalid:** `10 / 9 / 1`  
**Strict wins in planned denominator:** `9/10`

## Locked primary adjudication

All four preregistered conditions pass: minimum valid pairs `True`, planned wins `True`, positive median D `True`, and exact one-sided sign test `True`. Median D is `20.0064951395` and the exact one-sided p-value is `0.001953125`.

The v4.4 external Allen--Cahn comparative claim is `SUPPORTED`: SAEPS is closer than raw fixed-state curvature to the exact finite-gamma reduced Hessian on all nine valid seeds. Seed 81 is center-invalid and remains a planned non-win.

## Secondary absolute accuracy and profile bridge

E_SAEPS median is `27.856670%`, IQR `14.807139%`, and range `11.989208%` to `46.672331%`. `0/9` valid seeds are within 5%. SAEPS therefore improves the comparative endpoint strongly but is not a uniformly accurate exact-Hessian surrogate.

The frozen GN indicator has classification accuracy `1.000`, Spearman association `0.983333`, and median absolute calibration error `0.063049` on nine valid seeds. This remains secondary, non-recalibrated evidence.

The gamma-matched nonlinear profile bridge passes only `1/10` planned seeds. It is nonbinding by protocol and does not change the curvature-primary result, but nonlinear-profile agreement is not established.

## Execution audit

All ten seed computations were performed exactly once. After the frozen aggregate summary was written, packaging attempted to hash an incorrect directory. The recorded recovery only hashed the already committed raw files at their actual paths and generated the missing manifest and failed-seed file. Independent raw-to-frozen-aggregate reproduction passes; no seed, raw value, threshold or status rule changed.

Raw manifest hash: `de7f91b110da243c87a5b9d59846f49cbf53a22c8dc303e510d66ff2b94c657a`. V4.4 is permanently closed and cannot be rerun.
