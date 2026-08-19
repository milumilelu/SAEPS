# Amendment 004 — P8 operation-count aggregation

## Scope

Artifact-only correction after the single P8 cost run. The raw records already contain per-seed CG, JVP and VJP counts, but the first generated `summary.json` omitted their aggregate statistics.

## Permitted action

`scripts/12_finalize_cost_artifacts.py` verifies every raw-record SHA-256 against the original manifest, computes medians, and appends aggregate operation counts plus artifact provenance to the summary.

## Prohibited action

No training, SAEPS solve, frozen profile or reoptimized profile is rerun. No raw record, timing value, locked config, scientific gate or cost threshold is changed.
