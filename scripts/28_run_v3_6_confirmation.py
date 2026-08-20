"""Execute the locked v3.6 scalar confirmation exactly once."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v36.pipeline import run_v36_confirmation


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = run_v36_confirmation(
        root / "configs/v3_6/locked_scalar_confirmation.yaml",
        root / "outputs/runs/v3_6_scalar_confirmation",
        root,
        root / "configs/v3_6/EXECUTION_AUTHORIZATION.json",
        root / "docs/evidence/PRE_CONFIRMATION_AUDIT.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))

