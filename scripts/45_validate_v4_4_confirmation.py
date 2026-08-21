"""Validate the permanently closed v4.4 Allen--Cahn result."""

import json
from pathlib import Path

from saeps.v44.result_validation import validate_v44_result


if __name__ == "__main__":
    result = validate_v44_result(Path(__file__).resolve().parents[1])
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASSED" else 1)
