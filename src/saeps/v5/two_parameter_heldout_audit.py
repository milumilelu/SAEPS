"""Audit V5.3B and issue conditional confirmation authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from saeps.io_utils import write_json_atomic
from saeps.v5.governance import sha256_file
from saeps.v5.two_parameter_frozen import HELDOUT_SEEDS


def build_two_parameter_heldout_audit(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    rows = []
    sources = []
    for seed in HELDOUT_SEEDS:
        path = root / f"outputs/runs/v5/two_parameter/heldout/seed_{seed}/result.json"
        if not path.is_file():
            raise ValueError(f"missing V5.3B seed: {seed}")
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
                "D2_descriptive_nonbinding": (record["primary"] or {}).get("D2"),
            }
        )
        sources.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)})
    valid = sum(row["binding_valid"] for row in rows)
    return {
        "schema_version": 1,
        "phase": "V5_3B_TWO_PARAMETER_HELDOUT",
        "engineering_status": "PASSED" if valid == 2 else "FAILED",
        "binding_valid_count": valid,
        "planned_count": 2,
        "confirmation_authorized": valid == 2,
        "authorization_inputs": ["binding_valid_seed_213", "binding_valid_seed_214"],
        "comparative_metrics_entered_authorization": False,
        "frozen_executable_sha256": sha256_file(root / "src/saeps/v5/two_parameter_frozen.py"),
        "rows": rows,
        "source_records": sources,
    }


def write_two_parameter_heldout_audit(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    audit = build_two_parameter_heldout_audit(root)
    write_json_atomic(root / "docs/evidence/v5/V5_TWO_PARAMETER_HELDOUT_AUDIT.json", audit)
    lines = [
        "# V5.3B Two-Parameter Held-Out Audit",
        "",
        f"- Engineering status: `{audit['engineering_status']}`",
        f"- Binding-valid: `{audit['binding_valid_count']}/2`",
        f"- Confirmation authorized: `{str(audit['confirmation_authorized']).lower()}`",
        "- Authorization inputs: binding-valid statuses only; comparative values are descriptive and nonbinding.",
        "",
        "| Seed | Status | Center | Solver | Exact | Coupling | D2 descriptive |",
        "|---:|---|---|---|---|---:|---:|",
    ]
    lines.extend(
        f"| {row['seed']} | {row['status']} | {row['center_status']} | {row['solver_status']} | {row['exact_status']} | {row['coupling']:.6g} | {row['D2_descriptive_nonbinding']:.6g} |"
        for row in audit["rows"]
    )
    (root / "docs/evidence/v5/V5_TWO_PARAMETER_HELDOUT_AUDIT.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    if audit["confirmation_authorized"]:
        authorization = {
            "schema_version": 1,
            "contract_id": "SAEPS-V5.3C-TWO-PARAMETER-CONFIRMATION-AUTHORIZATION",
            "authorization_date": "2026-08-23",
            "confirmation_authorized": True,
            "seeds": list(range(215, 225)),
            "planned_denominator": 10,
            "frozen_executable_sha256": audit["frozen_executable_sha256"],
            "heldout_binding_valid_count": audit["binding_valid_count"],
            "authorization_inputs": audit["authorization_inputs"],
            "comparative_metrics_entered_authorization": False,
            "source_records": audit["source_records"],
            "threshold_or_seed_change": False,
        }
        write_json_atomic(
            root / "configs/v5/TWO_PARAMETER_CONFIRMATION_AUTHORIZATION.json",
            authorization,
        )
    return audit
