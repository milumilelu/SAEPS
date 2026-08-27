# P2 paper-facing wording recommendations

Scope: presentation recommendations only. No manuscript or scientific adjudication was changed.

## Comparative evidence

- Replace informal “wins all” phrasing with: “SAEPS improved exact-reference accuracy at all 12 Burgers binding-valid checkpoints (12/15 planned) and all 9 Allen--Cahn binding-valid checkpoints (9/10 planned).”
- Use “one-sided exact binomial sign test” consistently. Preserve the frozen values: Burgers `p=0.000244140625`; Allen--Cahn `p=0.001953125`.
- Always report both valid and planned denominators. Invalid planned records remain planned non-wins.
- Define an exact-Hessian anchor as a binding-valid noise/sparsity condition for which the saved exact finite-damping reduced-Hessian comparison is available. State: “14/15 planned exact-Hessian anchors were valid; SAEPS improved exact-reference accuracy at all 14 valid anchors.”

Tracked occurrences needing author review include `V5_JCP_MINIMAL_PROTOCOL.md` (lines 26, 33, 45, 47), `V4_FINAL_AUDIT_REPORT.md` (lines 17, 18, 22), `V5_FINAL_JCP_AUDIT_REPORT.md` (lines 13--15), and historical task/decision/evidence reports. Historical records should not be rewritten; manuscript prose should adopt the wording above. No literal “wins all” string was found in tracked Markdown/TeX/RST files.

## Damping and scalability

- Describe the finite-gamma sweep as descriptive sensitivity evidence. At the smallest tested `alpha=1e-10`, only `2/6` planned records passed; retain all four failures in the denominator.
- Replace “27 conditions” with: “9 dimension combinations, each repeated three times, for 27 verified solves.”
- Timing wording: “Reported iterative solve time includes JVP/VJP applications but excludes one-time shared condition setup.” Do not combine setup and solve time without relabelling.
- State the tested extent (`n_theta` up to 100001; residual count `m` up to 3413) and retain the cost/engineering-only scope.

## Variable-projection positioning

Present P3 only as `POSTHOC_NONBINDING_BASELINE_ANALYSIS`. The undamped GN pseudoinverse is cutoff-sensitive, and none of the 21 V3-valid centers admits the ordinary exact gamma=0 classical Schur complement under the frozen historical positive-definiteness rule. A defensible factual positioning is that finite damping provides a regularized reduced geometry; it is not evidence that undamped variable projection is a preregistered comparator or that a nonlinear unregularized profile Hessian exists at these centers.
