# P2 Controlled Tangent Geometry — Confirmation Evidence

**Engineering gate:** `PASSED`  
**Scientific gate SG-1:** `FAIL`  
**Confirmation date:** 2026-08-19  
**Locked implementation/config commit:** `7bc466a60936e065430e5180d3279aa90a9cef10`

## Locked run identity

- Run ID: `p2-confirmation-s10-20260819T072235.025972+0000-7059ee357d5a`
- Phase-lock SHA256: `32003edbcfbe03c6bf357ffce25051ba9b279263a15d2e80b4c762087ec0c30e`
- Provenance: Python 3.12.13, PyTorch 2.13.0, float64 CPU, `git_dirty=false`
- Locked sources: `q_parallel=sin3x_sin2t`, `q_perpendicular=sin4x_constantt`
- Locked `gamma_alpha=1e-10`
- Wall time: `108.59190169999783` seconds

## Engineering denominator

All 10 locked seeds and all five locked alpha values ran exactly once:

```text
planned evaluations:   50
completed evaluations: 50
PASS:                   25
CHECKPOINT_INVALID:     25
SOLVER_FAILURE:          0
NUMERICAL_FAILURE:       0
PROFILE_FAILURE:         0
```

The manifest contains 50 record paths and SHA256 hashes; an independent verification found all hashes valid. The generated `figure2_controlled_geometry.svg` parses as valid XML. Across the 25 valid evaluations, maximum formal CG relative residual was `9.824566961063183e-11` (`<=1e-8`) and maximum explicit/MF relative error was `5.549164375509722e-9` (`<1e-6`).

## Locked checkpoint gate

All seeds passed training loss `<=0.1`. Seeds 10, 11, 12, 13, and 16 failed only the locked diagnostic `S_theta<=0.01` gate and were not assigned eta values.

| Seed | Status | Training loss | S_theta | State RMSE (validation-only) |
|---:|---|---:|---:|---:|
| 10 | CHECKPOINT_INVALID | 0.004665007104961487 | 0.011402142035860952 | 0.02055484896174564 |
| 11 | CHECKPOINT_INVALID | 0.0026251876204991193 | 0.01898600273493288 | 0.01681112532301857 |
| 12 | CHECKPOINT_INVALID | 0.00277525638000145 | 0.01707289720409125 | 0.019198092919150592 |
| 13 | CHECKPOINT_INVALID | 0.002340221592917318 | 0.0112128913415081 | 0.014541228363555342 |
| 14 | PASS | 0.0025045168612806653 | 0.0019176814675438208 | 0.016867300300821748 |
| 15 | PASS | 0.006138411241658664 | 0.008190172780856503 | 0.016317769164136613 |
| 16 | CHECKPOINT_INVALID | 0.0035757766206772085 | 0.02290054188144901 | 0.016142829479772233 |
| 17 | PASS | 0.0025553552257108823 | 0.00950189403568376 | 0.017298704850906996 |
| 18 | PASS | 0.0021456526900231207 | 0.002398738070498483 | 0.01653587906969686 |
| 19 | PASS | 0.0024589219135319916 | 0.007474919465477967 | 0.018365546319432585 |

Training loss is exactly reconstructed as `0.5 * total_weighted_rms^2`, because the locked training and diagnostic point sets are identical and the recorded objective uses the mean squared weighted residual.

## All valid seed eta values

Columns correspond to `alpha=[0,0.25,0.5,0.75,1]`.

| Seed | eta values | Spearman | Monotonic |
|---:|---|---:|---|
| 14 | [0.024400955439251023, 0.06050959077059461, 0.0999086399680296, 0.14051206405728087, 0.1844059018078316] | 0.9999999999999998 | yes |
| 15 | [0.033944165447477914, 0.11436914747827658, 0.1953657052731144, 0.2765714742840624, 0.35834881907089344] | 0.9999999999999998 | yes |
| 17 | [0.025805813537996013, 0.07857339817331505, 0.12517020840207418, 0.16950835904664655, 0.20767573504216036] | 0.9999999999999998 | yes |
| 18 | [0.027234185249862593, 0.056710901889400755, 0.08947820880965274, 0.12344995539132908, 0.16071229223232103] | 0.9999999999999998 | yes |
| 19 | [0.027757896973300757, 0.06883167415370636, 0.11345622361622872, 0.1593804456350572, 0.20885543734975007] | 0.9999999999999998 | yes |

Median eta by alpha was `[0.027234185249862593, 0.06883167415370636, 0.11345622361622872, 0.1593804456350572, 0.20767573504216036]`.

## Scientific decision

Among valid seeds, median Spearman was `0.9999999999999998` and all 5/5 were monotonic. This does **not** satisfy the preregistered 10-seed denominator: only 5/10 seeds were valid and only 5/10 could count as monotonic, below the required 8/10. Therefore SG-1 is `FAIL`.

No source, gamma, threshold, seed, or alpha was changed after viewing confirmation results. P2 engineering completion authorizes P3, but the negative SG-1 outcome remains binding for final interpretation.

