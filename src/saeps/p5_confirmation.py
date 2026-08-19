"""Locked P5 scalar confirmation, aggregation, and paper-facing raw artifacts."""

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
from saeps.p4_screening import _classical_profile, _profile_checkpoint, _stationarity
from saeps.profile import ProfileFitError, fit_local_quadratic, profile_frozen
from saeps.provenance import environment_provenance, make_run_id
from saeps.scalar import (
    refine_scalar_checkpoint,
    scalar_residual,
    solve_truth,
    train_scalar_checkpoint,
)


def _runtime_config(locked: dict[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(locked)
    benchmark = str(locked["selected_benchmark"])
    config["benchmarks"] = {benchmark: copy.deepcopy(locked["benchmark"])}
    return config


def _profile_config(locked: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "optimizer": copy.deepcopy(locked["profile"]["optimizer"]),
        "stopping": copy.deepcopy(locked["profile"]["stopping"]),
        "fit_quality": copy.deepcopy(locked["profile"]["fit_quality"]),
    }


def _frozen_profile(
    checkpoint: Any,
    points: Any,
    reference: Any,
    config: dict[str, Any],
    profile_config: dict[str, Any],
) -> dict[str, Any]:
    offsets = [float(value) for value in config["profile"]["offsets"]]

    def objective(theta: torch.Tensor, coordinate: torch.Tensor) -> torch.Tensor:
        residual = scalar_residual(
            theta, coordinate, checkpoint.benchmark, points, reference, config
        )
        return 0.5 * torch.mean(residual.square())

    values = profile_frozen(
        objective,
        checkpoint.theta,
        checkpoint.log_parameter,
        torch.ones_like(checkpoint.log_parameter),
        offsets,
    )
    result: dict[str, Any] = {
        "offsets": offsets,
        "losses": [point.loss for point in values],
        "statuses": [point.status for point in values],
    }
    try:
        fit = fit_local_quadratic(values, profile_config["fit_quality"], offsets)
        result.update(
            {
                "fit_status": "PASS",
                "curvature": fit.curvature,
                "minimum": fit.minimum,
                "r_squared": fit.r_squared,
                "normalized_rmse": fit.normalized_rmse,
            }
        )
    except ProfileFitError as error:
        result.update({"fit_status": "PROFILE_FAILURE", "fit_failure_reason": str(error)})
    return result


def _bootstrap_interval(values: list[float], specification: dict[str, Any]) -> tuple[float, float] | None:
    if not values:
        return None
    generator = torch.Generator(device="cpu").manual_seed(int(specification["rng_seed"]))
    tensor = torch.tensor(values, dtype=torch.float64)
    medians = torch.empty(int(specification["resamples"]), dtype=torch.float64)
    for index in range(medians.numel()):
        sample = torch.randint(tensor.numel(), (tensor.numel(),), generator=generator)
        medians[index] = torch.median(tensor[sample])
    tail = 0.5 * (1.0 - float(specification["confidence_level"]))
    quantiles = torch.quantile(medians, torch.tensor([tail, 1.0 - tail], dtype=torch.float64))
    return float(quantiles[0].item()), float(quantiles[1].item())


def _classification(planned: int, valid: int, wins: int, median_d: float | None, ci: tuple[float, float] | None) -> str:
    if median_d is not None and median_d <= 0.0:
        return "NOT_SUPPORTED"
    if valid == planned and wins >= 9 and median_d is not None and median_d > 0.0:
        if ci is not None and ci[0] > 0.0:
            return "STRONGLY_SUPPORTED"
        return "SUPPORTED_WITH_UNCERTAINTY"
    if median_d is not None and median_d > 0.0:
        return "PARTIALLY_SUPPORTED"
    return "NOT_SUPPORTED"


def _write_svg(path: Path, records: list[dict[str, Any]]) -> None:
    valid = [record for record in records if record["status"] == "PASS"]
    width, height = 720, 440
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="360" y="28" text-anchor="middle" font-size="18" font-weight="bold">Scalar curvature errors by seed</text>',
        '<line x1="70" y1="380" x2="690" y2="380" stroke="black"/>',
        '<line x1="70" y1="45" x2="70" y2="380" stroke="black"/>',
    ]
    maximum = max(
        [max(record["E_raw"], record["E_saeps"]) for record in valid], default=1.0
    )
    for index, record in enumerate(valid):
        x = 100 + index * (560 / max(len(valid), 1))
        raw_height = 300 * record["E_raw"] / max(maximum, 1.0e-30)
        saeps_height = 300 * record["E_saeps"] / max(maximum, 1.0e-30)
        lines.append(f'<rect x="{x:.1f}" y="{380-raw_height:.1f}" width="16" height="{raw_height:.1f}" fill="#D55E00"/>')
        lines.append(f'<rect x="{x+18:.1f}" y="{380-saeps_height:.1f}" width="16" height="{saeps_height:.1f}" fill="#0072B2"/>')
        lines.append(f'<text x="{x+17:.1f}" y="400" text-anchor="middle" font-size="12">{record["seed"]}</text>')
    lines.extend(
        [
            '<text x="350" y="425" text-anchor="middle" font-size="14">confirmation seed</text>',
            '<text x="18" y="220" text-anchor="middle" font-size="14" transform="rotate(-90 18 220)">relative curvature error</text>',
            '</svg>',
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def run_p5_confirmation(
    config_path: str | Path, output_root: str | Path, repo_root: str | Path
) -> dict[str, Any]:
    started = time.perf_counter()
    locked = load_config(config_path)
    if locked.get("phase") != "P5_SCALAR_CONFIRMATION":
        raise ValueError("not a locked P5 scalar config")
    seeds = list(locked["confirmation_seeds"])
    if seeds != list(range(10, 20)):
        raise ValueError("P5 confirmation seeds must be exactly 10..19")
    config = _runtime_config(locked)
    profile_config = _profile_config(locked)
    benchmark = str(locked["selected_benchmark"])
    truth = solve_truth(config, benchmark)
    provenance = environment_provenance(repo_root, locked["dtype"], locked["device"])
    digest = config_hash(locked)
    aggregate_id = make_run_id("P5-scalar", 10, digest, provenance["timestamp"])
    destination = Path(output_root) / aggregate_id
    records_dir = destination / "records"
    records_dir.mkdir(parents=True, exist_ok=False)
    records: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for seed in seeds:
        checkpoint, points = train_scalar_checkpoint(config, benchmark, int(seed), truth)

        def linearize(current: Any) -> tuple[Any, torch.Tensor, torch.Tensor, torch.Tensor, float, float]:
            lin = ResidualLinearization(
                lambda theta, parameter: scalar_residual(
                    theta, parameter, benchmark, points, truth, config
                ),
                current.theta,
                current.log_parameter,
            )
            residual = lin.residual()
            jt, jl = lin.explicit_jacobians()
            return lin, residual, jt, jl, _stationarity(jt, residual), _stationarity(jl, residual)

        linearization, residual, jt, jl, state_stationarity, parameter_stationarity = linearize(checkpoint)
        retry_used = False
        if (
            state_stationarity > float(locked["stationarity_gates"]["theta"])
            or parameter_stationarity > float(locked["stationarity_gates"]["parameter"])
        ) and bool(locked["additional_training"]["enabled"]):
            checkpoint = refine_scalar_checkpoint(
                config, checkpoint, points, truth, locked["additional_training"]
            )
            retry_used = True
            linearization, residual, jt, jl, state_stationarity, parameter_stationarity = linearize(checkpoint)
        checkpoint_valid = (
            state_stationarity <= float(locked["stationarity_gates"]["theta"])
            and parameter_stationarity <= float(locked["stationarity_gates"]["parameter"])
            and checkpoint.state_rmse
            <= float(locked["checkpoint_gates"]["state_rmse_max_validation_only"])
        )
        run_started = time.perf_counter()
        record: dict[str, Any] = {
            "schema_version": 1,
            "run_id": f"{aggregate_id}-seed{seed}",
            "timestamp": provenance["timestamp"],
            "git_commit": provenance["git_commit"],
            "config_path": "configs/locked/scalar.yaml",
            "config_hash": digest,
            "seed": seed,
            "split": "confirmation",
            "benchmark": benchmark,
            "architecture": locked["network"]["architecture"],
            "dtype": locked["dtype"],
            "hardware": provenance["processor"] or provenance["machine"],
            "parameter_coordinates": [locked["benchmark"]["coordinate"]],
            "training_points": locked["points"],
            "diagnostic_points": locked["points"],
            "sensor_layout": locked["sensor_layout"],
            "loss_weights": locked["loss_weights"],
            "optimizer": locked["optimizer"],
            "learning_rate": locked["optimizer"]["adam_learning_rate"],
            "training_stop_reason": checkpoint.stop_reason,
            "checkpoint_epoch": checkpoint.adam_epochs,
            "retry_used": retry_used,
            "theta_stationarity": state_stationarity,
            "lambda_stationarity": parameter_stationarity,
            "residuals": {"total_weighted_rms": float(torch.sqrt(torch.mean(residual.square())).item())},
            "state_error": {"value": checkpoint.state_rmse, "validation_only": True},
            "parameter_error": {"value": checkpoint.parameter_relative_error, "validation_only": True},
            "learned_parameter": float(torch.exp(checkpoint.log_parameter)[0].item()),
            "gamma_alpha": float(locked["gamma"]["nominal_alpha"]),
            "profile_points": locked["profile"]["offsets"],
            "training_time": checkpoint.elapsed_seconds,
            "peak_memory": None,
        }
        if not checkpoint_valid:
            record.update(
                {
                    "status": "CHECKPOINT_INVALID",
                    "failure_reason": "locked stationarity/state gate failed after allowed retry",
                    "Fraw": None,
                    "Fse": None,
                    "gse": None,
                    "eta": None,
                    "profile_curvature": None,
                    "profile_fit_quality": None,
                    "E_saeps": None,
                    "E_raw": None,
                    "D_paired": None,
                }
            )
        else:
            lambda_max = float(torch.linalg.eigvalsh(jt.T @ jt).max().item())
            gamma = float(locked["gamma"]["nominal_alpha"]) * lambda_max
            try:
                saeps = compute_matrix_free_saeps(
                    linearization,
                    gamma,
                    float(locked["gamma"]["cg_tolerance"]),
                    int(locked["gamma"]["cg_max_iterations"]),
                )
                frozen = _frozen_profile(
                    checkpoint, points, truth, config, profile_config
                )
                reoptimized = _profile_checkpoint(
                    checkpoint, points, truth, config, profile_config
                )
                classical = _classical_profile(
                    benchmark, points, truth, config, profile_config
                )
                residual_count = residual.numel()
                profile_ok = (
                    frozen.get("fit_status") == "PASS"
                    and reoptimized.get("fit_status") == "PASS"
                    and classical.get("status") == "PASS"
                )
                fraw = float(saeps.raw_curvature[0, 0].item())
                fse = float(saeps.eliminated_curvature[0, 0].item())
                if profile_ok:
                    h_profile = float(reoptimized["curvature"]) * residual_count
                    h_frozen = float(frozen["curvature"]) * residual_count
                    denominator = abs(h_profile) + 1.0e-30
                    e_saeps = abs(fse - h_profile) / denominator
                    e_raw = abs(fraw - h_profile) / denominator
                    d_paired = e_raw - e_saeps
                    status, failure = "PASS", None
                else:
                    h_profile = h_frozen = e_saeps = e_raw = d_paired = None
                    status, failure = "PROFILE_FAILURE", "locked profile/fit/classical rule failed"
                record.update(
                    {
                        "status": status,
                        "failure_reason": failure,
                        "gamma": gamma,
                        "CG_iterations": [solve.iterations for solve in saeps.solves],
                        "CG_relative_residual": [solve.relative_residual for solve in saeps.solves],
                        "JVP_count": saeps.operation_counts.get("jvp_theta", 0)
                        + saeps.operation_counts.get("jvp_parameter", 0),
                        "VJP_count": saeps.operation_counts.get("vjp_theta", 0),
                        "Fraw": [[fraw]],
                        "Fse": [[fse]],
                        "gse": saeps.eliminated_score.tolist(),
                        "eta": float(saeps.eta[0].item()),
                        "frozen_profile": frozen,
                        "reoptimized_profile": reoptimized,
                        "classical_profile": classical,
                        "profile_curvature": h_profile,
                        "frozen_curvature": h_frozen,
                        "profile_fit_quality": (
                            {
                                "r_squared": reoptimized.get("r_squared"),
                                "normalized_rmse": reoptimized.get("normalized_rmse"),
                            }
                            if profile_ok
                            else None
                        ),
                        "eta_profile": (
                            h_profile / (h_frozen + 1.0e-30) if profile_ok else None
                        ),
                        "E_saeps": e_saeps,
                        "E_raw": e_raw,
                        "D_paired": d_paired,
                        "saeps_time": time.perf_counter() - run_started,
                        "frozen_profile_time": None,
                        "reoptimized_profile_time": None,
                    }
                )
            except Exception as error:
                record.update(
                    {
                        "status": "SOLVER_FAILURE",
                        "failure_reason": f"{type(error).__name__}: {error}",
                        "Fraw": None,
                        "Fse": None,
                        "gse": None,
                        "eta": None,
                        "profile_curvature": None,
                        "profile_fit_quality": None,
                        "E_saeps": None,
                        "E_raw": None,
                        "D_paired": None,
                    }
                )
        record_path = records_dir / f"seed_{seed}.json"
        with record_path.open("w", encoding="utf-8") as stream:
            json.dump(record, stream, allow_nan=False, indent=2, sort_keys=True)
            stream.write("\n")
        manifest.append(
            {
                "seed": seed,
                "status": record["status"],
                "path": str(record_path.relative_to(destination)),
                "sha256": hashlib.sha256(record_path.read_bytes()).hexdigest(),
            }
        )
        records.append(record)
    valid = [record for record in records if record["status"] == "PASS"]
    differences = [float(record["D_paired"]) for record in valid]
    wins = sum(value > 0.0 for value in differences)
    median_d = statistics.median(differences) if differences else None
    ci = _bootstrap_interval(differences, locked["bootstrap"])
    classification = _classification(10, len(valid), wins, median_d, ci)
    status_counts = {
        status: sum(record["status"] == status for record in records)
        for status in ["PASS", "CHECKPOINT_INVALID", "PROFILE_FAILURE", "SOLVER_FAILURE", "NUMERICAL_FAILURE"]
    }
    summary = {
        "schema_version": 1,
        "phase": "P5",
        "run_id": aggregate_id,
        "engineering_gate": "PASSED" if len(records) == 10 else "FAILED",
        "scientific_classification_sg2": classification,
        "planned": 10,
        "valid": len(valid),
        "invalid_or_failed": 10 - len(valid),
        "status_counts": status_counts,
        "paired_wins_out_of_planned_10": wins,
        "median_D": median_d,
        "paired_bootstrap_95_ci": list(ci) if ci else None,
        "per_seed": [
            {
                "seed": record["seed"],
                "status": record["status"],
                "E_raw": record.get("E_raw"),
                "E_saeps": record.get("E_saeps"),
                "D_paired": record.get("D_paired"),
                "eta": record.get("eta"),
                "eta_profile": record.get("eta_profile"),
            }
            for record in records
        ],
        "config_hash": digest,
        "provenance": provenance,
        "elapsed_seconds": time.perf_counter() - started,
    }
    with (destination / "manifest.json").open("w", encoding="utf-8") as stream:
        json.dump({"schema_version": 1, "planned": 10, "records": manifest}, stream, indent=2, sort_keys=True)
        stream.write("\n")
    with (destination / "summary.json").open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, allow_nan=False, indent=2, sort_keys=True)
        stream.write("\n")
    with (destination / "table2_scalar.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["seed", "status", "E_raw", "E_saeps", "D_paired", "eta", "eta_profile"])
        writer.writeheader()
        writer.writerows(summary["per_seed"])
    _write_svg(destination / "figure4_curvature_errors.svg", records)
    return summary

