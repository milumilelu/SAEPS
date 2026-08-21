# Amendment 019 — v4.7 Practical Scalability

**Date:** 2026-08-21  
**State:** cost-only engineering authorization

V4.6 stops before confirmation because its fresh held-out center gate passes only 1/2. This amendment does not override that stop. It activates the independent practical-scalability audit on checkpoints `120--124`.

The audit uses the real controlled parabolic PINN residual and a function-preserving width expansion of a trained width-25 checkpoint. Added neurons have deterministic hidden weights and zero output weights, so the represented state initially remains identical while state-parameter dimension increases. This is a controlled operator-scaling experiment, not scientific curvature confirmation; stationarity and comparative claims are excluded.

Dimensions are fixed near `10^2,10^3,10^4,5*10^4,10^5`. Gamma is `1e-2` times a 20-step matrix-free power estimate of the largest normal-operator eigenvalue. The parameter RHS alone is solved by matrix-free CG with tolerance `1e-10`, acceptance `1e-8` and maximum 500 iterations. Explicit Jacobian cross-check is required only through dimension 1001. Every checkpoint records wall time, iterations, verified residual and JVP/VJP counts.
