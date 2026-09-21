# Matched-alpha operator audit

A small, read-only operator audit at seed 215 evaluates explicit dense, matrix-free CG and scaled LSQR against the dense solve at the same gamma.

- grid completeness: PASS (12/12 rows)
- solver pass rows: 12/12
- maximum relative residual: 7.006e-11
- maximum difference from dense reference: 2.993e-08

| alpha | PASS | max residual | max dense difference |
|---:|---:|---:|---:|
| 1e-08 | 3/3 | 7.006e-11 | 2.993e-08 |
| 1e-06 | 3/3 | 5.017e-11 | 2.333e-09 |
| 0.0001 | 3/3 | 5.608e-11 | 2.147e-10 |
| 0.01 | 3/3 | 6.197e-11 | 2.638e-11 |

The audit supports the narrower statement that the matrix-free operator agrees with the dense reference across the tested damping levels on this small coupled checkpoint. It does not convert the alpha=1e-2 large-state timing experiment into an alpha=1e-8 trained-accuracy result.

Machine-readable lineage: `outputs/posthoc/paper_strengthening/e8_matched_alpha_summary.json`.
