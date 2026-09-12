# reliability_audit_v1

This namespace implements the first, development-only increment of the reliability-aware identifiability program. It is deliberately separate from historical SAEPS/V2-V5 outputs.

Completed:

- RI-0 independent NumPy counterexamples and objective/unit audit;
- RI-1 analytic heat-equation observation map, rank, singular-value and reproducible-noise checks;
- permanent PyTorch regression tests for finite-gamma versus zero-damping curvature, parameter combinations, B1-B6 ranks, coordinate/damping dependence and collocation duplication;
- proposed protocol, literature audit, claim ledger and paper strategy.

Not completed: the 24-case RI-2 heat-equation PINN pilot. All 24 planned records remain `NOT_STARTED` in `run_plan.json`; no PINN reliability or uncertainty claim is made.
