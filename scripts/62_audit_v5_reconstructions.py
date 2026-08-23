"""Validate and aggregate the fixed V5 engineering reconstructions."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.reconstruction_audit import write_reconstruction_audit


if __name__ == "__main__":
    result = write_reconstruction_audit(Path(__file__).resolve().parents[1])
    print(json.dumps({key: result[key] for key in ["status", "attempted_count", "pass_count", "retry_count", "replacement_count"]}, indent=2))
