"""Run the one-shot V5.1 finite-gamma descriptive audit."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.finite_gamma import run_finite_gamma_audit


if __name__ == "__main__":
    rows = run_finite_gamma_audit(Path(__file__).resolve().parents[1])
    print(json.dumps({"terminal_records": len(rows), "pass_records": sum(row["status"] == "PASS" for row in rows)}, indent=2))
