"""Validation of real Allen--Cahn development records and schema integration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from saeps.config import load_config


REQUIRED_STATUSES = {
    "center_status",
    "parameter_reference_status",
    "curvature_solver_status",
    "score_solver_status",
    "exact_reference_status",
    "finite_primary_status",
    "profile_status",
    "directional_indicator_status",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_record_schema(record: dict[str, Any]) -> None:
    required = {
        "seed",
        "benchmark",
        "architecture",
        "status",
        "binding_valid",
        "statuses",
        "F_raw",
        "F_se_explicit",
        "F_se_GN",
        "H_red_exact_gamma",
        "directional_indicator",
        "gamma_matched_profile",
    }
    missing = required - set(record)
    if missing:
        raise ValueError(f"record schema missing fields: {sorted(missing)}")
    status_missing = REQUIRED_STATUSES - set(record["statuses"])
    if status_missing:
        raise ValueError(f"record status schema missing fields: {sorted(status_missing)}")


def validate_allen_engineering(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    specification = load_config(root / "configs/v4_3/allen_cahn_development.yaml")
    expected = [int(value) for value in specification["engineering_seeds"]]
    width = int(specification["architecture_engineering"]["selected_width"])
    records = []
    hashes = {}
    for seed in expected:
        directory = root / f"outputs/runs/v4_3_allen_cahn_development/architecture_w{width}/seed_{seed}"
        manifest_path = directory / "manifest.json"
        result_path = directory / "result.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["result_sha256"] != _sha256(result_path):
            raise RuntimeError(f"result hash mismatch for seed {seed}")
        record = json.loads(result_path.read_text(encoding="utf-8"))
        validate_record_schema(record)
        if int(record["seed"]) != seed or int(record["architecture"]["hidden_width"]) != width:
            raise RuntimeError(f"seed/architecture mismatch for seed {seed}")
        records.append(record)
        hashes[str(seed)] = manifest["result_sha256"]

    binding = [record for record in records if record["binding_valid"]]
    required_binding = specification["binding_nodes"]
    binding_node_pass = {
        node: sum(record["statuses"][node] == "PASS" for record in records)
        for node in required_binding
    }
    score_failures = sum(record["statuses"]["score_solver_status"] == "SOLVER_FAILURE" for record in records)
    profile_passes = sum(record["statuses"]["profile_status"] == "PASS" for record in records)
    indicator_passes = sum(
        record["statuses"]["directional_indicator_status"] == "PASS" for record in records
    )
    state_rmse = [float(record["training"]["state_rmse_validation_only"]) for record in records]
    full_binding_pass = len(binding) == len(expected) and all(
        count == len(expected) for count in binding_node_pass.values()
    )
    result = {
        "schema_version": 1,
        "phase": "V4_3_ALLEN_CAHN_ENGINEERING_VALIDATION",
        "status": "PASSED" if full_binding_pass and indicator_passes == len(expected) else "FAILED",
        "scientific_gate": "NONE_DEVELOPMENT_ONLY",
        "seeds": expected,
        "selected_width": width,
        "state_parameters": 4 * width + 1,
        "record_hashes": hashes,
        "binding_valid_count": len(binding),
        "binding_node_pass_counts": binding_node_pass,
        "score_failure_nonbinding_count": score_failures,
        "directional_indicator_pass_count": indicator_passes,
        "profile_bridge_pass_count": profile_passes,
        "profile_bridge_failure_count": len(expected) - profile_passes,
        "state_rmse": state_rmse,
        "state_rmse_maximum": max(state_rmse),
        "selection_metrics_exclude_comparative_quantities": True,
        "confirmation_authorized": False,
        "runner_aggregator_schema_integration": "PASS",
    }
    if result["status"] != "PASSED":
        raise RuntimeError("Allen-Cahn engineering acceptance failed")
    return result

