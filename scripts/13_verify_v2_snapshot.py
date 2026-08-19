"""Create or verify the immutable v2 raw-data snapshot manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def inventory(root: Path) -> list[dict[str, object]]:
    files: list[Path] = []
    for relative in ["outputs/runs", "paper_artifacts/data", "paper_artifacts/figures", "paper_artifacts/tables"]:
        files.extend(path for path in (root / relative).rglob("*") if path.is_file())
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(files)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = root / "docs/evidence/v2_data_snapshot.json"
    current = {
        "schema_version": 1,
        "protocol": "SAEPS-JCP-EXEC-v2.0",
        "scope": [
            "outputs/runs",
            "paper_artifacts/data",
            "paper_artifacts/figures",
            "paper_artifacts/tables",
        ],
        "files": inventory(root),
    }
    if arguments.write:
        destination.write_text(
            json.dumps(current, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(json.dumps({"status": "WRITTEN", "files": len(current["files"])}, sort_keys=True))
        return 0
    expected = json.loads(destination.read_text(encoding="utf-8"))
    if current != expected:
        print(json.dumps({"status": "FAILED", "reason": "snapshot inventory mismatch"}, sort_keys=True))
        return 1
    print(json.dumps({"status": "PASSED", "files": len(current["files"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
