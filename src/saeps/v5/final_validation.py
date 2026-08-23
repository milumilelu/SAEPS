"""Post-execution V5 repository validator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from saeps.config import load_config
from saeps.v5.final_audit import build_final_audit, final_report_markdown
from saeps.v5.governance import (
    NEW_CHECKPOINT_ROLE,
    RECONSTRUCTED_ROLE,
    sha256_file,
    validate_checkpoint_inventory,
    validate_checkpoint_manifest,
    validate_historical_inventory,
    validate_seed_registry,
)


def _check(condition: bool, detail: str) -> dict[str, str]:
    return {"status": "PASS" if condition else "FAIL", "detail": detail}


def _validate_sources(root: Path, aggregate_path: str) -> int:
    aggregate = json.loads((root / aggregate_path).read_text(encoding="utf-8"))
    for source in aggregate["source_records"]:
        path = root / source["path"]
        if not path.is_file() or sha256_file(path) != source["sha256"]:
            raise ValueError(f"aggregate lineage failure: {source['path']}")
    return len(aggregate["source_records"])


def validate_v5_repository(repo_root: str | Path, *, require_final: bool = True) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    checks: dict[str, dict[str, str]] = {}
    registry = load_config(root / "configs/v5/seed_registry.yaml")
    validate_seed_registry(registry)
    checks["seed_registry"] = _check(True, "all registered cohorts remain exact and disjoint")
    inventory = json.loads((root / "configs/v5/HISTORICAL_HASH_INVENTORY.json").read_text(encoding="utf-8"))
    validate_historical_inventory(root, inventory)
    checks["historical_immutability"] = _check(True, "441 protected pre-V5 files retain the frozen tree digest")

    freeze_files = sorted(root.glob("configs/v5/*FREEZE*.json"))
    frozen_count = 0
    for freeze_path in freeze_files:
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        for relative, expected in freeze.get("file_sha256", {}).items():
            if sha256_file(root / relative) != expected:
                raise ValueError(f"frozen executable mismatch: {relative}")
            frozen_count += 1
    checks["frozen_protocol_and_executables"] = _check(True, f"{frozen_count} frozen file hashes match")

    checkpoint_count = validate_checkpoint_inventory(root)
    manifests = sorted((root / "outputs/runs/v5/checkpoints").rglob("checkpoint_manifest.json"))
    records = [validate_checkpoint_manifest(root, path) for path in manifests]
    reconstructed = [int(row["source_seed"]) for row in records if row["artifact_role"] == RECONSTRUCTED_ROLE]
    scientific = [int(row["source_seed"]) for row in records if row["artifact_role"] == NEW_CHECKPOINT_ROLE]
    expected_reconstructed = [45, 46, 47, 70, 71, 72, 73, 74, 120]
    expected_scientific = list(range(200, 205)) + list(range(210, 225))
    checkpoint_ok = (
        checkpoint_count == 29
        and sorted(reconstructed) == expected_reconstructed
        and sorted(scientific) == expected_scientific
        and all(int(row.get("attempt", 1)) == 1 for row in records)
        and all(row.get("replacement_permitted") is False for row in records)
        and all(row.get("retry_permitted") is False for row in records)
    )
    checks["training_ceiling_and_checkpoint_lineage"] = _check(checkpoint_ok, "29/29 unique one-attempt reloadable checkpoints; no retry or replacement")

    source_counts = {
        "finite_gamma": _validate_sources(root, "docs/evidence/v5/V5_FINITE_GAMMA_AUDIT.json"),
        "profile": _validate_sources(root, "docs/evidence/v5/V5_PROFILE_BRIDGE_REPORT.json"),
        "two_parameter": _validate_sources(root, "docs/evidence/v5/V5_TWO_PARAMETER_CONFIRMATION_REPORT.json"),
        "residual_scalability": _validate_sources(root, "docs/evidence/v5/V5_RESIDUAL_SCALABILITY_REPORT.json"),
        "baseline": _validate_sources(root, "docs/evidence/v5/V5_BASELINE_CONSOLIDATION.json"),
    }
    checks["raw_to_aggregate_lineage"] = _check(source_counts == {"finite_gamma": 42, "profile": 5, "two_parameter": 10, "residual_scalability": 27, "baseline": 5}, f"source record counts: {source_counts}")

    profile = json.loads((root / "docs/evidence/v5/V5_PROFILE_BRIDGE_REPORT.json").read_text(encoding="utf-8"))
    two = json.loads((root / "docs/evidence/v5/V5_TWO_PARAMETER_CONFIRMATION_REPORT.json").read_text(encoding="utf-8"))
    residual = json.loads((root / "docs/evidence/v5/V5_RESIDUAL_SCALABILITY_REPORT.json").read_text(encoding="utf-8"))
    outcomes_ok = (
        profile["scientific_status"] == "NOT_SUPPORTED" and profile["profile_valid_count"] == 1
        and two["scientific_status"] == "INCONCLUSIVE" and two["binding_valid_count"] == 8
        and residual["engineering_status"] == "PASSED" and residual["pass_count"] == 27
    )
    checks["scientific_adjudications_preserved"] = _check(outcomes_ok, "profile NOT_SUPPORTED; two-parameter INCONCLUSIVE; residual scaling 27/27 PASS")
    inactive = list((root / "outputs/runs").glob("v4_6_two_parameter_confirmation*"))
    forbidden = list((root / "outputs/runs/v5").glob("**/*rescue*"))
    checks["stopped_and_forbidden_cohorts"] = _check(not inactive and not forbidden, "inactive 105--114 and V5 rescue cohorts remain absent")

    if require_final:
        audit_path = root / "docs/evidence/v5_final_audit.json"
        report_path = root / "V5_FINAL_JCP_AUDIT_REPORT.md"
        stored = json.loads(audit_path.read_text(encoding="utf-8"))
        rebuilt = build_final_audit(root)
        final_ok = stored == rebuilt and report_path.read_text(encoding="utf-8") == final_report_markdown(rebuilt)
        checks["final_report_rebuild"] = _check(final_ok, "machine audit and Markdown report rebuild exactly from source aggregates")
        manifest = json.loads((root / "paper_artifacts/v5/manifest.json").read_text(encoding="utf-8"))
        artifact_ok = all(sha256_file(root / row["path"]) == row["sha256"] for row in manifest["artifacts"])
        checks["paper_artifact_manifest"] = _check(artifact_ok and len(manifest["artifacts"]) >= 7, f"{len(manifest['artifacts'])} V5 paper artifacts match manifest hashes")

    status = "PASSED" if all(row["status"] == "PASS" for row in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V5_FINAL_REPOSITORY_VALIDATION",
        "status": status,
        "checks": checks,
        "scientific_conclusion": "PARTIALLY_SUPPORTED",
        "full_general_JCP_claim_ready": False,
    }
