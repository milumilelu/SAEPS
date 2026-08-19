# P7 Robustness & Architecture — Acceptance Evidence

**Engineering gate:** `PASSED / completion_mode: FULL`  
**Scientific gate:** `DESCRIPTIVE_ONLY`  
**Run:** `p7-robustness-s10-20260819T084233.286983+0000-fa8846c72a36`  
**Execution commit:** `8333411bc57a8e2ee1918c43a61164af5232f94e` (`git_dirty=false`)

All 55 newly planned runs have final statuses:

```text
PASS:               43
CHECKPOINT_INVALID:  2
SOLVER_FAILURE:     10
```

The locked 45-run noise × observation-fraction matrix is complete. Valid counts were 4/5, 3/5 and 4/5 at noise 0 for fractions 1, 0.5 and 0.25; 5/5, 4/5 and 2/5 at noise 0.01; and 5/5, 4/5 and 4/5 at noise 0.05. Thus failure frequency generally increased under observation sparsity, but it was not monotone in noise level. Across valid cells, median eta decreased as fraction fell from 1 to 0.25: approximately 0.0347 to 0.0158 at noise 0, 0.0323 to 0.0165 at noise 0.01, and 0.0324 to 0.0145 at noise 0.05. Every reported median effect `Fraw-Fse` was positive.

Architecture transfer yielded 5/5 valid narrow runs (median eta 0.0396) and 3/5 valid wide runs (median eta 0.0328). The immutable nominal P5 run supplied all 10 locked seeds by reference, with eta computable for 9/10 records and median 0.0335; P5 was not rerun.

Ten failures were locked-tolerance CG failures and two were checkpoint-gate failures. The strongest observed failure concentration was the noise 0.01/fraction 0.25 cell (2/5 valid); wide architecture also had two CG failures. These are descriptive failure boundaries, not a post hoc scientific gate. No threshold, gamma, retry rule, architecture definition or locked config was changed.

Manifest SHA-256 verification passed for all 55 records. The CSV summary reports effect, raw/state-eliminated curvature, eta, stationarity and validation RMSE for every condition.
