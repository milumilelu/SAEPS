# P6 Multi-parameter Confirmation — Acceptance Evidence

**Engineering gate:** `PASSED / grid NOT_APPLICABLE_NO_VALID_SEED`  
**SG-3:** `FAIL`  
**Run:** `p6-multi-s10-20260819T082908.416321+0000-e44ef183ef75`  
**Execution commit:** `59fb24a0bb4d287ce47c55e3540af326a524cc0e` (`git_dirty=false`)

All 10 locked confirmation seeds have final statuses:

```text
PASS:               0
CHECKPOINT_INVALID: 4  (12,13,16,18)
PROFILE_FAILURE:    2  (14,15)
SOLVER_FAILURE:     4  (10,11,17,19)
```

Seeds 14 and 15 produced full state-eliminated matrices with eigenvalues `[1.8474,22.0066]` and `[1.7383,19.5849]`, respectively, but their minimum-eigendirection profiles failed locked fit quality. Maximum-direction fits passed. No seed formed a valid directional pair.

The 5×5 grid rule selects the first valid seed in ascending order. Because the valid set was empty, the selection function had no value and the grid is recorded as `NOT_APPLICABLE_NO_VALID_SEED`; using an invalid seed would violate the lock.

Manifest SHA256 verification, Figure 5 SVG parsing and Table 3 CSV checks passed. SG-3 requires 9/10 valid ordering agreements; observed value is 0/10, hence `FAIL`. No locked threshold, CG setting or profile rule was changed and the run was not repeated.

