# P8 Computational Cost — Acceptance Evidence

**Engineering gate:** `PASSED`  
**Scientific gate:** `DESCRIPTIVE_ONLY`  
**Run:** `p8-cost-s0-20260819T085547.064222+0000-b80f00209a91`  
**Execution commit:** `45d28c5724730dd544ee6c444b96a8b7baf5dba2` (`git_dirty=false`)  
**Artifact finalization commit:** `af533f5ec4c2c968aae89903d42ee06073f962d5` (`git_dirty=false`)

Three cost-only development seeds `[0,1,2]` completed actual end-to-end training, SAEPS, seven-point frozen profiling and seven independently reoptimized profile points. No confirmation seed was rerun and the cost records do not enter a scientific gate.

Median wall-clock costs on the recorded Intel CPU, float64 backend were:

```text
training:                 3.7658554 s
SAEPS:                    5.2209698 s
frozen profile:           0.0049640 s
reoptimized profile:      9.1248596 s
```

The required ratio `T_reoptimized_profile/T_SAEPS` is 2.0483 as the median of paired per-seed ratios. The independently computed ratio of median times is 1.7477. SAEPS was therefore faster than full nonlinear profiling in this small CPU benchmark, but only by roughly a factor of two; the evidence does not support an order-of-magnitude acceleration claim.

Median operation counts were CG iterations `[256,293]` for the two solves (549 total), JVP count 556 and VJP count 555. Native peak CPU tensor memory is not reliably exposed by this PyTorch backend, so peak memory is `null` with an explicit reason rather than a misleading Python-allocation proxy.

All 21 reoptimization points completed their stopping rules. Two of three reoptimized quadratic fits failed the locked fit-quality gate, which does not invalidate the measured cost of executing the full algorithm but confirms the numerical limitation already observed in P5. Manifest hashes, the three-row CSV and Figure 6 SVG were validated. The aggregate-count correction was artifact-only under Amendment 004 and did not rerun or alter any raw measurement.
