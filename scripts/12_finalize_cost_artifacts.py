"""Add operation-count aggregates to the single immutable P8 run."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.p8_finalize import finalize_cost_artifacts


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    runs = sorted((root / "outputs/runs/p8_cost").glob("*/manifest.json"))
    if len(runs) != 1:
        raise SystemExit(f"expected exactly one P8 run, found {len(runs)}")
    summary = finalize_cost_artifacts(runs[0].parent, root)
    print(json.dumps(summary["aggregate_operation_counts"], indent=2, sort_keys=True))
