"""Create or verify the immutable v2 raw-data snapshot manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


V2_RUN_DIRECTORIES = [
    "outputs/runs/p1",
    "outputs/runs/p2_confirmation",
    "outputs/runs/p2_development",
    "outputs/runs/p3",
    "outputs/runs/p4_screening",
    "outputs/runs/p5_scalar",
    "outputs/runs/p6_development",
    "outputs/runs/p6_multi",
    "outputs/runs/p7_robustness",
    "outputs/runs/p8_cost",
]
V2_PAPER_DIRECTORIES = [
    "paper_artifacts/data",
    "paper_artifacts/figures",
    "paper_artifacts/tables",
]


def inventory(root: Path) -> list[dict[str, object]]:
    files: list[Path] = []
    for relative in V2_RUN_DIRECTORIES + V2_PAPER_DIRECTORIES:
        files.extend(path for path in (root / relative).rglob("*") if path.is_file())
    records = []
    for path in sorted(files):
        canonical = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "canonical_lf_bytes": len(canonical),
                "canonical_lf_sha256": hashlib.sha256(canonical).hexdigest(),
            }
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = root / "docs/evidence/v2_data_snapshot.json"
    current = {
        "schema_version": 2,
        "protocol": "SAEPS-JCP-EXEC-v2.0",
        "hash_canonicalization": "all CRLF and CR newlines converted to LF before byte count and SHA256",
        "scope": V2_RUN_DIRECTORIES + V2_PAPER_DIRECTORIES,
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
