# Development decision log

- **2026-09-12 / RI-1 gamma grid:** The pasted goal and repository execution contract specify the six-point grid `gamma_alpha ∈ {1e-12,1e-10,1e-8,1e-6,1e-4,1e-2}` with `gamma = gamma_alpha * lambda_max(J_w^T J_w)`. The supplied package task document mentions a different relative exploratory grid. Because neither grid is locked for this new namespace, this implementation records the execution-contract grid as the current proposal and marks it `DEVELOPMENT_ONLY`; no confirmation run has used it.

- **2026-09-12 / RI-2 pilot:** The 24 planned PINN fits remain `NOT_STARTED` until a heat-equation PINN adapter records the required checkpoint, profile, cost and failure provenance. No surrogate is substituted.
