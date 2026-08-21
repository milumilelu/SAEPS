"""Independent validation for the permanently closed v4.4 result."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from saeps.config import load_config
from saeps.v44.aggregation import aggregate_allen_confirmation


PLANNED_SEEDS = list(range(75, 85))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_result_paths(root: Path) -> list[Path]:
    run = root / "outputs/runs/v4_4_allen_cahn_confirmation"
    return [run / f"architecture_w8/seed_{seed}/result.json" for seed in PLANNED_SEEDS]


def build_manifest_rows(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    run = root / "outputs/runs/v4_4_allen_cahn_confirmation"
    paths = raw_result_paths(root)
    if not all(path.is_file() for path in paths):
        missing = [str(path) for path in paths if not path.is_file()]
        raise RuntimeError(f"all exact v4.4 raw records are required; missing={missing}")
    records = [_read_json(path) for path in paths]
    if [record.get("seed") for record in records] != PLANNED_SEEDS:
        raise RuntimeError("raw record seeds do not match the locked planned order")
    rows = [
        {
            "seed": record["seed"],
            "status": record["status"],
            "binding_valid": record["binding_valid"],
            "path": str(path.relative_to(run)).replace("\\", "/"),
            "sha256": _sha256(path),
        }
        for path, record in zip(paths, records)
    ]
    return rows, records


def validate_v44_result(root: Path) -> dict[str, Any]:
    run = root / "outputs/runs/v4_4_allen_cahn_confirmation"
    summary = _read_json(run / "summary.json")
    manifest = _read_json(run / "manifest.json")
    rows, records = build_manifest_rows(root)
    seed_manifests_match = True
    for row in rows:
        seed_manifest = _read_json(
            run / f"architecture_w8/seed_{row['seed']}/manifest.json"
        )
        seed_manifests_match &= (
            seed_manifest.get("seed") == row["seed"]
            and seed_manifest.get("status") == row["status"]
            and seed_manifest.get("binding_valid") == row["binding_valid"]
            and seed_manifest.get("result_sha256") == row["sha256"]
        )
    specification = load_config(root / "configs/v4_4/locked_allen_cahn_confirmation.yaml")
    reproduced = aggregate_allen_confirmation(records, specification)
    aggregate_keys = list(reproduced)
    aggregate_matches = all(summary.get(key) == reproduced[key] for key in aggregate_keys)
    rows_match = manifest.get("records") == rows
    raw_records_sha256 = hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    checks = {
        "exact_seed_set": [row["seed"] for row in rows] == PLANNED_SEEDS,
        "raw_hashes_match": rows_match,
        "per_seed_manifests_match": seed_manifests_match,
        "raw_records_sha256_matches": manifest.get("raw_records_sha256") == raw_records_sha256,
        "locked_aggregate_reproduction": aggregate_matches,
        "planned_denominator_is_10": summary.get("planned") == 10,
        "all_primary_conditions_pass": all(summary.get("primary_conditions", {}).values()),
        "scientific_status_supported": summary.get("scientific_status") == "SUPPORTED",
        "seed_computation_not_repeated": manifest.get("seed_computation_repeated") is False,
    }
    return {
        "schema_version": 1,
        "status": "PASSED" if all(checks.values()) else "FAILED",
        "checks": checks,
        "raw_records_sha256": raw_records_sha256,
        "planned_seeds": PLANNED_SEEDS,
        "scientific_status": summary.get("scientific_status"),
    }
