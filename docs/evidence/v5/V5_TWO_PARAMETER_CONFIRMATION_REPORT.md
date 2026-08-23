# V5.3 Two-Parameter Confirmation Report

- Engineering status: `PASSED`
- Scientific status: `INCONCLUSIVE`
- Binding-valid: `8/10` (required >=9)
- Planned wins: `8/10` (required >=9)
- Valid median D2: `14.4917`
- One-sided exact sign test: `8/8`, p=`0.00390625`

The direction of the comparison is positive for every valid seed, but the preregistered minimum-valid and planned-win gates fail because seeds219 and221 are checkpoint-invalid. The correct status is INCONCLUSIVE, not NOT_SUPPORTED.

| Seed | Terminal | Valid | Planned win | E_raw2 | E_SAEPS2 | D2 | Coupling | Eigengap (nonbinding) |
|---:|---|---|---|---:|---:|---:|---:|---:|
| 215 | PASS | true | true | 17.3643 | 0.0259327 | 17.3383 | 0.864697 | 0.616019 |
| 216 | PASS | true | true | 9.57217 | 0.0211552 | 9.55102 | 0.760396 | 0.362947 |
| 217 | PASS | true | true | 14.4154 | 0.0109979 | 14.4044 | 0.710863 | 0.340342 |
| 218 | PASS | true | true | 14.5991 | 0.0201913 | 14.579 | 0.784431 | 0.318335 |
| 219 | CHECKPOINT_INVALID | false | false | NA | NA | NA | NA | NA |
| 220 | PASS | true | true | 9.23728 | 0.038536 | 9.19874 | 0.810108 | 0.348985 |
| 221 | CHECKPOINT_INVALID | false | false | NA | NA | NA | NA | NA |
| 222 | PASS | true | true | 14.9614 | 0.0298242 | 14.9316 | 0.814573 | 0.385574 |
| 223 | PASS | true | true | 15.508 | 0.118557 | 15.3895 | 0.822541 | 0.246095 |
| 224 | PASS | true | true | 12.3405 | 0.0952626 | 12.2452 | 0.798614 | 0.329348 |
