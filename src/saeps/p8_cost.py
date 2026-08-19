"""Auditable wall-clock cost benchmark using the locked scalar workflow."""

from __future__ import annotations

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
from saeps.p4_screening import _profile_checkpoint, _stationarity
from saeps.p5_confirmation import _frozen_profile, _profile_config, _runtime_config
from saeps.provenance import environment_provenance, make_run_id
from saeps.scalar import (
    refine_scalar_checkpoint,
    scalar_residual,
    solve_truth,
    train_scalar_checkpoint,
)


def _timed(call: Any) -> tuple[Any, float]:
    started = time.perf_counter()
    value = call()
    return value, time.perf_counter() - started


def _median(records: list[dict[str, Any]], key: str) -> float | None:
    values = [float(record[key]) for record in records if record.get(key) is not None]
    return statistics.median(values) if values else None


def _record(
    seed: int,
    config: dict[str, Any],
    locked: dict[str, Any],
    truth: Any,
    profile_config: dict[str, Any],
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
    gates = locked["stationarity_gates"]
    if (
        theta_stationarity > float(gates["theta"])
        or parameter_stationarity > float(gates["parameter"])
    ) and locked["additional_training"]["enabled"]:
        checkpoint = refine_scalar_checkpoint(
            config, checkpoint, points, truth, locked["additional_training"]
        )
        retry_used = True
        (
            linearization,
            jacobian_theta,
            theta_stationarity,
            parameter_stationarity,
        ) = linearize(checkpoint)

    checkpoint_gate_pass = (
        theta_stationarity <= float(gates["theta"])
        and parameter_stationarity <= float(gates["parameter"])
        and checkpoint.state_rmse
        <= float(locked["checkpoint_gates"]["state_rmse_max_validation_only"])
    )
    result: dict[str, Any] = {
        "seed": seed,
        "status": "PASS",
        "failure_reason": None,
        "split": "cost_only_development",
        "retry_used": retry_used,
        "checkpoint_gate_pass": checkpoint_gate_pass,
        "theta_stationarity": theta_stationarity,
        "parameter_stationarity": parameter_stationarity,
        "state_rmse_validation_only": checkpoint.state_rmse,
        "training_seconds": checkpoint.elapsed_seconds,
        "peak_memory_bytes": None,
        "peak_memory_reason": (
            "Native peak CPU tensor memory is not reliably exposed by the selected "
            "PyTorch backend; Python allocation peaks would be misleading."
        ),
    }

    gamma = float(locked["gamma"]["nominal_alpha"]) * float(
        torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item()
    )
    try:
        saeps, saeps_seconds = _timed(
            lambda: compute_matrix_free_saeps(
                linearization,
                gamma,
                float(locked["gamma"]["cg_tolerance"]),
                int(locked["gamma"]["cg_max_iterations"]),
            )
        )
        result.update(
            {
                "gamma": gamma,
                "saeps_seconds": saeps_seconds,
                "CG_iterations": [solve.iterations for solve in saeps.solves],
                "CG_relative_residual": [
                    solve.relative_residual for solve in saeps.solves
                ],
                "JVP_count": saeps.operation_counts.get("jvp_theta", 0)
                + saeps.operation_counts.get("jvp_parameter", 0),
                "VJP_count": saeps.operation_counts.get("vjp_theta", 0),
            }
        )
    except Exception as error:
        result.update(
            {
                "status": "SOLVER_FAILURE",
                "failure_reason": f"SAEPS: {type(error).__name__}: {error}",
                "saeps_seconds": None,
                "CG_iterations": None,
                "CG_relative_residual": None,
                "JVP_count": None,
                "VJP_count": None,
            }
        )

    frozen, frozen_seconds = _timed(
        lambda: _frozen_profile(
            checkpoint, points, truth, config, profile_config
        )
    )
    reoptimized, reoptimized_seconds = _timed(
        lambda: _profile_checkpoint(
            checkpoint, points, truth, config, profile_config
        )
    )
    result.update(
        {
            "frozen_profile_seconds": frozen_seconds,
            "frozen_profile_status": frozen["fit_status"],
            "reoptimized_profile_seconds": reoptimized_seconds,
            "reoptimized_profile_status": reoptimized["fit_status"],
            "reoptimized_point_statuses": reoptimized["statuses"],
            "reoptimized_to_saeps_ratio": (
                reoptimized_seconds / float(result["saeps_seconds"])
                if result.get("saeps_seconds")
                else None
            ),
        }
    )
    return result


def _write_figure(path: Path, medians: dict[str, float | None]) -> None:
    labels = ["training", "SAEPS", "frozen profile", "reoptimized profile"]
    keys = [
        "training_seconds",
        "saeps_seconds",
        "frozen_profile_seconds",
        "reoptimized_profile_seconds",
    ]
    values = [float(medians[key] or 0.0) for key in keys]
    maximum = max(values, default=1.0) or 1.0
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="460">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="380" y="30" text-anchor="middle" font-size="18" font-weight="bold">Figure 6 — Median computational cost</text>',
        '<line x1="80" y1="390" x2="730" y2="390" stroke="black"/>',
        '<line x1="80" y1="55" x2="80" y2="390" stroke="black"/>',
    ]
    colors = ["#999999", "#0072B2", "#56B4E9", "#D55E00"]
    for index, (label, value, color) in enumerate(zip(labels, values, colors)):
        x = 120 + index * 150
        bar_height = 300 * value / maximum
        lines.append(
            f'<rect x="{x}" y="{390-bar_height:.2f}" width="75" height="{bar_height:.2f}" fill="{color}"/>'
        )
        lines.append(
            f'<text x="{x+37.5}" y="{375-bar_height:.2f}" text-anchor="middle" font-size="12">{value:.4g} s</text>'
        )
        lines.append(
            f'<text x="{x+37.5}" y="415" text-anchor="middle" font-size="12">{label}</text>'
        )
    lines.extend(
        [
            '<text x="22" y="225" text-anchor="middle" font-size="14" transform="rotate(-90 22 225)">wall seconds</text>',
            '</svg>',
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def run_cost_benchmark(
    cost_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    cost = load_config(cost_path)
    root = Path(repo_root)
    locked_path = root / cost["source_config"]
    locked = load_config(locked_path)
    config = _runtime_config(locked)
    profile_config = _profile_config(locked)
    truth = solve_truth(config, "Burgers")
    provenance = environment_provenance(root, locked["dtype"], locked["device"])
    digest = config_hash(cost)
    run_id = make_run_id("P8-cost", int(cost["seeds"][0]), digest, provenance["timestamp"])
    destination = Path(output_root) / run_id
    records_dir = destination / "records"
    records_dir.mkdir(parents=True, exist_ok=False)

    records = [
        _record(int(seed), config, locked, truth, profile_config)
        for seed in cost["seeds"]
    ]
    manifest = []
    for record in records:
        path = records_dir / f"seed_{record['seed']}.json"
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

    timing_keys = [
        "training_seconds",
        "saeps_seconds",
        "frozen_profile_seconds",
        "reoptimized_profile_seconds",
    ]
    medians = {key: _median(records, key) for key in timing_keys}
    ratios = [
        float(record["reoptimized_to_saeps_ratio"])
        for record in records
        if record.get("reoptimized_to_saeps_ratio") is not None
    ]
    summary = {
        "schema_version": 1,
        "phase": "P8",
        "run_id": run_id,
        "engineering_gate": "PASSED" if len(records) == len(cost["seeds"]) else "FAILED",
        "scientific_gate": "DESCRIPTIVE_ONLY",
        "planned": len(cost["seeds"]),
        "completed": len(records),
        "status_counts": {
            status: sum(record["status"] == status for record in records)
            for status in ["PASS", "SOLVER_FAILURE"]
        },
        "median_times_seconds": medians,
        "median_paired_reoptimized_to_saeps_ratio": (
            statistics.median(ratios) if ratios else None
        ),
        "ratio_of_median_reoptimized_to_median_saeps": (
            float(medians["reoptimized_profile_seconds"])
            / float(medians["saeps_seconds"])
            if medians["reoptimized_profile_seconds"] is not None
            and medians["saeps_seconds"] is not None
            else None
        ),
        "peak_memory_bytes": None,
        "peak_memory_reason": records[0]["peak_memory_reason"],
        "cost_config_hash": digest,
        "locked_scalar_file_sha256": hashlib.sha256(locked_path.read_bytes()).hexdigest(),
        "provenance": provenance,
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
    with (destination / "table4_cost.csv").open("w", encoding="utf-8", newline="") as stream:
        fields = [
            "seed",
            "status",
            "training_seconds",
            "saeps_seconds",
            "frozen_profile_seconds",
            "reoptimized_profile_seconds",
            "reoptimized_to_saeps_ratio",
            "CG_iterations",
            "JVP_count",
            "VJP_count",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    _write_figure(destination / "figure6_computational_cost.svg", medians)
    return summary
