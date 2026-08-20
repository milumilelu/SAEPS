"""Validate frozen v3.6 raw-to-aggregate evidence without changing it."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v36.result_validation import validate_v3_6_result


if __name__ == "__main__":
    result = validate_v3_6_result(Path(__file__).resolve().parents[1])
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASSED" else 1)

