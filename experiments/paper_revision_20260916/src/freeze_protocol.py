"""Freeze the E3 protocol snapshot before the held-out cohort runs.

Mirrors the repository's own convention of pinning a protocol by hash before a
confirmation run: the snapshot records the protocol file hash, the executable hash and
the frozen commit, and the held-out runner refuses to start unless the live files still
match.  That makes "the configuration was not changed after development" checkable
rather than merely asserted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo_adapter as A  # noqa: E402

NAMESPACE = Path(__file__).resolve().parents[1]
FROZEN_FILES = ("protocol.yaml", "src/e3_saturation.py")
DEFAULT_OUT = NAMESPACE / "reports/E3_FROZEN_PROTOCOL.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(A.repo_root()), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--development-summary", type=Path)
    args = parser.parse_args()

    destination = args.out.resolve()
    if destination.exists():
        raise FileExistsError(f"{destination} already exists; a frozen protocol is immutable")

    development = None
    if args.development_summary is not None:
        development = json.loads(args.development_summary.read_text(encoding="utf-8"))

    snapshot = {
        "schema_version": 1,
        "contract": "SAEPS-PAPER-REVISION-E3-FROZEN",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_ref": A.DEFAULT_REF,
        "evidence_commit": A.resolve_commit(A.repo_root(), A.DEFAULT_REF),
        "repo_head": git("rev-parse", "HEAD"),
        "repo_head_subject": git("log", "-1", "--format=%s"),
        "reason": args.reason,
        "frozen_files": {name: sha256_file(NAMESPACE / name) for name in FROZEN_FILES},
        "development_summary": development,
        "heldout": {
            "seeds": [916101, 916102, 916103, 916104, 916105, 916106],
            "planned_fits": 24,
            "authorized": True,
            "protocol_change_after_freeze_forbidden": True,
        },
        "classification": "NEW_EXPERIMENT",
        "historical_records_modified": False,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(destination)


if __name__ == "__main__":
    main()
