"""Binding-only validation of v4.6 engineering."""

import hashlib
import json
from pathlib import Path


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    rows = []
    for seed in (100, 101, 102):
        path = root / f"outputs/runs/v4_6_two_parameter/architecture_w6/seed_{seed}/result.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        manifest = json.loads(path.with_name("manifest.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append({"seed": seed, "binding_valid": record["binding_valid"], "center": record["center"]["final"]["local_minimum_gate"], "state_rmse_validation_only": record["training"]["state_rmse"], "solver": record["solver"]["status"], "max_solver_residual": max(record["solver"]["verified_residuals"]), "explicit_error": record["solver"]["matrix_free_vs_explicit_relative_error"], "exact": record["exact_hessian"]["gamma_matched"]["status"], "coupling": record["coupling"], "hash_matches": digest == manifest["result_sha256"]})
    checks = {"binding_3_of_3": sum(row["binding_valid"] for row in rows) == 3, "hashes": all(row["hash_matches"] for row in rows), "nontrivial_coupling_3_of_3": all(row["coupling"] >= 0.1 for row in rows), "solver_gate": max(row["max_solver_residual"] for row in rows) <= 1e-8 and max(row["explicit_error"] for row in rows) <= 1e-6, "exact_gate": all(row["exact"] == "PASS" for row in rows)}
    audit = {"schema_version": 1, "phase": "V4_6_TWO_PARAMETER_ENGINEERING", "status": "PASSED" if all(checks.values()) else "FAILED", "checks": checks, "rows": rows, "excluded": ["D", "E_raw", "E_SAEPS", "favorable_eigenvalues", "figure_appearance"]}
    out = root / "docs/evidence/v4_6_two_parameter_engineering.json"
    out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(audit, indent=2, sort_keys=True))
    raise SystemExit(0 if audit["status"] == "PASSED" else 1)
