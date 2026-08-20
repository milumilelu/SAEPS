"""Run one v3.5 cohort."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.v35.pipeline import run_v35_cohort


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--role",
        required=True,
        choices=[
            "RETROSPECTIVE_DIAGNOSTIC",
            "ENGINEERING_SELECTION",
            "HELDOUT_DEVELOPMENT",
        ],
    )
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = run_v35_cohort(
        arguments.role,
        root / "configs/v3_5/diagnostic_engineering.yaml",
        root / "outputs/runs/v3_5_second_order_engineering",
        root,
    )
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "role": result["role"],
                "seeds": result["seeds"],
                "record_statuses": {
                    str(row["seed"]): row["status"] for row in result["records"]
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
