"""Adjudicate v4.6 recovery held-out binding gate."""

import hashlib
import json
from pathlib import Path


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    rows = []
    for seed in (115, 116):
        path = root / f"outputs/runs/v4_6_two_parameter/heldout/seed_{seed}/result.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        manifest = json.loads(path.with_name("manifest.json").read_text(encoding="utf-8"))
        rows.append({"seed": seed, "status": record["status"], "binding_valid": record["binding_valid"], "center": record["center"]["final"]["local_minimum_gate"], "solver": record["solver"]["status"] if record["solver"] else None, "exact": record["exact_hessian"]["gamma_matched"]["status"] if record["exact_hessian"] else None, "coupling": record["coupling"], "hash_matches": hashlib.sha256(path.read_bytes()).hexdigest() == manifest["result_sha256"]})
    checks = {"exact_fresh_seeds": [row["seed"] for row in rows] == [115, 116], "hashes": all(row["hash_matches"] for row in rows), "binding_2_of_2": sum(row["binding_valid"] for row in rows) == 2}
    audit = {"schema_version": 1, "phase": "V4_6_TWO_PARAMETER_RECOVERY_HELDOUT", "status": "PASSED" if all(checks.values()) else "FAILED", "checks": checks, "rows": rows, "confirmation_authorized": False, "excluded": ["D", "E_raw", "E_SAEPS", "eigenspectrum"]}
    path = root / "docs/evidence/v4_6_two_parameter_heldout.json"
    path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(audit, indent=2, sort_keys=True))
    raise SystemExit(0 if audit["status"] == "PASSED" else 1)
