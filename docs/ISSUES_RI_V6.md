# RI-v6 correction-layer issues

## RI-V6-P0-001 — Archived RI-2 decision path used oracle/reference inputs

Classification: `implementation failure` (confirmed). The new correction
layer rejects truth and reference-FIM fields at the `SAEPS_ONLY` input boundary
and keeps physical plug-in and oracle reference interfaces separate. Archived
records remain unchanged and are not reclassified in place.

## RI-V6-P0-002 — Boundary and closure semantics were not auditable

Classification: `implementation failure` (confirmed). The LBFGS closure no
longer mutates parameters after backpropagation; projected terminal parameters
are reported as boundary/KKT candidates and cannot be interior fit-qualified.

## RI-V6-P0-003 — Physical residual and reference threshold were mis-specified

Classification: `implementation failure` (confirmed). New development code
provides the ratio-form heat residual with explicit scale and optional
normalized quadrature. The written reference rule is `noise_scale * 0.01`;
the archived difference `1.579809e-4` consequently remains a failure. Legacy
outputs are not overwritten.

## RI-V6-P0-004 — Nonlinear profile and comparative scientific value remain open

Classification: `scientific failure` / `UNTESTED`. Profile execution and a
matched RAW–SAEPS risk comparison were not implemented in P0. No claim of
profile success or incremental reliability is made; P1/P2 remain stopped.
