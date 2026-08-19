"""P4 development-only screening and deterministic scalar benchmark selection."""

from __future__ import annotations

import hashlib
import copy
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

import torch
import yaml

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.core import MatrixFreeEliminator, explicit_tikhonov_operator
from saeps.profile import ProfileFitError, fit_local_quadratic, profile_reoptimized
from saeps.provenance import environment_provenance, make_run_id
from saeps.scalar import (
    classical_observation_loss,
    scalar_network,
    scalar_residual,
    solve_truth,
    train_scalar_checkpoint,
)
from saeps.solvers import conjugate_gradient


def _stationarity(jacobian: torch.Tensor, residual: torch.Tensor) -> float:
    return float(
        (
            torch.linalg.vector_norm(jacobian.T @ residual)
            / (
                torch.linalg.matrix_norm(jacobian) * torch.linalg.vector_norm(residual)
                + torch.finfo(residual.dtype).eps
            )
        ).item()
    )


def _gamma_sweep(
    linearization: ResidualLinearization,
    jacobian_theta: torch.Tensor,
    jacobian_parameter: torch.Tensor,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    lambda_max = float(torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item())
    fixed = float((jacobian_parameter.T @ jacobian_parameter).item())
    rows: list[dict[str, Any]] = []
    for alpha in config["gamma"]["alpha_grid"]:
        gamma = float(alpha) * lambda_max
        explicit = explicit_tikhonov_operator(jacobian_theta, gamma)
        explicit_eta = float((jacobian_parameter.T @ explicit @ jacobian_parameter).item()) / fixed
        eliminator = MatrixFreeEliminator(
            linearization,
            gamma,
            float(config["gamma"]["cg_tolerance"]),
            int(config["gamma"]["cg_max_iterations"]),
        )
        vector = jacobian_parameter[:, 0]
        rhs = linearization.vjp_theta(vector)
        solve = conjugate_gradient(
            eliminator.normal_operator,
            rhs,
            float(config["gamma"]["cg_tolerance"]),
            int(config["gamma"]["cg_max_iterations"]),
        )
        mf = vector - linearization.jvp_theta(solve.solution)
        explicit_value = explicit @ vector
        comparison = float(
            (
                torch.linalg.vector_norm(mf - explicit_value)
                / (torch.linalg.vector_norm(explicit_value) + torch.finfo(vector.dtype).eps)
            ).item()
        )
        rows.append(
            {
                "gamma_alpha": float(alpha),
                "gamma": gamma,
                "explicit_eta": explicit_eta,
                "cg_converged": solve.converged,
                "cg_iterations": solve.iterations,
                "cg_relative_residual": solve.relative_residual,
                "explicit_mf_relative_error": comparison,
            }
        )
    return rows


def _select_gamma(sweeps: list[list[dict[str, Any]]], config: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    grid = [float(value) for value in config["gamma"]["alpha_grid"]]
    eligible: list[bool] = []
    medians: list[float] = []
    for index in range(len(grid)):
        rows = [sweep[index] for sweep in sweeps]
        eligible.append(
            all(
                row["cg_converged"]
                and row["cg_relative_residual"] <= float(config["gamma"]["cg_acceptance"])
                and row["explicit_mf_relative_error"]
                < float(config["gamma"]["explicit_mf_relative_tolerance"])
                for row in rows
            )
        )
        medians.append(statistics.median(float(row["explicit_eta"]) for row in rows))
    changes = [
        abs(medians[index + 1] - medians[index]) / max(abs(medians[index]), 1.0e-30)
        for index in range(len(grid) - 1)
    ]
    candidates = [
        index
        for index in range(1, len(grid))
        if eligible[index] and changes[index - 1] <= float(config["gamma"]["plateau_relative_tolerance"])
    ]
    if not candidates:
        raise RuntimeError(f"no scalar gamma satisfies locked stability/plateau rule: {eligible}, {changes}")
    selected = candidates[0]
    return grid[selected], {
        "eligible": eligible,
        "median_explicit_eta": medians,
        "adjacent_relative_changes": changes,
        "selected_index": selected,
    }


def _profile_checkpoint(
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

    points_result = profile_reoptimized(
        objective,
        checkpoint.theta,
        checkpoint.log_parameter,
        torch.ones_like(checkpoint.log_parameter),
        offsets,
        profile_config["optimizer"],
        profile_config["stopping"],
    )
    result: dict[str, Any] = {
        "objective_scaling": "0.5 * mean(weighted_residual^2)",
        "statuses": [point.status for point in points_result],
        "losses": [point.loss for point in points_result],
        "failure_reasons": [point.failure_reason for point in points_result],
    }
    try:
        fit = fit_local_quadratic(
            points_result, profile_config["fit_quality"], expected_offsets=offsets
        )
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


def _classical_profile(
    benchmark: str, points: Any, truth: Any, config: dict[str, Any], profile_config: dict[str, Any]
) -> dict[str, Any]:
    offsets = [float(value) for value in config["profile"]["offsets"]]
    truth_parameter = float(config["benchmarks"][benchmark]["truth_parameter"])
    losses = [
        classical_observation_loss(
            config, benchmark, truth_parameter * math.exp(offset), points, truth
        )
        for offset in offsets
    ]
    from saeps.profile import ProfilePoint

    profile_points = [
        ProfilePoint(
            offset,
            torch.tensor([math.log(truth_parameter) + offset], dtype=truth.values.dtype),
            loss,
            "PASS",
            None,
            None,
            0,
            0,
            None,
            None,
            True,
            True,
            True,
        )
        for offset, loss in zip(offsets, losses, strict=True)
    ]
    try:
        fit = fit_local_quadratic(profile_points, profile_config["fit_quality"], offsets)
        return {
            "status": "PASS",
            "offsets": offsets,
            "losses": losses,
            "curvature": fit.curvature,
            "minimum": fit.minimum,
            "r_squared": fit.r_squared,
            "normalized_rmse": fit.normalized_rmse,
        }
    except ProfileFitError as error:
        return {
            "status": "PROFILE_FAILURE",
            "offsets": offsets,
            "losses": losses,
            "failure_reason": str(error),
        }


def _select_candidate(
    candidate_summaries: dict[str, dict[str, Any]]
) -> tuple[str | None, list[dict[str, Any]]]:
    audit: list[dict[str, Any]] = []
    eligible = [name for name, value in candidate_summaries.items() if value["hard_gate_pass"]]
    audit.append({"criterion": "hard_numerical_gates", "remaining": sorted(eligible)})
    if not eligible:
        audit.append(
            {
                "criterion": "selection_stopped",
                "reason": "neither scalar candidate passed hard numerical gates",
            }
        )
        return None, audit
    maximum_stationarity = max(candidate_summaries[name]["stationarity_passing_count"] for name in eligible)
    eligible = [name for name in eligible if candidate_summaries[name]["stationarity_passing_count"] == maximum_stationarity]
    audit.append({"criterion": "stationarity_passing_count", "remaining": sorted(eligible)})
    if len(eligible) > 1:
        maximum_clarity = max(candidate_summaries[name]["classical_clarity"] for name in eligible)
        eligible = [name for name in eligible if candidate_summaries[name]["classical_clarity"] == maximum_clarity]
    audit.append({"criterion": "classical_curvature_clarity", "remaining": sorted(eligible)})
    if len(eligible) > 1:
        minimum_failure = min(candidate_summaries[name]["profile_failure_fraction"] for name in eligible)
        eligible = [name for name in eligible if candidate_summaries[name]["profile_failure_fraction"] == minimum_failure]
    audit.append({"criterion": "reoptimization_failure_rate", "remaining": sorted(eligible)})
    selected = sorted(eligible)[0]
    audit.append({"criterion": "alphabetical_name", "selected": selected})
    return selected, audit


def run_p4_screening(config_path: str | Path, output_root: str | Path, repo_root: str | Path) -> dict[str, Any]:
    started = time.perf_counter()
    config = load_config(config_path)
    profile_config = load_config(Path(repo_root) / config["profile"]["optimizer_source"])
    profile_config = copy.deepcopy(profile_config)
    profile_config["optimizer"].update(config["profile"]["optimizer_amendment"])
    profile_config["stopping"].update(config["profile"]["stopping_amendment"])
    profile_config["fit_quality"].update(config["profile"]["fit_quality_amendment"])
    if config["development_seeds"] != [0, 1, 2] or config["candidates"] != ["Allen-Cahn", "Burgers"]:
        raise ValueError("P4 candidate/seed split violates v2.0")
    candidate_results: dict[str, Any] = {}
    summaries: dict[str, dict[str, Any]] = {}
    for benchmark in config["candidates"]:
        truth = solve_truth(config, benchmark)
        rows: list[dict[str, Any]] = []
        sweeps: list[list[dict[str, Any]]] = []
        for seed in config["development_seeds"]:
            checkpoint, points = train_scalar_checkpoint(config, benchmark, int(seed), truth)
            linearization = ResidualLinearization(
                lambda theta, parameter: scalar_residual(
                    theta, parameter, benchmark, points, truth, config
                ),
                checkpoint.theta,
                checkpoint.log_parameter,
            )
            residual = linearization.residual()
            jacobian_theta, jacobian_parameter = linearization.explicit_jacobians()
            theta_stationarity = _stationarity(jacobian_theta, residual)
            parameter_stationarity = _stationarity(jacobian_parameter, residual)
            sweep = _gamma_sweep(linearization, jacobian_theta, jacobian_parameter, config)
            sweeps.append(sweep)
            profile = _profile_checkpoint(
                checkpoint, points, truth, config, profile_config
            )
            classical = _classical_profile(
                benchmark, points, truth, config, profile_config
            )
            stationarity_pass = (
                theta_stationarity <= float(config["stationarity_gates"]["theta"])
                and parameter_stationarity
                <= float(config["stationarity_gates"]["parameter"])
            )
            rows.append(
                {
                    "seed": int(seed),
                    "checkpoint": {
                        "training_loss": checkpoint.training_loss,
                        "state_rmse_validation_only": checkpoint.state_rmse,
                        "parameter_relative_error_validation_only": checkpoint.parameter_relative_error,
                        "learned_parameter": float(torch.exp(checkpoint.log_parameter)[0].item()),
                        "theta_stationarity": theta_stationarity,
                        "parameter_stationarity": parameter_stationarity,
                        "stationarity_pass": stationarity_pass,
                        "stop_reason": checkpoint.stop_reason,
                        "training_seconds": checkpoint.elapsed_seconds,
                    },
                    "gamma_sweep": sweep,
                    "reoptimized_profile": profile,
                    "classical_profile": classical,
                }
            )
        try:
            nominal_gamma, gamma_evidence = _select_gamma(sweeps, config)
            gamma_pass = True
        except RuntimeError as error:
            nominal_gamma, gamma_evidence, gamma_pass = None, {"failure_reason": str(error)}, False
        stationarity_count = sum(row["checkpoint"]["stationarity_pass"] for row in rows)
        state_pass = all(
            row["checkpoint"]["state_rmse_validation_only"]
            <= float(config["hard_gates"]["state_rmse_max"])
            for row in rows
        )
        profile_point_count = sum(
            len(row["reoptimized_profile"]["statuses"]) for row in rows
        )
        profile_failures = sum(
            status != "PASS"
            for row in rows
            for status in row["reoptimized_profile"]["statuses"]
        )
        profile_failure_fraction = profile_failures / profile_point_count
        profile_fit_passing_count = sum(
            row["reoptimized_profile"]["fit_status"] == "PASS" for row in rows
        )
        maximum_offset = max(abs(float(value)) for value in config["profile"]["offsets"])
        classical_pass = all(
            row["classical_profile"]["status"] == "PASS"
            and abs(float(row["classical_profile"]["minimum"])) <= maximum_offset
            and float(row["classical_profile"]["curvature"]) > 0.0
            for row in rows
        )
        classical_clarity = (
            statistics.median(row["classical_profile"]["r_squared"] for row in rows)
            if classical_pass
            else None
        )
        hard_gate_pass = (
            state_pass
            and stationarity_count >= int(config["hard_gates"]["minimum_valid_checkpoints"])
            and profile_failure_fraction
            <= float(config["hard_gates"]["maximum_profile_failure_fraction"])
            and classical_pass
            and gamma_pass
        )
        summaries[benchmark] = {
            "hard_gate_pass": hard_gate_pass,
            "state_rmse_gate_pass": state_pass,
            "stationarity_passing_count": stationarity_count,
            "profile_failure_fraction": profile_failure_fraction,
            "profile_fit_passing_count": profile_fit_passing_count,
            "classical_profiles_pass": classical_pass,
            "classical_clarity": classical_clarity,
            "gamma_pass": gamma_pass,
            "nominal_gamma_alpha": nominal_gamma,
        }
        candidate_results[benchmark] = {
            "rows": rows,
            "gamma_selection": gamma_evidence,
            "summary": summaries[benchmark],
        }
    selected, selection_audit = _select_candidate(summaries)
    provenance = environment_provenance(repo_root, config["dtype"], "cpu")
    digest = config_hash(config)
    run_id = make_run_id("P4-screening", 0, digest, provenance["timestamp"])
    result = {
        "schema_version": 1,
        "phase": "P4_SCREENING",
        "status": "PASS" if selected is not None else "DEVELOPMENT_FAILURE",
        "run_id": run_id,
        "config_hash": digest,
        "candidate_results": candidate_results,
        "selected_candidate": selected,
        "selection_audit": selection_audit,
        "forbidden_metrics_consulted": [],
        "provenance": provenance,
        "elapsed_seconds": time.perf_counter() - started,
    }
    destination = Path(output_root) / run_id
    destination.mkdir(parents=True, exist_ok=False)
    with (destination / "screening.json").open("w", encoding="utf-8") as stream:
        json.dump(result, stream, allow_nan=False, indent=2, sort_keys=True)
        stream.write("\n")
    return result
