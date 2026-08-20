"""Pre-confirmation audit for the immutable v3.6 one-shot run."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from saeps.config import load_config
from saeps.provenance import git_provenance


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _command(root: Path, command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def run_preconfirmation_audit(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config_path = root / "configs/v3_6/locked_scalar_confirmation.yaml"
    record_path = root / "configs/v3_6/LOCK_RECORD.json"
    specification = load_config(config_path)
    lock_record = json.loads(record_path.read_text(encoding="utf-8"))
    checks: dict[str, Any] = {}

    current_hash = _sha256(config_path)
    lock_commit = lock_record["lock_commit"]
    committed = subprocess.run(
        ["git", "show", f"{lock_commit}:configs/v3_6/locked_scalar_confirmation.yaml"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    committed_hash = hashlib.sha256(committed.stdout).hexdigest() if committed.returncode == 0 else None
    checks["immutable_lock"] = {
        "status": "PASS"
        if current_hash == lock_record["locked_config_sha256"] == committed_hash
        else "FAIL",
        "current_sha256": current_hash,
        "recorded_sha256": lock_record["locked_config_sha256"],
        "commit_sha256": committed_hash,
        "lock_commit": lock_commit,
    }

    source_rows = []
    for source in specification["source_files"].values():
        actual = _sha256(root / source["path"])
        source_rows.append(
            {
                "path": source["path"],
                "expected_sha256": source["sha256"],
                "actual_sha256": actual,
                "status": "PASS" if actual == source["sha256"] else "FAIL",
            }
        )
    checks["source_hashes"] = {
        "status": "PASS" if all(row["status"] == "PASS" for row in source_rows) else "FAIL",
        "sources": source_rows,
    }
    checks["planned_seeds"] = {
        "status": "PASS" if specification["planned_seeds"] == list(range(30, 45)) else "FAIL",
        "seeds": specification["planned_seeds"],
    }
    existing = sorted(
        str(path.relative_to(root)).replace("\\", "/")
        for path in (root / "outputs/runs").glob("v3_6*")
    )
    checks["absence_of_prior_outputs"] = {
        "status": "PASS" if not existing else "FAIL",
        "existing_paths": existing,
    }
    provenance = git_provenance(root)
    checks["clean_execution_source"] = {
        "status": "PASS" if not provenance["git_dirty"] else "FAIL",
        **provenance,
    }
    python = root / ".venv/Scripts/python.exe"
    commands = {
        "pytest": _command(root, [str(python), "-m", "pytest", "-q"]),
        "v3_6_lock_validator": _command(root, [str(python), "scripts/26_validate_v3_6_lock.py"]),
        "repository_validator": _command(root, [str(python), "scripts/validate_repository.py"]),
    }
    checks["static_commands"] = {
        "status": "PASS" if all(row["exit_code"] == 0 for row in commands.values()) else "FAIL",
        "commands": commands,
    }
    taskbook = root / "SAEPS Master Research Program v4.0.md"
    taskbook_info = {
        "path": taskbook.name,
        "sha256": _sha256(taskbook) if taskbook.is_file() else None,
    }
    status = "PASSED" if all(row["status"] == "PASS" for row in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V3_6_PRE_CONFIRMATION_AUDIT",
        "status": status,
        "checks": checks,
        "taskbook": taskbook_info,
        "execution_started": False,
        "confirmation_runs_observed": 0,
    }

