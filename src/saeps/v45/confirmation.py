"""Locked aggregation and one-shot execution for v4.5 confirmation."""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

from saeps.config import load_config
from saeps.controlled import spearman
from saeps.provenance import environment_provenance
from saeps.v46.pipeline import run_controlled_confirmation_seed


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def aggregate_v45_confirmation(records: list[dict[str, Any]], specification: dict[str, Any]) -> dict[str, Any]:
    planned = [int(seed) for seed in specification["planned_seeds"]]
    if [record["seed"] for record in records] != planned:
        raise ValueError("records do not match locked planned seeds")
    alphas = [float(value) for value in specification["alpha_values"]]
    per_seed = []
    correlations = []
    monotonic_count = 0
    for record in records:
        valid = bool(record["binding_valid"]) and all(
            row["status"] == "PASS" and row.get("eta") is not None
            for row in record["alpha_evaluations"]
        )
        eta = [float(row["eta"]) for row in record["alpha_evaluations"]] if valid else None
        rho = spearman(alphas, eta) if eta is not None else None
        monotonic = bool(
            eta is not None
            and all(
                eta[index + 1] >= eta[index] - float(specification["primary"]["monotonic_absolute_tolerance"])
                for index in range(len(eta) - 1)
            )
        )
        if rho is not None:
            correlations.append(float(rho))
        monotonic_count += int(monotonic)
        per_seed.append({"seed": record["seed"], "status": record["status"], "binding_valid": valid, "eta": eta, "spearman": rho, "monotonic": monotonic})
    valid_count = sum(row["binding_valid"] for row in per_seed)
    median_rho = statistics.median(correlations) if correlations else None
    conditions = {
        "all_planned_centers_valid": valid_count == len(planned),
        "planned_monotonic_count": monotonic_count >= int(specification["primary"]["monotonic_planned_seeds_required"]),
        "median_spearman": median_rho is not None and median_rho >= float(specification["primary"]["median_valid_seed_spearman_min"]),
    }
    return {
        "schema_version": 1,
        "phase": specification["phase"],
        "planned": len(planned),
        "valid": valid_count,
        "invalid": len(planned) - valid_count,
        "monotonic_planned_seeds": monotonic_count,
        "median_valid_seed_spearman": median_rho,
        "primary_conditions": conditions,
        "scientific_status": "SUPPORTED" if all(conditions.values()) else "NOT_SUPPORTED",
        "per_seed": per_seed,
    }


def run_v45_confirmation(root: Path) -> dict[str, Any]:
    authorization = json.loads((root / "configs/v4_5/CONFIRMATION_AUTHORIZATION.json").read_text(encoding="utf-8"))
    if authorization.get("authorized_once") is not True:
        raise RuntimeError("v4.5 confirmation is not authorized")
    specification = load_config(root / "configs/v4_5/locked_controlled_confirmation.yaml")
    destination = root / "outputs/runs/v4_5_controlled_confirmation"
    if destination.exists():
        raise RuntimeError("v4.5 confirmation output already exists; rerun forbidden")
    provenance = environment_provenance(root, "float64", "cpu")
    if provenance["git_dirty"]:
        raise RuntimeError("v4.5 confirmation requires a clean worktree")
    claim = {"schema_version": 1, "state": "CLAIMED_ONE_SHOT", "planned_seeds": specification["planned_seeds"], "git_commit": provenance["git_commit"], "rerun_forbidden": True}
    _write(destination / "execution_claim.json", claim)
    records = [run_controlled_confirmation_seed(root, int(seed), provenance) for seed in specification["planned_seeds"]]
    summary = aggregate_v45_confirmation(records, specification)
    summary.update(execution_claim=claim, provenance=provenance)
    _write(destination / "summary.json", summary)
    rows = []
    for record in records:
        path = destination.parent / "v4_5_controlled_mechanism/confirmation" / f"seed_{record['seed']}/result.json"
        rows.append({"seed": record["seed"], "status": record["status"], "binding_valid": record["binding_valid"], "path": str(path.relative_to(root)).replace("\\", "/"), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    _write(destination / "manifest.json", {"schema_version": 1, "planned": len(rows), "records": rows, "raw_records_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()})
    return summary
