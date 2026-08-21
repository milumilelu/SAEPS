# Amendment 020 — V4.8 Paired Robustness

**Date:** 2026-08-21  
**State:** locked descriptive execution authorization

V4.2 and V4.4 remain permanently closed. V4.5 and V4.6 negative or
incomplete findings remain unchanged. This amendment opens only the fresh
paired robustness namespace reserved by Amendment 014.

## Planned data

- noise/sparsity seeds: `130--134`, paired across all nine cells;
- noise levels: `0.0`, `0.01`, `0.05` times the observation standard deviation;
- observation fractions: `1.0`, `0.5`, `0.2`;
- exact finite-gamma reduced Hessian anchors: `(0.0, 1.0)`, `(0.01, 0.5)`,
  `(0.05, 0.2)`;
- architecture seeds: `135--139`, paired across widths `8`, `16`, `32`.

Every planned run records center status, parameter-only explicit reference,
matrix-free curvature-solver status, `F_raw`, `F_se`, retained fraction
`eta`, timing, and failure reason. Anchor cells additionally require the exact
finite-gamma reduced-Hessian node. Score/residual right-hand sides are not
binding and are not needed for this curvature-only stress test.

## Frozen semantics

The center policy, gamma, two-pass scaled-LSQR refinement, explicit agreement
threshold, exact gold standard, and finite-value rules are inherited without
change from the protected V3.6 protocol through the V4.1 execution-semantic
repair. A non-anchor run is binding-valid only when center, parameter reference,
curvature solver and finite curvature nodes pass. An anchor also requires the
exact-reference node.

This phase is descriptive. It has no positive-result gate and may not modify
the method, thresholds, conditions, seeds, or prior claims. Failed runs remain
in their paired planned denominators. Execution is one shot per family/seed;
replacement and selective rerun are forbidden.
