"""Aggregate and audit the one-shot V5 engineering reconstructions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from saeps.io_utils import write_json_atomic
from saeps.v5.governance import (
    sha256_file,
    tree_digest,
    validate_checkpoint_inventory,
    validate_historical_inventory,
)


EXPECTED = {
    "burgers": [45, 46, 47],
    "allen_cahn": [70, 71, 72, 73, 74],
    "scalability_base": [120],
}


def build_reconstruction_audit(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    inventory = json.loads(
        (root / "configs/v5/HISTORICAL_HASH_INVENTORY.json").read_text(encoding="utf-8")
    )
    validate_historical_inventory(root, inventory)
    checkpoint_count = validate_checkpoint_inventory(root)
    rows: list[dict[str, Any]] = []
    commits: set[str] = set()
    for family, seeds in EXPECTED.items():
        for seed in seeds:
            directory = root / "outputs/runs/v5/checkpoints" / family / f"seed_{seed}"
            result_path = directory / "result.json"
            manifest_path = directory / "checkpoint_manifest.json"
            if not result_path.is_file() or not manifest_path.is_file():
                raise ValueError(f"missing fixed reconstruction record: {family}/{seed}")
            result = json.loads(result_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            commits.add(str(manifest["reconstruction_commit"]))
            rows.append(
                {
                    "family": family,
                    "seed": seed,
                    "status": result["status"],
                    "binding_valid": bool(result["binding_valid"]),
                    "elapsed_seconds": float(result["elapsed_seconds"]),
                    "result_path": result_path.relative_to(root).as_posix(),
                    "result_sha256": sha256_file(result_path),
                    "manifest_path": manifest_path.relative_to(root).as_posix(),
                    "manifest_sha256": sha256_file(manifest_path),
                    "model_state_hash": manifest["model_state_hash"],
                }
            )
    historical_count, historical_digest = tree_digest(
        root, "outputs/runs", excluded_prefixes=["outputs/runs/v5"]
    )
    if checkpoint_count != 9 or len(rows) != 9 or len(commits) != 1:
        raise ValueError("V5 reconstruction inventory is incomplete or spans source commits")
    pass_count = sum(row["status"] == "PASS" and row["binding_valid"] for row in rows)
    return {
        "schema_version": 1,
        "phase": "V5_ENGINEERING_RECONSTRUCTION",
        "status": "PASSED" if pass_count == 9 else "COMPLETED_WITH_INVALIDS",
        "scientific_result": None,
        "attempted_count": 9,
        "pass_count": pass_count,
        "retry_count": 0,
        "replacement_count": 0,
        "reconstruction_commit": next(iter(commits)),
        "historical_outputs_file_count": historical_count,
        "historical_outputs_tree_sha256": historical_digest,
        "records": rows,
    }


def write_reconstruction_audit(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    audit = build_reconstruction_audit(root)
    json_path = root / "docs/evidence/v5/V5_RECONSTRUCTION_AUDIT.json"
    markdown_path = root / "docs/evidence/v5/V5_RECONSTRUCTION_AUDIT.md"
    write_json_atomic(json_path, audit)
    lines = [
        "# V5 Engineering Reconstruction Audit",
        "",
        f"- Status: `{audit['status']}`",
        f"- Fixed sources attempted: `{audit['attempted_count']}/9`",
        f"- Binding-valid checkpoints: `{audit['pass_count']}/9`",
        "- Retries: `0`",
        "- Replacements: `0`",
        f"- Reconstruction source commit: `{audit['reconstruction_commit']}`",
        f"- Protected historical tree: `{audit['historical_outputs_file_count']}` files, `{audit['historical_outputs_tree_sha256']}`",
        "",
        "These artifacts are deterministic V5 engineering reconstructions. They are not historical tensor reuse and no tensor-identity claim is made.",
        "",
        "| Family | Seed | Status | Binding valid | Seconds |",
        "|---|---:|---|---|---:|",
    ]
    lines.extend(
        f"| {row['family']} | {row['seed']} | {row['status']} | {str(row['binding_valid']).lower()} | {row['elapsed_seconds']:.3f} |"
        for row in audit["records"]
    )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return audit
