"""Validate the V5.0 freeze without running scientific experiments."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.governance import validate_v5_governance


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = validate_v5_governance(root)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASSED" else 1)
