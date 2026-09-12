# Failure audit

RI-0 confirms the finite-γ operator can report positive curvature for an exactly flat unanchored profile. This is a mathematical interpretation limit, not an implementation failure. Historical Phase-2 failure roots are summarized in `outputs/reliability_audit_v1/pilot/ri0/HISTORICAL_ROOT_AUDIT.csv`; source evidence remains under `docs/evidence/` and `outputs/runs/`.

The RI-2 development pilot executed each of the 24 declared cases exactly once. All 24 produced computable diagnostic matrices and independent analytic observation-FIM artifacts. B1 had only 2/6 fit-qualified cases; B2–B4 had 6/6. The predeclared 5/6-per-benchmark availability gate therefore failed. This is classified as a training/centre availability limitation. Profiles were not implemented (`PROFILE_ELIGIBLE=0/24`), so confirmation and intervention were not authorized. No seed was silently retried or replaced.

The denominator registry retains all 24 planned rows as `NOT_STARTED` administrative entries; terminal observed statuses are merged from per-run manifests into `outputs/reliability_audit_v1/pilot/ri2_full_v3/summary.json` and `PILOT_RESULTS.json`. This preserves the planned denominator without misrepresenting the observed pilot.

Repository-wide validation was rerun after this increment: new analytic and RI-2 tests pass, while the pre-existing V5 validator fails because user-deleted historical files (including `V5_JCP_MINIMAL_PROTOCOL.md` and `FINAL_VALIDATION_REPORT.md`) are absent. This is recorded as I-UPGRADE-002; those deletions were not restored or altered.
