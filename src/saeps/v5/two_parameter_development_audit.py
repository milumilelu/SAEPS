"""Audit the V5.3A 3/3 center-only development gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from saeps.io_utils import write_json_atomic
from saeps.v5.governance import sha256_file
from saeps.v5.two_parameter_development import SEEDS


def build_two_parameter_development_audit(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    rows = []
    sources = []
    for seed in SEEDS:
        path = root / f"outputs/runs/v5/two_parameter/development/seed_{seed}/result.json"
        if not path.is_file():
            raise ValueError(f"missing V5.3A seed: {seed}")
        record = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "seed": seed,
                "status": record["status"],
                "binding_valid": record["binding_valid"],
                "center_status": record["center"]["final"]["local_minimum_gate"],
                "solver_status": (record["solver"] or {}).get("status"),
                "exact_status": (record["exact_hessian"] or {}).get("gamma_matched", {}).get("status"),
                "coupling": record["coupling"],
                "scientific_comparison": record["scientific_comparison"],
                "selection_forbidden_metrics_computed": record[
                    "selection_forbidden_metrics_computed"
                ],
            }
        )
        sources.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)})
    valid = sum(row["binding_valid"] for row in rows)
    return {
        "schema_version": 1,
        "phase": "V5_3A_TWO_PARAMETER_DEVELOPMENT",
        "engineering_status": "PASSED" if valid == 3 else "FAILED",
        "binding_valid_count": valid,
        "planned_count": 3,
        "heldout_authorized": valid == 3,
        "forbidden_metrics_computed": any(
            row["selection_forbidden_metrics_computed"] for row in rows
        ),
        "rows": rows,
        "source_records": sources,
    }


def write_two_parameter_development_audit(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    audit = build_two_parameter_development_audit(root)
    write_json_atomic(root / "docs/evidence/v5/V5_TWO_PARAMETER_DEVELOPMENT_AUDIT.json", audit)
    lines = [
        "# V5.3A Two-Parameter Development Audit",
        "",
        f"- Engineering status: `{audit['engineering_status']}`",
        f"- Binding-valid: `{audit['binding_valid_count']}/3`",
        f"- Held-out authorized: `{str(audit['heldout_authorized']).lower()}`",
        f"- Forbidden comparative metrics computed: `{str(audit['forbidden_metrics_computed']).lower()}`",
        "",
        "| Seed | Status | Center | Solver | Exact | Coupling |",
        "|---:|---|---|---|---|---:|",
    ]
    lines.extend(
        f"| {row['seed']} | {row['status']} | {row['center_status']} | {row['solver_status']} | {row['exact_status']} | {row['coupling']:.6g} |"
        for row in audit["rows"]
    )
    (root / "docs/evidence/v5/V5_TWO_PARAMETER_DEVELOPMENT_AUDIT.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return audit
