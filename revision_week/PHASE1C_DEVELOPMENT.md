# Prospective development authorization

The user's request “你试试1、2、3” authorizes the three proposed development
checks. It does not reopen V5 confirmation or retroactively modify Phase 1B.
Use this isolated worktree; preserve the unrelated changes in the original
main checkout. No training, new seeds or automatic push in this experiment.

Commit this code/config and unit tests before measurement. The executable
records its commit, hashes of its dependencies, and all day1/day2/correction
outputs before workers start. Each of two roots and the 25-record matrix audit
has one immutable attempt, at most 300 seconds; total process budget is 1800
seconds. No retry. An interrupted/failed root retains available raw outputs.

1. Polish the 12 previously saved strict start/candidate states with up to eight
   SPD Newton steps and twelve fixed Armijo halvings, using the unchanged sum
   objective, anchor, gamma and data. Keep the normalized gradient gate 1e-8;
   internal target 1e-10. At objective roundoff, require gradient halving before
   taking a step. Record original LBFGS iteration/evaluation counters and every
   Newton state. A fixed mean normalization is preserved, not relabeled as the
   residual-relative stationarity convention of other protocols.
2. At each valid polished common start recompute four curvatures, common gradient
   and GN predictor. Use 0.1 times each shifted raw step, capped at 0.1; one
   candidate per method, no radius search. All candidates use the same LBFGS
   plus Newton procedure. Acceptance needs SPD, gradient gate and decrease above
   Armijo plus local gradient-energy error estimate. This estimate is diagnostic,
   not a global branch or objective-error certificate. Report paired SO-GN
   differences with a numerical resolution estimate; parameter truth is posthoc.
   This is a scalar discrimination test. No independent two-parameter center is
   introduced or selected from confirmation results.
3. Replay the unchanged SO-ADAPT endpoint on 21 matrices; retain 4 unavailable
   records. Use eight diagonal-PCG steps only to estimate terminal defect energy,
   not to update Z or change its original stopping. The identity
   q = 2 d^T w - w^T A w + r^T A^-1 r gives the interval [lower, lower+||r||²/mu].
   Keep the numerical dense mu and charge spectrum, estimator and reference
   separately. Relative estimate is U/(|F|-U). Oracle energy only validates after
   fixed estimator execution; it never selects an iteration or method.

Commands use the existing SAEPS/.venv/Scripts/python.exe:

    python -m pytest -q revision_week/test_p1c_development.py revision_week/test_p1b_correction.py revision_week/test_core.py
    python revision_week/p1c_development.py run
    python scripts/validate_repository.py

All evidence stays development-only even if positive. Any scientific failure
ends this fixed run rather than triggering a search for favorable settings.
