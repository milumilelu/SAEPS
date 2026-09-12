# Failure audit

RI-0 confirms the finite-γ operator can report positive curvature for an exactly flat unanchored profile. This is a mathematical interpretation limit, not an implementation failure. Historical Phase-2 failure roots are summarized in `outputs/reliability_audit_v1/pilot/ri0/HISTORICAL_ROOT_AUDIT.csv`; source evidence remains under `docs/evidence/` and `outputs/runs/`.

Three versioned RI-2 development attempts are preserved. The original v3 run used a single data/noise stream and had 20/24 fit-qualified cases (B1 2/6). v5 separated the noise RNG and corrected B4 nuisance handling. Current v6 additionally records protocol terminal statuses and required unavailable-cost fields: 24/24 cases were computable, 23/24 fit-qualified, and one terminal row is `CHECKPOINT_INVALID`; no seed was silently retried or replaced.

The analytic B1–B6 profiles and independent finite-difference physical reference pass their declared development checks. The fixed gamma-path decision analysis nevertheless abstains or flags all B2–B4 cases and does not demonstrate a lower false-reliable risk than RAW at matched coverage. PINN-reoptimised profiles, bootstrap calibration, and B5/B6 PINN intervention remain unimplemented, so G2/G4/G5 are not passed and confirmation remains stopped.

The denominator registry retains all 24 planned rows as `NOT_STARTED` administrative entries; terminal observed statuses are merged from per-run manifests into the current v6 `summary.json` and `PILOT_RESULTS.json`. This preserves the planned denominator without misrepresenting observed outcomes.

Repository-wide validation was rerun: new reliability tests pass, while the pre-existing V5 validator fails because user-deleted historical files (including `V5_JCP_MINIMAL_PROTOCOL.md` and `FINAL_VALIDATION_REPORT.md`) are absent. Those deletions were not restored or altered.
