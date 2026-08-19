"""Run the P8 cost-only benchmark on committed development seeds."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.p8_cost import run_cost_benchmark


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    summary = run_cost_benchmark(
        root / "configs/cost.yaml", root / "outputs/runs/p8_cost", root
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    raise SystemExit(0 if summary["engineering_gate"] == "PASSED" else 1)
