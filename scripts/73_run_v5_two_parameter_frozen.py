from __future__ import annotations

import argparse
import json
from pathlib import Path

from saeps.v5.two_parameter_frozen import run_two_parameter_frozen_cohort


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["heldout", "confirmation"], required=True)
    arguments = parser.parse_args()
    rows = run_two_parameter_frozen_cohort(Path(__file__).resolve().parents[1], arguments.role)
    print(json.dumps({"role": arguments.role, "terminal_records": len(rows), "binding_valid": sum(row["binding_valid"] for row in rows)}, indent=2))
