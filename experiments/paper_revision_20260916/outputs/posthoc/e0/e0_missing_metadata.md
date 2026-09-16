# E0 missing metadata and unresolved traces

Frozen evidence: `jcp-submission-v1` (`jcp-submission-v1`).

## Available and traced

- Scalar cohorts read directly from run records; every record hash is listed in
  `e0_source_audit.json` under `scalar.input_sha256`.
- Two-parameter cohort read from the confirmation report with all 10 planned seeds present.
- Cost record read from raw run output for `outputs/runs/v5/residual_scalability/n_100001/m_3413`.

## Not available from the frozen archive

- **Scalar state tensors, observation sets and residuals.** The scalar posthoc records
  store parameter and state matrix blocks only. Consequences: the E1 identity cannot be
  re-derived by autograd for scalar centres (block-level self-consistency only), and E2
  state refinement is `NOT_AVAILABLE` for the prescribed scalar queue
  (Burgers 55/60/69; Allen-Cahn 75/79/84).
- **Original scalar centre tensors.** `outputs/runs/v5/checkpoints/burgers`,
  `.../allen_cahn` hold `V5_RECONSTRUCTED_ENGINEERING_CHECKPOINT` artifacts with
  `historical_tensor_identity_claimed: false`. They are engineering reconstructions, not
  the archived confirmation tensors, so they cannot stand in for the original reference.
- **Native peak tensor memory.** The scalability record reports
  `peak_memory_unavailable_reason = 'unavailable_native_cpu_tensor_peak'`.
  No native tensor peak is recorded, and process RSS is not a substitute.

## Deliberately not reconstructed

- No historical seed was re-run, and no failed seed was replaced.
- No scalar state tensor was regenerated to fill the E1/E2 gap.

## Denominator notes

- Scalar evaluation denominators are the surviving binding-valid counts, as recorded:
  Burgers 12/15,
  Allen-Cahn 9/10,
  two-parameter 8/10.
- Two-parameter invalid seeds are non-wins in the planned denominator; the 8/10 result and
  the `INCONCLUSIVE` scientific status are unchanged.
- Architecture robustness: the `wide` group has 0 binding-valid centres out of
  5 planned.
