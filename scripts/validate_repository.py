"""Run the SAEPS v2.0 end-to-end repository audit."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.repository_validation import validate_repository


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = validate_repository(root)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASSED" else 1)
