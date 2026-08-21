# v4.6 Two-Parameter Exact-Geometry Development Contract

The coupled reaction-diffusion benchmark and two log-parameter coordinates are inherited unchanged from the immutable P6 lock. Historical P6 remains `SG-3 FAIL` and cannot be reaggregated.

- Engineering seeds: `100--102`.
- Held-out development seeds: `103--104`, inactive until executable freeze.
- Untouched confirmation seeds: `105--114`, inactive until independent lock and authorization.
- Finite damping: inherited `gamma_alpha=1e-8`.
- Gold standard: exact full-objective finite-gamma Schur reduction.
- Curvature solver: parameter-RHS-only two-pass scaled-LSQR, independently checked against explicit GN.
- Center: deterministic multistart GN plus exact first/second-order state-local-minimum gate.

Development selection may use center validity, state RMSE marked validation-only, two-column solver validity, exact-reference validity, nontrivial coupling and cost. `D`, `E_raw`, `E_SAEPS`, favorable generalized eigenvalues and plot appearance cannot select settings.
