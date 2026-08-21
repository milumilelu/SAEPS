"""Aggregate and validate practical scalability records."""

import hashlib
import json
from pathlib import Path


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    rows = []
    for checkpoint in range(120, 125):
        path = root / f"outputs/runs/v4_7_scalability/checkpoint_{checkpoint}/result.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        manifest = json.loads(path.with_name("manifest.json").read_text(encoding="utf-8"))
        rows.append({**record, "hash_matches": hashlib.sha256(path.read_bytes()).hexdigest() == manifest["result_sha256"]})
    checks = {"exact_checkpoints": [row["checkpoint"] for row in rows] == list(range(120,125)), "all_pass": all(row["status"] == "PASS" for row in rows), "hashes": all(row["hash_matches"] for row in rows), "covers_1e2_to_1e5": rows[0]["state_parameter_count"] <= 101 and rows[-1]["state_parameter_count"] >= 100001, "small_explicit_audits": all(row["explicit_relative_error"] is not None and row["explicit_relative_error"] <= 1e-6 for row in rows[:2])}
    audit = {"schema_version": 1, "phase": "V4_7_SCALABILITY", "status": "PASSED" if all(checks.values()) else "FAILED", "checks": checks, "rows": [{key: row[key] for key in ["checkpoint","state_parameter_count","residual_count","cg_iterations","verified_relative_residual","explicit_relative_error","JVP_count","VJP_count","solve_seconds","elapsed_seconds","status"]} for row in rows], "scope_limit": "function-preserving padded controlled-PINN checkpoint; cost-only, not scientific curvature confirmation"}
    out = root / "docs/evidence/v4_7_scalability.json"
    out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(audit, indent=2, sort_keys=True))
    raise SystemExit(0 if audit["status"] == "PASSED" else 1)
