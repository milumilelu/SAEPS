"""Record a SHA-256 manifest of every file in the paper-revision namespace.

Run from the namespace root:  python src/manifest_outputs.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> None:
    files = {}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative == "reports/output_manifest.json" or "__pycache__" in path.parts:
            continue
        files[relative] = sha256(path)
    manifest = {
        "namespace": "experiments/paper_revision_20260916",
        "evidence_ref": "jcp-submission-v1",
        "evidence_commit": git("rev-parse", "jcp-submission-v1^{commit}"),
        "repo_head_at_run": git("rev-parse", "HEAD"),
        "classification": "NEW_POSTHOC_READ_ONLY",
        "training_executed": False,
        "historical_records_modified": False,
        "files": files,
    }
    (ROOT / "reports/output_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(files)} entries")


if __name__ == "__main__":
    main()
