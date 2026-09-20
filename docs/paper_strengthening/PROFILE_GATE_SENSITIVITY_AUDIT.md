# Profile gate sensitivity audit

This is an aggregation-only audit. It does not alter the locked E7 verdict.

| Normalized gradient threshold | Branches passing | Paired steps passing |
|---:|---:|---:|
| `1e-04` | 42/42 | 21/21 |
| `1e-05` | 42/42 | 21/21 |
| `1e-06` | 42/42 | 21/21 |
| `1e-07` | 42/42 | 21/21 |
| `1e-08` | 5/42 | 1/21 |
| `1e-09` | 0/42 | 0/21 |
| `1e-10` | 0/42 | 0/21 |
| `1e-12` | 0/42 | 0/21 |

The audit shows that the original (10^{-8}) requirement is the binding numerical gate, while (h^{-2}) amplification remains a separate profile-error requirement. A relaxed threshold is therefore a candidate for a new predeclared rescue protocol, not a retrospective reclassification.

Source: `experiments\paper_revision_20260916\outputs\heldout\e7\e7_profile_resolution.csv` (SHA256 `11d7cd271fd9d6ee4a3d7e8410d147f9b0c0d12b9de5cf288d3bd4ed5279c555`).
