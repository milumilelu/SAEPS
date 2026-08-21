"""Clean preflight for one-shot v4.5 controlled confirmation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from saeps.config import load_config


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / "configs/v4_5/CONTROLLED_CONFIRMATION_LOCK_RECORD.json").read_text(encoding="utf-8"))
    specification = load_config(root / "configs/v4_5/locked_controlled_confirmation.yaml")
    checks = {
        "exact_seeds_90_99": specification["planned_seeds"] == list(range(90, 100)),
        "all_locked_hashes": all(hashlib.sha256((root / path).read_bytes()).hexdigest() == expected for path, expected in lock["file_sha256"].items()),
        "no_prior_summary_output": not (root / "outputs/runs/v4_5_controlled_confirmation").exists(),
        "no_prior_seed_output": not (root / "outputs/runs/v4_5_controlled_mechanism/confirmation").exists(),
        "clean_worktree": subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True).stdout.strip() == "",
        "historical_results_present": (root / "configs/v4_2/CONFIRMATION_RESULT_RECORD.json").is_file() and (root / "configs/v4_4/CONFIRMATION_RESULT_RECORD.json").is_file(),
    }
    tests = subprocess.run([str(root / ".venv/Scripts/python.exe"), "-m", "pytest", "-q"], cwd=root, capture_output=True, text=True)
    checks["full_test_suite"] = tests.returncode == 0
    audit = {"schema_version": 1, "phase": "V4_5_CONTROLLED_CONFIRMATION_PREFLIGHT", "status": "PASSED" if all(checks.values()) else "FAILED", "checks": checks, "lock_commit": lock["lock_commit"], "locked_config_sha256": lock["locked_config_sha256"], "test_tail": tests.stdout.strip().splitlines()[-1] if tests.stdout.strip() else tests.stderr[-500:]}
    path = root / "docs/evidence/V4_5_CONTROLLED_PRECONFIRMATION_AUDIT.json"
    path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(audit, indent=2, sort_keys=True))
    raise SystemExit(0 if audit["status"] == "PASSED" else 1)
