# v4.6 Two-Parameter Exact-Geometry Development Contract

The coupled reaction-diffusion benchmark and two log-parameter coordinates are inherited unchanged from the immutable P6 lock. Historical P6 remains `SG-3 FAIL` and cannot be reaggregated.

- Engineering seeds: `100--102`.
- Original held-out seeds `103--104` were invalidated before a freeze commit by I-031; seed103 is retained dirty-provenance evidence and seed104 is not run. Fresh recovery held-out seeds are `115--116` under Amendment 018.
- Untouched confirmation seeds: `105--114`, inactive until independent lock and authorization.
- Finite damping: inherited `gamma_alpha=1e-8`.
- Gold standard: exact full-objective finite-gamma Schur reduction.
- Curvature solver: parameter-RHS-only two-pass scaled-LSQR, independently checked against explicit GN.
- Center: deterministic multistart GN plus exact first/second-order state-local-minimum gate.

Development selection may use center validity, state RMSE marked validation-only, two-column solver validity, exact-reference validity, nontrivial coupling and cost. `D`, `E_raw`, `E_SAEPS`, favorable generalized eigenvalues and plot appearance cannot select settings.

The inherited width-12 screening attempt remains a saddle despite passing the gradient gate. Architecture development therefore follows the committed fallback `12 -> 8 -> 6` on screening seed100. A smaller width may be selected only if the exact center, validation-only RMSE, solver, exact-reference and coupling gates pass; comparative errors remain excluded.
