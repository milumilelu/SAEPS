"""One-shot V5.2B fresh held-out nonlinear profile bridge."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Callable

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.io_utils import write_json_atomic
from saeps.p4_screening import _stationarity
from saeps.provenance import environment_provenance
from saeps.scalar import scalar_residual, solve_truth, train_scalar_checkpoint
from saeps.v3.foundation import _reduce_hessian
from saeps.v31.local_minimum import exact_state_diagnostics, optimize_state_local_minimum
from saeps.v31.pipeline import _mean_residual_objective
from saeps.v35.engineering import scaled_augmented_lsqr_candidates
from saeps.v36.pipeline import _center_specs
from saeps.v41.numerics import explicit_curvature_reference
from saeps.v43.center import allen_center_candidates
from saeps.v5.finite_gamma import _full_hessian_blocks, _runtime
from saeps.v5.governance import NEW_CHECKPOINT_ROLE, sha256_file
from saeps.v5.profile_engineering import _local_specification
from saeps.v5.reconstruction import _point_tensors, _tensor_digest


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]
SEEDS = [200, 201, 202, 203, 204]


def _verify(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    development = json.loads(
        (root / "docs/evidence/v5/V5_PROFILE_DEVELOPMENT_AUDIT.json").read_text(encoding="utf-8")
    )
    if development.get("heldout_authorized") is not True:
        raise RuntimeError("V5.2B held-out was not authorized by V5.2A")
    freeze = json.loads(
        (root / "configs/v5/PROFILE_HELDOUT_EXECUTABLE_FREEZE.json").read_text(encoding="utf-8")
    )
    if freeze.get("execution_authorized") is not True:
        raise RuntimeError("V5.2B executable freeze does not authorize execution")
    for relative, expected in freeze["file_sha256"].items():
        if sha256_file(root / relative) != expected:
            raise RuntimeError(f"V5.2B frozen file mismatch: {relative}")
    return (
        json.loads((root / "configs/v5/PROFILE_OPTIMIZER_LOCK.json").read_text(encoding="utf-8")),
        load_config(root / "configs/v5/profile_bridge.yaml"),
    )


def _save_checkpoint(
    root: Path,
    seed: int,
    theta: torch.Tensor,
    parameter: torch.Tensor,
    points: Any,
    status: str,
    provenance: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    directory = root / f"outputs/runs/v5/checkpoints/profile_heldout/seed_{seed}"
    directory.mkdir(parents=True, exist_ok=False)
    artifact = directory / "model_state.pt"
    point_tensors = _point_tensors(points)
    torch.save(
        {
            "theta": theta.detach().cpu().clone(),
            "coordinate": parameter.detach().cpu().clone(),
            "source_seed": seed,
            "benchmark": "Allen-Cahn",
            "points": point_tensors,
            "model_metadata": {"hidden_width": 8, "cohort": "V5.2B_fresh_heldout"},
        },
        artifact,
    )
    artifact_hash = sha256_file(artifact)
    source = "configs/v5/profile_bridge.yaml"
    manifest = {
        "schema_version": 1,
        "artifact_role": NEW_CHECKPOINT_ROLE,
        "source_protocol": source,
        "source_config_hash": sha256_file(root / source),
        "source_seed": seed,
        "reconstruction_commit": provenance["git_commit"],
        "model_state_path": artifact.relative_to(root).as_posix(),
        "model_state_hash": artifact_hash,
        "diagnostic_set_hash": _tensor_digest(point_tensors),
        "dtype": str(theta.dtype).removeprefix("torch."),
        "device": str(theta.device),
        "environment": provenance,
        "status": status,
        "attempt": 1,
        "retry_permitted": False,
        "replacement_permitted": False,
    }
    write_json_atomic(directory / "checkpoint_manifest.json", manifest)
    return manifest, artifact_hash


def _profile(
    root: Path,
    residual_function: ResidualFunction,
    theta0: torch.Tensor,
    parameter0: torch.Tensor,
    gamma: float,
    h_values: list[float],
    exact_value: float | None,
) -> dict[str, Any]:
    local = _local_specification(root, 1.0e-6)
    m = int(residual_function(theta0, parameter0).numel())
    center_objective = _mean_residual_objective(
        residual_function, parameter0, theta0, gamma, True
    )
    center_loss = float(center_objective(theta0).item())
    losses: dict[float, float] = {}
    points = []
    for h in h_values:
        for sign in [-1.0, 1.0]:
            offset = sign * h
            coordinate = parameter0 + offset * torch.ones_like(parameter0)
            objective = _mean_residual_objective(
                residual_function, coordinate, theta0, gamma, True
            )
            started = time.perf_counter()
            optimized, optimization = optimize_state_local_minimum(objective, theta0, local)
            diagnostics = None
            loss = None
            status = "PROFILE_FAILURE"
            if optimized is not None:
                diagnostics, _, _, _ = exact_state_diagnostics(objective, optimized, local)
                loss = float(objective(optimized).item())
                if diagnostics["local_minimum_gate"] == "PASS":
                    status = "PASS"
                    losses[offset] = loss
            points.append(
                {
                    "h": h,
                    "sign": int(sign),
                    "offset": offset,
                    "start": "independent_common_theta0",
                    "status": status,
                    "loss_mean": loss,
                    "exact_diagnostics": diagnostics,
                    "optimization": optimization,
                    "elapsed_seconds": time.perf_counter() - started,
                }
            )
    curvatures = []
    for h in h_values:
        value = (
            m * (losses[h] - 2.0 * center_loss + losses[-h]) / (h * h)
            if h in losses and -h in losses
            else None
        )
        curvatures.append({"h": h, "curvature": value})
    by_h = {row["h"]: row["curvature"] for row in curvatures}
    finest, previous = by_h[0.005], by_h[0.01]
    exact_error = (
        abs(finest - exact_value) / max(abs(exact_value), 1.0e-8)
        if finest is not None and exact_value is not None
        else None
    )
    change = (
        abs(finest - previous) / max(abs(finest), 1.0e-8)
        if finest is not None and previous is not None
        else None
    )
    return {
        "objective": "0.5_mean_residual_squared_plus_gamma_over_2m_state_displacement_squared",
        "independent_start_from_common_theta0": True,
        "continuation_used": False,
        "center_loss_mean": center_loss,
        "points": points,
        "curvatures": curvatures,
        "all_8_profile_points_pass": len(points) == 8
        and all(row["status"] == "PASS" for row in points),
        "two_smallest_curvatures_finite": all(
            value is not None and math.isfinite(value) for value in [finest, previous]
        ),
        "finest_profile_exact_relative_error": exact_error,
        "last_two_curvature_relative_change": change,
    }


def _run_seed(
    root: Path,
    seed: int,
    provenance: dict[str, Any],
    lock: dict[str, Any],
    bridge: dict[str, Any],
) -> dict[str, Any]:
    destination = root / f"outputs/runs/v5/profile_bridge/seed_{seed}"
    if destination.exists():
        raise RuntimeError("V5.2B seed already has a terminal record; rerun forbidden")
    destination.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    runtime, runtime_hashes, benchmark = _runtime(root, "allen_cahn")
    truth = solve_truth(runtime, benchmark)
    checkpoint, points = train_scalar_checkpoint(runtime, benchmark, seed, truth)
    residual_function: ResidualFunction = lambda state, coordinate: scalar_residual(
        state, coordinate, benchmark, points, truth, runtime
    )
    parameter = checkpoint.log_parameter.detach().clone()
    curvature = load_config(root / "configs/v3_6/locked_scalar_confirmation.yaml")
    objective = _mean_residual_objective(
        residual_function, parameter, checkpoint.theta, 0.0, False
    )
    local, _ = _center_specs(curvature)
    development = load_config(root / "configs/v4_3/allen_cahn_development.yaml")
    theta, center = allen_center_candidates(
        lambda state: residual_function(state, parameter),
        objective,
        checkpoint.theta,
        seed,
        local,
        development["center_engineering"],
    )
    selected = theta if theta is not None else checkpoint.theta
    center_stationarity = None
    center_pass = False
    if theta is not None:
        linearization = ResidualLinearization(residual_function, theta, parameter)
        residual = linearization.residual()
        jt, jl = linearization.explicit_jacobians()
        selected_diagnostics = center["candidates"][int(center["selected_candidate"])]
        g_theta = float(
            selected_diagnostics["final_exact_diagnostics"]["normalized_objective_gradient"]
        )
        s_theta = _stationarity(jt, residual)
        s_lambda = _stationarity(jl, residual)
        center_stationarity = {"G_theta": g_theta, "S_theta": s_theta, "S_lambda": s_lambda}
        center_pass = (
            g_theta < float(curvature["center"]["required_objective_gradient_tolerance"])
            and s_theta < float(curvature["center"]["residual_stationarity_tolerance"])
        )
    checkpoint_status = "PASS" if center_pass else "CHECKPOINT_INVALID"
    manifest, model_hash = _save_checkpoint(
        root, seed, selected, parameter, points, checkpoint_status, provenance
    )
    record: dict[str, Any] = {
        "schema_version": 1,
        "phase": "V5_2B_PROFILE_BRIDGE_HELDOUT",
        "role": "fresh_heldout_profile_bridge",
        "benchmark": benchmark,
        "seed": seed,
        "status": checkpoint_status,
        "binding_valid": False,
        "failure_stage": None if center_pass else "center",
        "failure_reason": None if center_pass else "frozen center gate failed",
        "config_hash": config_hash(bridge),
        "source_hashes": {
            "profile_optimizer_lock": sha256_file(root / "configs/v5/PROFILE_OPTIMIZER_LOCK.json"),
            "checkpoint_manifest": sha256_file(
                root / f"outputs/runs/v5/checkpoints/profile_heldout/seed_{seed}/checkpoint_manifest.json"
            ),
            "model_state": model_hash,
            **runtime_hashes,
        },
        "provenance": provenance,
        "training": {
            "loss_mean": checkpoint.training_loss,
            "state_rmse_validation_only": checkpoint.state_rmse,
            "parameter_relative_error_validation_only": checkpoint.parameter_relative_error,
            "stop_reason": checkpoint.stop_reason,
            "seconds": checkpoint.elapsed_seconds,
        },
        "center": center,
        "center_stationarity": center_stationarity,
        "checkpoint_manifest": manifest,
        "diagnostic_set_hash": manifest["diagnostic_set_hash"],
        "F_raw": None,
        "F_se_GN_explicit": None,
        "F_se_GN_matrix_free": None,
        "H_red_exact_gamma": None,
        "E_raw": None,
        "E_SAEPS": None,
        "D": None,
        "PROFILE_EVALUABLE": False,
        "PROFILE_VALID": False,
        "profile": None,
    }
    if center_pass and theta is not None:
        linearization = ResidualLinearization(residual_function, theta, parameter)
        residual = linearization.residual()
        jt, jl = linearization.explicit_jacobians()
        lambda_max = float(torch.linalg.svdvals(jt)[0].square().item())
        gamma = 1.0e-8 * lambda_max
        raw = float(torch.dot(jl[:, 0], jl[:, 0]).item())
        explicit = explicit_curvature_reference(jt, jl, gamma)
        solver_spec = curvature["curvature_solver"]
        candidates = scaled_augmented_lsqr_candidates(
            linearization,
            jl[:, 0],
            gamma,
            float(solver_spec["tolerance"]),
            int(solver_spec["max_iterations_per_pass"]),
            int(solver_spec["refinement_passes"]),
        )
        solved = candidates["scaled_LSQR_iterative_refinement"]
        fse = float(solved["Fse"])
        solver_error = abs(fse - float(explicit["Fse_explicit"])) / max(
            abs(float(explicit["Fse_explicit"])), 1.0e-30
        )
        solver_pass = (
            explicit["parameter_reference_status"] == "PASS"
            and solved["verified_original_relative_normal_residual"]
            <= float(solver_spec["verified_normal_residual_acceptance"])
            and solver_error <= float(solver_spec["explicit_reference_relative_acceptance"])
            and solved["total_iterations"] <= int(solver_spec["maximum_total_iterations"])
        )
        h_tt, h_tl, h_ll, symmetry = _full_hessian_blocks(residual_function, theta, parameter)
        exact = _reduce_hessian(
            h_tt + gamma * torch.eye(theta.numel(), dtype=theta.dtype),
            h_tl,
            h_tl.T,
            h_ll,
            curvature["gold_standard"],
        )
        exact_value = float(exact["reduced_hessian"][0][0]) if exact["reduced_hessian"] else None
        exact_pass = (
            exact["status"] == "PASS"
            and symmetry <= float(curvature["gold_standard"]["symmetry_relative_tolerance"])
        )
        profile = _profile(
            root,
            residual_function,
            theta,
            parameter,
            gamma,
            [float(value) for value in bridge["h_values"]],
            exact_value,
        )
        evaluable = (
            center_pass
            and exact_pass
            and profile["all_8_profile_points_pass"]
            and profile["two_smallest_curvatures_finite"]
        )
        valid = (
            evaluable
            and profile["finest_profile_exact_relative_error"]
            <= float(bridge["profile_valid_requires"]["finest_profile_exact_relative_error_max"])
            and profile["last_two_curvature_relative_change"]
            <= float(bridge["profile_valid_requires"]["last_two_curvature_relative_change_max"])
        )
        denominator = max(abs(exact_value), 1.0e-8) if exact_value is not None else None
        record.update(
            {
                "gamma_alpha": 1.0e-8,
                "gamma": gamma,
                "lambda_max": lambda_max,
                "m": int(residual.numel()),
                "n_theta": int(theta.numel()),
                "F_raw": raw,
                "F_se_GN_explicit": float(explicit["Fse_explicit"]),
                "F_se_GN_matrix_free": fse,
                "H_red_exact_gamma": exact_value,
                "E_raw": None if denominator is None else abs(raw - exact_value) / denominator,
                "E_SAEPS": None if denominator is None else abs(fse - exact_value) / denominator,
                "D": None
                if denominator is None
                else abs(raw - exact_value) / denominator - abs(fse - exact_value) / denominator,
                "parameter_reference": explicit,
                "curvature_solver": {
                    "status": "PASS" if solver_pass else "SOLVER_FAILURE",
                    "verified_original_relative_normal_residual": solved[
                        "verified_original_relative_normal_residual"
                    ],
                    "explicit_relative_error": solver_error,
                    "iterations": solved["total_iterations"],
                    "setup_jvp_count": candidates["setup_jvp_count"],
                },
                "exact_reference": {**exact, "full_hessian_symmetry_relative_error": symmetry},
                "profile": profile,
                "PROFILE_EVALUABLE": evaluable,
                "PROFILE_VALID": valid,
                "binding_valid": evaluable and solver_pass,
                "status": "PASS"
                if evaluable and solver_pass
                else "SOLVER_FAILURE"
                if not solver_pass
                else "PROFILE_FAILURE",
                "failure_stage": None
                if evaluable and solver_pass
                else "curvature_solver"
                if not solver_pass
                else "profile_or_exact",
                "failure_reason": None
                if evaluable and solver_pass
                else "frozen held-out numerical chain failed",
            }
        )
    record["elapsed_seconds"] = time.perf_counter() - started
    write_json_atomic(destination / "result.json", record)
    return record


def run_profile_heldout(repo_root: str | Path) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    lock, bridge = _verify(root)
    provenance = environment_provenance(root, "float64", "cpu")
    if provenance["git_dirty"]:
        raise RuntimeError("V5.2B requires a clean committed executable")
    for seed in SEEDS:
        if (root / f"outputs/runs/v5/profile_bridge/seed_{seed}").exists() or (
            root / f"outputs/runs/v5/checkpoints/profile_heldout/seed_{seed}"
        ).exists():
            raise RuntimeError("V5.2B cohort has prior output; rerun forbidden")
    return [_run_seed(root, seed, provenance, lock, bridge) for seed in SEEDS]
