# Identifiability Pilot Report (RI-2)

**Status: NOT EXECUTED.** The supplied research package explicitly states that the proposed PINN experiments were not implemented. RI-0 (independent analytic counterexamples and historical root audit) and RI-1 (analytic heat observation reference) are complete in this workspace. The 24-run RI-2 plan is recorded in `experiments/reliability_audit_v1/run_plan.json`; all 24 records remain `NOT_STARTED` and are retained in the denominator.

The analytic gate is currently satisfied: B1/B2 have rank one with B2's singular value much smaller than B1; B3 and B4 have rank-one confounding; B5 and B6 have rank two after the declared intervention. The independent NumPy check report contains seven passing algebraic checks. These are reference checks, not PINN training results.

No claim about SAEPS reliability, parameter recovery, uncertainty calibration, or observation-design benefit is supported by this pilot. A PINN pilot requires a heat-equation residual/training adapter that records separate data and optimizer seeds, checkpoint validity, `F_raw`, finite-gamma `F_gamma`, independent observation FIM, profile eligibility, and full failure provenance. Until that adapter is implemented and tested, the correct decision is `PROTOCOL_STOP_PENDING_IMPLEMENTATION`, rather than silently substituting an easier surrogate.

The next authorized increment is to implement the adapter in the new `reliability_audit_v1` namespace, run the 24 predeclared B1-B4 cases once, and apply the frozen per-benchmark availability rule (at least 5/6 fit-qualified cases) without seed replacement or threshold changes.
