"""Locked descriptive robustness and architecture-transfer experiments."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.core import compute_matrix_free_saeps
from saeps.p4_screening import _stationarity
from saeps.p5_confirmation import _runtime_config
from saeps.provenance import environment_provenance, make_run_id
from saeps.scalar import (
    refine_scalar_checkpoint,
    scalar_residual,
    solve_truth,
    train_scalar_checkpoint,
)


def _single(
    config: dict[str, Any],
    locked: dict[str, Any],
    seed: int,
    truth: Any,
    label: str,
) -> dict[str, Any]:
    checkpoint, points = train_scalar_checkpoint(config, "Burgers", seed, truth)

    def linearize(current: Any) -> tuple[Any, ...]:
        linearization = ResidualLinearization(
            lambda theta, parameter: scalar_residual(
                theta, parameter, "Burgers", points, truth, config
            ),
            current.theta,
            current.log_parameter,
        )
        residual = linearization.residual()
        jacobian_theta, jacobian_parameter = linearization.explicit_jacobians()
        return (
            linearization,
            jacobian_theta,
            _stationarity(jacobian_theta, residual),
            _stationarity(jacobian_parameter, residual),
        )

    linearization, jacobian_theta, theta_stationarity, parameter_stationarity = (
        linearize(checkpoint)
    )
    retry_used = False
    stationarity_gates = locked["stationarity_gates"]
    if (
        theta_stationarity > float(stationarity_gates["theta"])
        or parameter_stationarity > float(stationarity_gates["parameter"])
    ) and locked["additional_training"]["enabled"]:
        checkpoint = refine_scalar_checkpoint(
            config,
            checkpoint,
            points,
            truth,
            locked["additional_training"],
        )
        retry_used = True
        (
            linearization,
            jacobian_theta,
            theta_stationarity,
            parameter_stationarity,
        ) = linearize(checkpoint)

    record: dict[str, Any] = {
        "seed": seed,
        "label": label,
        "architecture": config["network"]["architecture"],
        "noise": float(config.get("observation_noise", 0.0)),
        "observation_fraction": float(config.get("observation_fraction", 1.0)),
        "theta_stationarity": theta_stationarity,
        "parameter_stationarity": parameter_stationarity,
        "state_rmse_validation_only": checkpoint.state_rmse,
        "retry_used": retry_used,
        "training_seconds": checkpoint.elapsed_seconds,
    }
    valid = (
        theta_stationarity <= float(stationarity_gates["theta"])
        and parameter_stationarity <= float(stationarity_gates["parameter"])
        and checkpoint.state_rmse
        <= float(locked["checkpoint_gates"]["state_rmse_max_validation_only"])
    )
    if not valid:
        record.update(
            {
                "status": "CHECKPOINT_INVALID",
                "failure_reason": "locked checkpoint gate failed",
                "Fraw": None,
                "Fse": None,
                "effect": None,
                "eta": None,
                "saeps_seconds": None,
            }
        )
        return record

    try:
        gamma = float(locked["gamma"]["nominal_alpha"]) * float(
            torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item()
        )
        saeps_started = time.perf_counter()
        saeps = compute_matrix_free_saeps(
            linearization,
            gamma,
            float(locked["gamma"]["cg_tolerance"]),
            int(locked["gamma"]["cg_max_iterations"]),
        )
        saeps_seconds = time.perf_counter() - saeps_started
        raw = float(saeps.raw_curvature[0, 0].item())
        eliminated = float(saeps.eliminated_curvature[0, 0].item())
        record.update(
            {
                "status": "PASS",
                "failure_reason": None,
                "gamma": gamma,
                "Fraw": raw,
                "Fse": eliminated,
                "effect": raw - eliminated,
                "eta": float(saeps.eta[0].item()),
                "saeps_seconds": saeps_seconds,
                "CG_relative_residual": [
                    solve.relative_residual for solve in saeps.solves
                ],
                "CG_iterations": [solve.iterations for solve in saeps.solves],
                "JVP_count": saeps.operation_counts.get("jvp_theta", 0)
                + saeps.operation_counts.get("jvp_parameter", 0),
                "VJP_count": saeps.operation_counts.get("vjp_theta", 0),
            }
        )
    except Exception as error:  # every planned run must receive a final status
        record.update(
            {
                "status": "SOLVER_FAILURE",
                "failure_reason": f"{type(error).__name__}: {error}",
                "Fraw": None,
                "Fse": None,
                "effect": None,
                "eta": None,
                "saeps_seconds": None,
            }
        )
    return record


def _median(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return statistics.median(values) if values else None


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "planned": len(rows),
        "valid": sum(row["status"] == "PASS" for row in rows),
        "status_counts": {
            status: sum(row["status"] == status for row in rows)
            for status in ["PASS", "CHECKPOINT_INVALID", "SOLVER_FAILURE"]
        },
        "median_Fraw": _median(rows, "Fraw"),
        "median_Fse": _median(rows, "Fse"),
        "median_effect": _median(rows, "effect"),
        "median_eta": _median(rows, "eta"),
        "median_theta_stationarity": _median(rows, "theta_stationarity"),
        "median_parameter_stationarity": _median(rows, "parameter_stationarity"),
        "median_state_rmse": _median(rows, "state_rmse_validation_only"),
    }


def _nominal_reference(output_root: Path) -> dict[str, Any]:
    p5_runs = sorted((output_root.parent / "p5_scalar").glob("*/summary.json"))
    if len(p5_runs) != 1:
        raise RuntimeError(
            f"expected exactly one immutable P5 run, found {len(p5_runs)}"
        )
    summary_path = p5_runs[0]
    p5_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return {
        "run_id": p5_summary["run_id"],
        "relative_summary_path": str(summary_path.relative_to(output_root.parent.parent)),
        "summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
        "planned": 10,
        "completed": len(p5_summary["per_seed"]),
        "status_counts": p5_summary["status_counts"],
        "median_eta_all_computable": _median(p5_summary["per_seed"], "eta"),
        "note": "Referenced without rerunning locked P5 confirmation.",
    }


def run_robustness(
    scalar_path: str | Path,
    robustness_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    started = time.perf_counter()
    locked = load_config(scalar_path)
    robust = load_config(robustness_path)
    base = _runtime_config(locked)
    truth = solve_truth(base, "Burgers")
    provenance = environment_provenance(repo_root, locked["dtype"], locked["device"])
    digest = config_hash(robust)
    run_id = make_run_id("P7-robustness", 10, digest, provenance["timestamp"])
    output_root = Path(output_root)
    destination = output_root / run_id
    records_dir = destination / "records"
    records_dir.mkdir(parents=True, exist_ok=False)

    records: list[dict[str, Any]] = []
    for noise in robust["noise_levels"]:
        for fraction in robust["observation_fractions"]:
            for seed in robust["seeds"]:
                config = copy.deepcopy(base)
                config["observation_noise"] = float(noise)
                config["observation_fraction"] = float(fraction)
                records.append(
                    _single(
                        config,
                        locked,
                        int(seed),
                        truth,
                        f"noise={noise}_fraction={fraction}",
                    )
                )

    for width, name in [(8, "narrow"), (32, "wide")]:
        for seed in robust["seeds"]:
            config = copy.deepcopy(base)
            config["network"] = {
                "architecture": f"tanh_mlp_2x{width}x1",
                "hidden_width": width,
            }
            records.append(
                _single(
                    config,
                    locked,
                    int(seed),
                    truth,
                    f"architecture={name}",
                )
            )

    manifest = []
    for index, record in enumerate(records):
        path = records_dir / f"record_{index:03d}.json"
        path.write_text(
            json.dumps(record, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        manifest.append(
            {
                "path": str(path.relative_to(destination)),
                "status": record["status"],
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(record["label"], []).append(record)
    groups = {label: _summarize(rows) for label, rows in grouped.items()}
    summary = {
        "schema_version": 1,
        "phase": "P7",
        "run_id": run_id,
        "engineering_gate": "PASSED" if len(records) == 55 else "FAILED",
        "completion_mode": "FULL",
        "planned_new_runs": 55,
        "completed_new_runs": len(records),
        "status_counts": {
            status: sum(record["status"] == status for record in records)
            for status in ["PASS", "CHECKPOINT_INVALID", "SOLVER_FAILURE"]
        },
        "groups": groups,
        "nominal_architecture_reference": _nominal_reference(output_root),
        "scientific_gate": "DESCRIPTIVE_ONLY",
        "config_hash": digest,
        "provenance": provenance,
        "elapsed_seconds": time.perf_counter() - started,
    }
    (destination / "manifest.json").write_text(
        json.dumps({"schema_version": 1, "records": manifest}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (destination / "summary.json").write_text(
        json.dumps(summary, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with (destination / "robustness_table.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        fields = [
            "condition",
            "planned",
            "valid",
            "median_Fraw",
            "median_Fse",
            "median_effect",
            "median_eta",
            "median_theta_stationarity",
            "median_parameter_stationarity",
            "median_state_rmse",
        ]
        writer = csv.writer(stream)
        writer.writerow(fields)
        for label, values in sorted(groups.items()):
            writer.writerow([label, *(values[field] for field in fields[1:])])
    return summary
