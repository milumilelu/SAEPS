# P5 Scalar Confirmation — Acceptance Evidence

**Engineering gate:** `PASSED`  
**SG-2:** `PARTIALLY_SUPPORTED`  
**Run:** `p5-scalar-s10-20260819T082303.440919+0000-ecf337e72926`  
**Lock commit:** `ad794ca2908c8935d0e21702fab7914ff944cce7`  
**Execution commit:** `90ca1a4765cd69c8cb7134b341a90ad17085b040` (`git_dirty=false`)

All 10 planned seeds have final statuses: 1 `PASS`, 1 `CHECKPOINT_INVALID`, and 8 `PROFILE_FAILURE`. There were no solver or numerical failures. Manifest SHA256 verification, SVG parsing and CSV existence checks passed.

The eight profile failures were not optimizer failures: all 56 reoptimization points passed the locked combined stopping rule. Their locked quadratic fit R2 values ranged from `0.0963` to `0.9878`, below `0.99`; no point was interpolated or excluded silently.

Only seed 18 formed a valid pair:

```text
E_raw   = 19.265994679401842
E_saeps = 0.05884864022049956
D       = 19.207146039181342
eta_se  = 0.05224755344955769
eta_profile = 0.049187140255932245
```

Thus paired wins are `1/10`. The numeric median and percentile interval both equal the single valid value; this degenerate interval is reported but is not evidence for uncertainty control or strong support. The locked classifier returns `PARTIALLY_SUPPORTED`, reflecting a positive result in the sole valid pair but inadequate confirmation coverage. No locked setting was changed and the run was not repeated.

