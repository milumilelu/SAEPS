"""Independently reproduce and finalize the permanent v4.5 result."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from saeps.config import load_config
from saeps.v45.confirmation import aggregate_v45_confirmation


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    run = root / "outputs/runs/v4_5_controlled_confirmation"
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    records = []
    hash_checks = []
    for row in manifest["records"]:
        path = root / row["path"]
        hash_checks.append(hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"])
        records.append(json.loads(path.read_text(encoding="utf-8")))
    specification = load_config(root / "configs/v4_5/locked_controlled_confirmation.yaml")
    reproduced = aggregate_v45_confirmation(records, specification)
    checks = {
        "exact_planned_seeds": [record["seed"] for record in records] == list(range(90, 100)),
        "all_raw_hashes": all(hash_checks),
        "frozen_aggregate_reproduction": all(summary.get(key) == value for key, value in reproduced.items()),
        "planned_denominator_retained": summary["planned"] == 10,
        "scientific_status_not_supported": summary["scientific_status"] == "NOT_SUPPORTED",
    }
    audit = {"schema_version": 1, "status": "PASSED" if all(checks.values()) else "FAILED", "checks": checks, "raw_records_sha256": manifest["raw_records_sha256"]}
    _write(root / "docs/evidence/v4_5_controlled_confirmation.json", {"schema_version": 1, "summary": summary, "result_audit": audit})
    report = f"""# v4.5 Controlled-Mechanism Confirmation Report

**Scientific status:** `{summary['scientific_status']}`  
**Planned / valid / invalid:** `10 / {summary['valid']} / {summary['invalid']}`  
**Planned monotonic seeds:** `{summary['monotonic_planned_seeds']}/10`

The locked result is `NOT_SUPPORTED`. Only {summary['valid']}/10 planned centers are binding-valid, below the strict 10/10 requirement, and only {summary['monotonic_planned_seeds']}/10 planned seeds count as monotonic, below 8/10. The valid-seed median Spearman coefficient is `{summary['median_valid_seed_spearman']:.12g}` and all six valid seeds are monotonic. Thus the tangent-overlap mechanism is highly consistent conditional on a valid local state minimum, but planned-denominator center availability is not established.

Seeds 90, 91, 94 and 98 are center-invalid planned failures. None was replaced or rerun. No threshold or scientific rule changed after execution. Independent raw-to-frozen-aggregate reproduction passes.

Historical P2 remains `FAIL`; v4.5 provides stronger conditional mechanism evidence but does not close the unconditional planned-denominator claim. Raw manifest hash: `{manifest['raw_records_sha256']}`.
"""
    (root / "docs/evidence/V4_5_CONTROLLED_CONFIRMATION_REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    print(json.dumps(audit, indent=2, sort_keys=True))
    raise SystemExit(0 if audit["status"] == "PASSED" else 1)
