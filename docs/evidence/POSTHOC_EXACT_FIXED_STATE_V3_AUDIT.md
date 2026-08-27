# Audit: SAEPS post-hoc exact fixed-state curvature decomposition v3

## Audit conclusion

`PASSED`

This analysis is post hoc and nonbinding. It does not alter any preregistered
confirmation result.

## Repository and protocol lineage

- Baseline scientific commit:
  `cf76ffe85a78c994351e50b97d013d33a0f01f85`.
- Branch: `posthoc/exact-fixed-state-decomposition-v3`.
- Frozen V3 execution-claim commit: `538b866`.
- Five-seed canary evidence commit:
  `32708fcbc8b4038fa37829ad897530093e7cd074`.
- Complete raw/aggregate evidence commit:
  `e30f65df3b9321422439b5f28d99b157f14ae100`.
- V1 and V2 are visibly retained as aborted protocols and supply no scientific
  value to the V3 aggregate.

## Validation before and after

- Pre-run V5 repository validator: `PASSED`, stored in
  `outputs/posthoc/exact_fixed_state_v3/preflight.json`.
- Final V5 repository validator after all 25 raw records and aggregate files:
  `PASSED`.
- V3 actual-evidence tests: `PASSED`; they independently verify every raw
  record SHA-256, the 25-seed denominator, original-valid/invalid membership,
  reproduction and numerical states, exact identities, and raw-to-aggregate
  medians.
- All 25 raw JSON records parse successfully.

## Historical immutability

The diff from the baseline contains no change under the protected historical
confirmation outputs, locked configurations, final V5 audit, original summary,
failed-seed records, or existing scientific adjudication. All new scientific
files are isolated under `outputs/posthoc/exact_fixed_state_v3/`,
`configs/posthoc_exact_fixed_state_v3.yaml`, the versioned post-hoc scripts and
tests, and `docs/evidence/posthoc_exact_fixed_state_v3.*`.

No seed was replaced. Original-invalid Burgers seeds 57, 61 and 63 and
Allen--Cahn seed 81 remained invalid and are present as terminal raw records.

## Completeness and numerical correctness

| Cohort | Planned | Original-valid | Reproduction-pass | Analysis-valid |
|---|---:|---:|---:|---:|
| Burgers | 15 | 12 | 12 | 12 |
| Allen--Cahn | 10 | 9 | 9 | 9 |

- Reproduction mismatches: none.
- Algebraic/numerical failures among original-valid seeds: none.
- Maximum primary-curvature reproduction relative error: `3.51e-16`.
- Maximum selected-LSQR versus explicit-Schur relative error: `5.70e-11`.
- Maximum serialized exact error-identity relative residual: `0.0`.
- GN remainder bound applicable: `0/21`; every `delta` exceeded one, so the
  sufficient bound condition is unavailable rather than failed.
- Total summed per-seed runtime: `3801.891591 s` (about 63 min 22 s).

## Descriptive mechanism result

| Median | Burgers | Allen--Cahn |
|---|---:|---:|
| `E_fix_exact_to_reduced` | 27.749988 | 19.947156 |
| `E_GN_fix_reduced_scale` | 0.156315 | 0.290258 |
| `E_relax` | 0.003081 | 0.002340 |
| `rho_relax` | 1.002442 | 1.002340 |
| `R_freezing_to_GN` | 166.513443 | 65.238090 |

For all 21 analysis-valid reruns, exact state-freezing error exceeded
fixed-state Gauss--Newton truncation under the reduced-Hessian normalization.
The GN relaxation correction closely tracked the exact relaxation correction.
These are descriptive post-hoc mechanism findings; no original gate, p-value,
denominator or paper claim was changed.

## Deliverables and author direction

- Complete per-seed exact and GN blocks: retained.
- Machine-readable aggregate JSON and CSV: retained.
- SHA-256 raw/artifact manifest: retained.
- Human-readable mechanism report and this audit: retained.
- Mechanism PDF figure: intentionally omitted at the author's direction.
