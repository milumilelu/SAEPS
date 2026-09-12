# Failure audit

RI-0 confirms the finite-γ operator can report positive curvature for an exactly flat unanchored profile. This is a mathematical interpretation limit, not an implementation failure. Historical Phase-2 failure roots are summarized in `outputs/reliability_audit_v1/pilot/ri0/HISTORICAL_ROOT_AUDIT.csv`; source evidence remains under `docs/evidence/` and `outputs/runs/`.

RI-2 is `NOT_STARTED`, so no training, solver, profile, or data failures are being hidden. The planned denominator is 24 and every record is explicitly `NOT_STARTED` in `experiments/reliability_audit_v1/run_plan.json`.

Repository-wide validation was rerun after this increment: new analytic tests pass, while the pre-existing V5 validator fails because user-deleted historical files (including V5_JCP_MINIMAL_PROTOCOL.md and FINAL_VALIDATION_REPORT.md) are absent. This is recorded as I-UPGRADE-002; those deletions were not restored or altered.

RI-2 pilot result: 24/24 diagnostic computations completed; B1 has only 2/6 fit-qualified cases, while B2-B4 are 6/6. The predeclared 5/6-per-benchmark availability gate therefore fails. This is classified as training/centre availability limitation; no confirmation run is authorized.
