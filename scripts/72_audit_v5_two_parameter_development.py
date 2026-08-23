from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.two_parameter_development_audit import write_two_parameter_development_audit


if __name__ == "__main__":
    result = write_two_parameter_development_audit(Path(__file__).resolve().parents[1])
    print(json.dumps({key: result[key] for key in ["engineering_status", "binding_valid_count", "heldout_authorized", "forbidden_metrics_computed"]}, indent=2))
