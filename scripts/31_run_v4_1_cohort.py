"""Run one registered v4.1 development cohort."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.v41.pipeline import run_v41_cohort


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True, choices=["ENGINEERING_INTEGRATION", "HELDOUT_DEVELOPMENT"])
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = run_v41_cohort(
        arguments.role,
        root / "configs/v4_1/post_confirmation_development.yaml",
        root / "outputs/runs/v4_1_post_confirmation_development",
        root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
