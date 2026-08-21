"""Finalize v4.4 packaging from immutable raw records without rerunning seeds."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from saeps.v44.result_validation import build_manifest_rows


def _write(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    run = root / "outputs/runs/v4_4_allen_cahn_confirmation"
    manifest_path = run / "manifest.json"
    failed_path = run / "failed_seeds.json"
    if manifest_path.exists() or failed_path.exists():
        raise RuntimeError("v4.4 recovery artifacts already exist; recovery rerun forbidden")
    if not (run / "summary.json").is_file():
        raise RuntimeError("frozen aggregator summary is required before packaging recovery")
    rows, records = build_manifest_rows(root)
    raw_records_sha256 = hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    _write(
        manifest_path,
        {
            "schema_version": 1,
            "planned": 10,
            "records": rows,
            "raw_records_sha256": raw_records_sha256,
            "packaging_recovered_without_seed_rerun": True,
            "seed_computation_repeated": False,
            "recovery_reason": "locked execution wrapper expected records/ instead of architecture_w8/",
        },
    )
    _write(
        failed_path,
        {
            "schema_version": 1,
            "failed": [
                {
                    "seed": record["seed"],
                    "status": record["status"],
                    "failure_reason": record["failure_reason"],
                    "statuses": record["statuses"],
                }
                for record in records
                if record["status"] != "PASS"
            ],
        },
    )
    print(json.dumps({"status": "PASSED", "raw_records_sha256": raw_records_sha256}, indent=2))
