# V4 Final Repository Validation

The final engineering audit is `PASSED_WITH_SCIENTIFIC_LIMITATIONS`.

- Full actual test suite: 80 passed, 0 failed; 18 PyTorch JIT deprecation
  warnings.
- V4.2 and V4.4 immutable confirmation validators: passed.
- V4.5 engineering and held-out validators: passed; its permanently closed
  confirmation remains `NOT_SUPPORTED`.
- V4.6 engineering validator: passed. Held-out validator returns its expected
  scientific failure because only 1/2 frozen seeds is binding-valid; this is
  not an audit malfunction.
- V4.7 scalability validator: passed.
- Historical end-to-end repository validator: passed.
- V4.8 raw manifests and 60-run aggregation: passed.
- Regenerating the current V4 report and machine audit is byte-identical.

The current scientific conclusion is `PARTIALLY_SUPPORTED`; the recommendation
is `INVESTIGATE_NUMERICS`. The incomplete two-parameter confirmation and failed
wide-network center availability remain visible and prevent a full JCP claim.
