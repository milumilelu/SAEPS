"""Clean preflight for one-shot Allen--Cahn external confirmation."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from saeps.config import load_config
from saeps.provenance import git_provenance
from saeps.v43.validation import validate_record_schema


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_v44_preflight(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config_path = root / "configs/v4_4/locked_allen_cahn_confirmation.yaml"
    specification = load_config(config_path)
    lock = json.loads((root / "configs/v4_4/LOCK_RECORD.json").read_text(encoding="utf-8"))
    checks: dict[str, Any] = {}
    checks["locked_config"] = {
        "status": "PASS" if _sha256(config_path) == lock["locked_config_sha256"] else "FAIL",
        "sha256": _sha256(config_path),
    }
    checks["planned_seeds"] = {
        "status": "PASS" if specification["planned_seeds"] == list(range(75, 85)) else "FAIL",
        "seeds": specification["planned_seeds"],
    }
    source_rows = []
    for name in ["source_development_freeze", "source_heldout_evidence"]:
        source = specification[name]
        source_rows.append(
            {
                "path": source["path"],
                "expected": source["sha256"],
                "actual": _sha256(root / source["path"]),
            }
        )
    checks["source_hashes"] = {
        "status": "PASS" if all(row["expected"] == row["actual"] for row in source_rows) else "FAIL",
        "sources": source_rows,
    }
    executable_rows = []
    for relative_path, expected in lock["file_sha256"].items():
        executable_rows.append(
            {"path": relative_path, "expected": expected, "actual": _sha256(root / relative_path)}
        )
    checks["executable_hashes"] = {
        "status": "PASS" if all(row["expected"] == row["actual"] for row in executable_rows) else "FAIL",
        "files": executable_rows,
    }
    existing = sorted(
        str(path.relative_to(root)).replace("\\", "/")
        for path in (root / "outputs/runs").glob("v4_4_allen_cahn_confirmation*")
    )
    checks["absence_of_prior_run"] = {"status": "PASS" if not existing else "FAIL", "paths": existing}
    provenance = git_provenance(root)
    checks["clean_source"] = {"status": "PASS" if not provenance["git_dirty"] else "FAIL", **provenance}
    schema_record = json.loads(
        (
            root
            / "outputs/runs/v4_3_allen_cahn_development/heldout/seed_74/result.json"
        ).read_text(encoding="utf-8")
    )
    try:
        validate_record_schema(schema_record)
        schema_status = "PASS"
    except Exception:
        schema_status = "FAIL"
    checks["raw_aggregator_schema"] = {"status": schema_status, "source": "real held-out seed74"}
    commands = {}
    for name, command in {
        "pytest": [sys.executable, "-m", "pytest", "-q"],
        "v4_3_heldout": [sys.executable, "scripts/41_validate_v4_3_allen_heldout.py"],
        "v4_2_result": [sys.executable, "scripts/38_validate_v4_2_confirmation.py"],
    }.items():
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        commands[name] = {
            "command": command,
            "exit_code": completed.returncode,
            "stdout_tail": completed.stdout[-3000:],
            "stderr_tail": completed.stderr[-3000:],
        }
    checks["static_commands"] = {
        "status": "PASS" if all(value["exit_code"] == 0 for value in commands.values()) else "FAIL",
        "commands": commands,
    }
    for version in ["v3_6", "v4_2"]:
        result = json.loads(
            (root / f"configs/{version}/CONFIRMATION_RESULT_RECORD.json").read_text(encoding="utf-8")
        )
        checks[f"{version}_permanent_protection"] = {
            "status": "PASS" if result["rerun_permitted"] is False else "FAIL",
            "scientific_status": result["scientific_status"],
        }
    status = "PASSED" if all(value["status"] == "PASS" for value in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V4_4_PRE_CONFIRMATION_AUDIT",
        "status": status,
        "checks": checks,
        "confirmation_runs_observed": len(existing),
        "execution_started": False,
    }

