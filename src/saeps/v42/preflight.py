"""Preflight for the separately locked v4.2 one-shot confirmation."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from saeps.config import load_config
from saeps.provenance import git_provenance


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_v42_preflight(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config_path = root / "configs/v4_2/locked_corrected_confirmation.yaml"
    specification = load_config(config_path)
    record = json.loads((root / "configs/v4_2/LOCK_RECORD.json").read_text(encoding="utf-8"))
    checks: dict[str, Any] = {}
    checks["locked_config"] = {
        "status": "PASS" if _sha256(config_path) == record["locked_config_sha256"] else "FAIL",
        "sha256": _sha256(config_path),
        "lock_commit": record["lock_commit"],
    }
    checks["planned_seeds"] = {
        "status": "PASS" if specification["planned_seeds"] == list(range(55, 70)) else "FAIL",
        "seeds": specification["planned_seeds"],
    }
    source_rows = []
    for key in [
        "source_v3_6_scientific_protocol",
        "source_v4_1_executable_freeze",
        "source_v4_1_heldout_evidence",
    ]:
        source = specification[key]
        actual = _sha256(root / source["path"])
        source_rows.append({"path": source["path"], "expected": source["sha256"], "actual": actual})
    checks["source_hashes"] = {
        "status": "PASS" if all(row["expected"] == row["actual"] for row in source_rows) else "FAIL",
        "sources": source_rows,
    }
    executable_rows = []
    for path_name, expected in record["file_sha256"].items():
        actual = _sha256(root / path_name)
        executable_rows.append({"path": path_name, "expected": expected, "actual": actual})
    checks["executable_hashes"] = {
        "status": "PASS" if all(row["expected"] == row["actual"] for row in executable_rows) else "FAIL",
        "files": executable_rows,
    }
    existing = sorted(str(path.relative_to(root)).replace("\\", "/") for path in (root / "outputs/runs").glob("v4_2*"))
    checks["absence_of_prior_run"] = {"status": "PASS" if not existing else "FAIL", "paths": existing}
    provenance = git_provenance(root)
    checks["clean_source"] = {"status": "PASS" if not provenance["git_dirty"] else "FAIL", **provenance}
    commands = {}
    for name, command in {
        "pytest": [sys.executable, "-m", "pytest", "-q"],
        "v4_1_heldout_validator": [sys.executable, "scripts/32_validate_v4_1_cohort.py", "--role", "HELDOUT_DEVELOPMENT"],
        "v3_6_result_validator": [sys.executable, "scripts/30_validate_v3_6_confirmation.py"],
    }.items():
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        commands[name] = {
            "command": command,
            "exit_code": completed.returncode,
            "stdout_tail": completed.stdout[-3000:],
            "stderr_tail": completed.stderr[-3000:],
        }
    checks["static_commands"] = {
        "status": "PASS" if all(row["exit_code"] == 0 for row in commands.values()) else "FAIL",
        "commands": commands,
    }
    v36_result = json.loads((root / "configs/v3_6/CONFIRMATION_RESULT_RECORD.json").read_text(encoding="utf-8"))
    checks["v3_6_permanent_protection"] = {
        "status": "PASS" if v36_result["rerun_permitted"] is False and v36_result["result_mutation_permitted"] is False else "FAIL",
        "scientific_status": v36_result["scientific_status"],
        "raw_records_sha256": v36_result["raw_records_sha256"],
    }
    status = "PASSED" if all(row["status"] == "PASS" for row in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V4_2_PRE_CONFIRMATION_AUDIT",
        "status": status,
        "checks": checks,
        "prior_runs": len(existing),
        "execution_started": False,
    }

