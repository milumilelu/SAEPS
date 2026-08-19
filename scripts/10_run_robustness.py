"""Run the locked P7 descriptive experiments."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.p7_robustness import run_robustness


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = run_robustness(
        root / "configs/locked/scalar.yaml",
        root / "configs/locked/robustness.yaml",
        root / "outputs/runs/p7_robustness",
        root,
    )
    print(
        json.dumps(
            {
                key: result[key]
                for key in [
                    "run_id",
                    "engineering_gate",
                    "completion_mode",
                    "planned_new_runs",
                    "completed_new_runs",
                    "status_counts",
                ]
            },
            indent=2,
            sort_keys=True,
        )
    )
    raise SystemExit(0 if result["engineering_gate"] == "PASSED" else 1)
