# P9 Paper Artifacts & Final Audit — Acceptance Evidence

**Engineering gate:** `PASSED`  
**Artifact-build implementation commit:** `16b290f0c58b9cc0877c0c74603ff3da0396eae4`  
**Final conclusion:** `PARTIALLY_SUPPORTED`  
**Recommendation:** `INVESTIGATE_NUMERICS`

The required commands both exited with code 0:

```text
python scripts/09_build_paper_artifacts.py
python scripts/validate_repository.py
```

The builder produced Figures 1–6, Tables 1–3, an aggregate summary, 11 supplementary files, a SHA-256 artifact manifest and `FINAL_VALIDATION_REPORT.md`. The validator executed the 30-test suite and passed all 11 audit groups: locked config hashes/lock-commit bytes, raw manifests, seed/run completeness, raw-to-aggregate equality, bootstrap lineage, cost lineage, provenance, paper artifacts, failed-run reporting and scientific-gate mapping.

The accepted workload is complete: P2 50/50 evaluations, P5 10/10 seeds, P6 10/10 seeds, P7 55/55 new runs and P8 3/3 cost-only runs. All 56 invalid/failed raw records across these accepted runs are retained in the supplementary failure table. Scientific FAIL/PARTIAL results do not cause an engineering failure.

The conclusion is deliberately limited. P1 and P3 numerical components passed, and the only valid P5 pair favored SAEPS, but SG-1 failed, P5 had only 1/10 valid pairs, SG-3 failed with 0/10 valid pairs, and unresolved stationarity/CG/profile-fit problems dominate the evidence. Therefore broad publication claims are not justified under v2.0; numerical investigation must occur under a new protocol version, without retuning the locked confirmation split.
