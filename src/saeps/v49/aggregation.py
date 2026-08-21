"""Read-only aggregation and integrity validation for V4.8 robustness."""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _median(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) is not None and row["binding_valid"]]
    return statistics.median(values) if values else None


def _load_seed(root: Path, family: str, seed: int, expected: int) -> list[dict[str, Any]]:
    directory = root / "outputs/runs/v4_8_robustness" / family / f"seed_{seed}"
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if summary["planned"] != expected or summary["completed"] != expected or len(manifest["records"]) != expected:
        raise RuntimeError(f"incomplete V4.8 seed: {family}/{seed}")
    records = []
    for row in manifest["records"]:
        path = directory / row["path"]
        if _sha256(path) != row["sha256"]:
            raise RuntimeError(f"V4.8 record hash mismatch: {path}")
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["seed"] != seed or record["status"] != row["status"] or record["binding_valid"] != row["binding_valid"]:
            raise RuntimeError(f"V4.8 manifest semantic mismatch: {path}")
        records.append(record)
    return records


def aggregate_v4_8(root: Path) -> dict[str, Any]:
    root = root.resolve()
    noise = [row for seed in range(130, 135) for row in _load_seed(root, "noise_sparsity", seed, 9)]
    architecture = [row for seed in range(135, 140) for row in _load_seed(root, "architecture", seed, 3)]
    if len(noise) != 45 or len(architecture) != 15:
        raise RuntimeError("V4.8 planned denominator mismatch")

    def grouped(rows: list[dict[str, Any]]) -> dict[str, Any]:
        values: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            values[row["condition"]].append(row)
        result = {}
        for condition, cell in sorted(values.items()):
            counts = Counter(row["status"] for row in cell)
            result[condition] = {
                "planned": len(cell), "binding_valid": sum(row["binding_valid"] for row in cell),
                "status_counts": {status: counts.get(status, 0) for status in ("PASS", "CHECKPOINT_INVALID", "SOLVER_FAILURE", "NUMERICAL_FAILURE")},
                "median_eta_valid": _median(cell, "eta"), "median_F_raw_valid": _median(cell, "F_raw"),
                "median_F_se_valid": _median(cell, "F_se_GN"),
                "valid_seeds": [row["seed"] for row in cell if row["binding_valid"]],
                "invalid_seeds": [row["seed"] for row in cell if not row["binding_valid"]],
            }
        return result

    anchors = [row for row in noise if row["exact_required"]]
    exact_valid = [row for row in anchors if row["binding_valid"]]
    overall = noise + architecture
    counts = Counter(row["status"] for row in overall)
    summary = {
        "schema_version": 1, "phase": "V4_8_PAIRED_ROBUSTNESS", "scientific_gate": "DESCRIPTIVE_ONLY",
        "integrity_gate": "PASS", "planned": 60, "completed": 60,
        "binding_valid": sum(row["binding_valid"] for row in overall),
        "status_counts": {status: counts.get(status, 0) for status in ("PASS", "CHECKPOINT_INVALID", "SOLVER_FAILURE", "NUMERICAL_FAILURE")},
        "noise_sparsity": {"planned": 45, "binding_valid": sum(row["binding_valid"] for row in noise), "cells": grouped(noise)},
        "architecture": {"planned": 15, "binding_valid": sum(row["binding_valid"] for row in architecture), "widths": grouped(architecture)},
        "exact_anchors": {
            "planned": 15, "binding_valid": len(exact_valid),
            "strict_SAEPS_wins": sum(float(row["D"]) > 0.0 for row in exact_valid),
            "median_E_raw_valid": _median(exact_valid, "E_raw"),
            "median_E_SAEPS_valid": _median(exact_valid, "E_SAEPS"),
            "median_D_valid": _median(exact_valid, "D"),
        },
        "adjudication": {
            "engineering_execution": "PASSED",
            "noise_sparsity": "DESCRIPTIVE_EVIDENCE_WITH_RETAINED_FAILURES",
            "architecture": "WIDE_CENTER_AVAILABILITY_LIMITATION",
            "method_or_threshold_change_authorized": False,
        },
    }
    return summary
