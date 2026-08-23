from __future__ import annotations

import json
from pathlib import Path

from saeps.io_utils import write_json_atomic
from saeps.v5.final_audit import write_final_artifacts
from saeps.v5.final_validation import validate_v5_repository


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    audit = write_final_artifacts(root)
    validation = validate_v5_repository(root, require_final=True)
    write_json_atomic(root / "docs/evidence/v5_final_validation.json", validation)
    print(json.dumps({"audit_status": audit["audit_status"], "scientific_conclusion": audit["scientific_conclusion"], "validation": validation["status"]}, indent=2))
    raise SystemExit(0 if validation["status"] == "PASSED" else 1)
