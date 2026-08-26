# V4 Final Evidence Audit Report

> **HISTORICAL v4 EVIDENCE — not the current paper-facing conclusion.** See [`V5_FINAL_JCP_AUDIT_REPORT.md`](V5_FINAL_JCP_AUDIT_REPORT.md) for the V5 final audit. The historical results below are preserved unchanged.

## Audit outcome

`PASSED_WITH_SCIENTIFIC_LIMITATIONS`. Scientific conclusion: `PARTIALLY_SUPPORTED`.
Recommendation: `INVESTIGATE_NUMERICS`. Paper readiness:
`NOT_READY_FOR_FULL_JCP_CLAIM`.

All source JSON files were loaded and SHA256-recorded. The V4.2, V4.4 and
V4.5 permanent result audits pass; V4.6 confirmation seeds 105--114 remain
untouched; V4.7 and V4.8 integrity checks pass.

## Evidence ledger

| Node | Result | Planned/valid | Main quantitative evidence |
|---|---|---:|---|
| Burgers scalar V4.2 | SUPPORTED | 15/12 | 12 planned wins; median D 27.6363; median E_SAEPS 0.0750; p=0.000244141 |
| Allen--Cahn scalar V4.4 | SUPPORTED | 10/9 | 9 planned wins; median D 20.0065; median E_SAEPS 0.2786; p=0.00195312; profile 1/9 |
| Controlled mechanism V4.5 | NOT_SUPPORTED | 10/6 | 6 planned monotonic; valid median Spearman 1.000 |
| Two-parameter V4.6 | confirmation not tested | 2/1 held-out | engineering PASSED; held-out FAILED |
| Scalability V4.7 | PASSED | 5/5 | up to 100001 state parameters; largest solve 5.037s |
| Robustness V4.8 | descriptive | 60/52 | exact anchors 14/14 wins; wide valid 0/5 |

## Scientific judgment

The strongest reproducible result is narrow and specific: local state
elimination is dramatically closer than frozen-state curvature to the exact
finite-gamma scalar reduced Hessian on two PDEs and at the robustness anchor
cells. SAEPS still has non-negligible, PDE-dependent Gauss--Newton error: the
median relative error is about 7.5% on Burgers and 27.9% on Allen--Cahn, and
the Allen nonlinear-profile bridge passes only 1/9 valid seeds.

The full V4 claim is not established. The planned controlled gate is
`NOT_SUPPORTED` because only 6/10 centers are valid, despite perfect
monotonicity among valid seeds. Two-parameter confirmation was never
authorized after its held-out gate passed only 1/2. Width32 architecture has
0/5 valid centers, so its curvature hypothesis is untested. These are major
numerical-availability and scope limitations, not quantities that may be
removed from the denominator.

## Permissible claim

SAEPS captures most of the scalar state-adaptation reduction in tested local,
finite-damping settings and substantially improves on raw fixed-state
curvature, while retaining seed- and PDE-dependent Gauss--Newton error.

Do not claim universal controlled-mechanism validation, exact nonlinear-profile
equivalence, confirmed two-parameter geometry, or wide-architecture validity.
The next scientific work should address center availability and nonlinear
profile reliability under a new preregistered program; none of the closed V4
cohorts may be rerun or retuned.

## Source integrity

Machine-readable audit: `docs/evidence/v4_final_audit.json`. Every source hash
used by this report is stored in that file. This report does not supersede the
historical v2 `FINAL_VALIDATION_REPORT.md`.
