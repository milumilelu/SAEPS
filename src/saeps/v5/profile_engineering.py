"""Independent-start nonlinear profile engineering for V5.2A."""

from __future__ import annotations

import copy
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any, Callable

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.io_utils import write_json_atomic
from saeps.provenance import environment_provenance
from saeps.scalar import scalar_residual, solve_truth
from saeps.v3.foundation import _reduce_hessian
from saeps.v31.local_minimum import exact_state_diagnostics, optimize_state_local_minimum
from saeps.v31.pipeline import _mean_residual_objective
from saeps.v43.center import exact_gauss_newton_refine, multidirection_saddle_escape
from saeps.v5.finite_gamma import _full_hessian_blocks, _load_checkpoint, _runtime
from saeps.v5.governance import sha256_file


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]
CANDIDATE_SEEDS = [70, 71, 72]
VALIDATION_SEEDS = [73, 74]


def _verify_freeze(root: Path) -> dict[str, Any]:
    freeze = json.loads(
        (root / "configs/v5/PROFILE_ENGINEERING_EXECUTABLE_FREEZE.json").read_text(encoding="utf-8")
    )
    if freeze.get("candidate_execution_authorized") is not True:
        raise RuntimeError("V5.2A candidate execution is not authorized")
    for relative, expected in freeze["file_sha256"].items():
        if sha256_file(root / relative) != expected:
            raise RuntimeError(f"V5.2A frozen file mismatch: {relative}")
    return load_config(root / "configs/v5/profile_engineering_execution.yaml")


def _local_specification(root: Path, tolerance: float) -> dict[str, Any]:
    numerical = load_config(root / "configs/v3_6/locked_scalar_confirmation.yaml")
    local = copy.deepcopy(numerical["center"]["local_minimum"])
    local["normalized_gradient_tolerance"] = tolerance
    local["stopping"]["normalized_gradient"] = tolerance
    return local


def _optimize_point(
    *,
    root: Path,
    candidate: str,
    objective: Callable[[torch.Tensor], torch.Tensor],
    residual_function: ResidualFunction,
    theta0: torch.Tensor,
    parameter: torch.Tensor,
    gamma: float,
) -> tuple[torch.Tensor | None, dict[str, Any]]:
    execution = load_config(root / "configs/v5/profile_engineering_execution.yaml")
    candidate_spec = execution["candidates"][candidate]
    local = _local_specification(root, float(candidate_spec["normalized_gradient_tolerance"]))
    if candidate_spec["kind"] == "optimize_state_local_minimum":
        return optimize_state_local_minimum(objective, theta0, local)
    development = load_config(root / "configs/v4_3/allen_cahn_development.yaml")
    engineering = development["center_engineering"]
    residual_count = residual_function(theta0, parameter).numel()
    scale = math.sqrt((residual_count + theta0.numel()) / residual_count)

    def augmented(state: torch.Tensor) -> torch.Tensor:
        return scale * torch.cat(
            [residual_function(state, parameter), math.sqrt(gamma) * (state - theta0)]
        )

    refined, gn = exact_gauss_newton_refine(augmented, theta0, engineering["gauss_newton"])
    selected, audit = multidirection_saddle_escape(
        objective, refined, local, engineering["multidirection_escape"]
    )
    passed = audit["status"] == "PASS"
    return (selected if passed else None), {
        "status": "PASS" if passed else "CHECKPOINT_INVALID",
        "method": "damped_gauss_newton_then_multidirection_exact_gate",
        "gauss_newton": gn,
        "exact_local_audit": audit,
        "failure_reason": None if passed else "profile point exact local-minimum gate failed",
    }


def run_profile_candidate_seed(
    repo_root: str | Path,
    candidate: str,
    seed: int,
    *,
    source_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    execution = _verify_freeze(root)
    if seed not in CANDIDATE_SEEDS:
        raise ValueError("V5.2A candidate seed is outside 70--72")
    if candidate not in execution["candidate_order"]:
        raise ValueError("unknown frozen profile optimizer candidate")
    destination = root / execution["output_root"] / "candidates" / candidate / f"seed_{seed}"
    if destination.exists():
        raise RuntimeError("V5.2A candidate record already exists; rerun forbidden")
    destination.mkdir(parents=True, exist_ok=False)
    provenance = source_provenance or environment_provenance(root, "float64", "cpu")
    if source_provenance is None and provenance["git_dirty"]:
        raise RuntimeError("V5.2A requires a clean committed executable")
    started = time.perf_counter()
    theta0, parameter0, points, manifest, _ = _load_checkpoint(root, "allen_cahn", seed)
    runtime, runtime_hashes, benchmark = _runtime(root, "allen_cahn")
    truth = solve_truth(runtime, benchmark)
    residual_function: ResidualFunction = lambda state, coordinate: scalar_residual(
        state, coordinate, benchmark, points, truth, runtime
    )
    linearization = ResidualLinearization(residual_function, theta0, parameter0)
    jacobian_theta, _ = linearization.explicit_jacobians()
    lambda_max = float(torch.linalg.svdvals(jacobian_theta)[0].square().item())
    gamma = float(execution["gamma_alpha"]) * lambda_max
    h_tt, h_tl, h_ll, symmetry = _full_hessian_blocks(residual_function, theta0, parameter0)
    numerical = load_config(root / "configs/v3_6/locked_scalar_confirmation.yaml")
    identity = torch.eye(theta0.numel(), dtype=theta0.dtype)
    exact = _reduce_hessian(
        h_tt + gamma * identity,
        h_tl,
        h_tl.T,
        h_ll,
        numerical["gold_standard"],
    )
    exact_value = float(exact["reduced_hessian"][0][0]) if exact["reduced_hessian"] else None
    m = int(linearization.residual().numel())
    center_objective = _mean_residual_objective(
        residual_function, parameter0, theta0, gamma, True
    )
    center_loss = float(center_objective(theta0).item())
    points_rows = []
    losses: dict[float, float] = {}
    for h in [float(value) for value in execution["h_values"]]:
        for sign in [-1.0, 1.0]:
            offset = sign * h
            coordinate = parameter0 + offset * torch.ones_like(parameter0)
            objective = _mean_residual_objective(
                residual_function, coordinate, theta0, gamma, True
            )
            point_started = time.perf_counter()
            optimized, optimization = _optimize_point(
                root=root,
                candidate=candidate,
                objective=objective,
                residual_function=residual_function,
                theta0=theta0,
                parameter=coordinate,
                gamma=gamma,
            )
            diagnostics = None
            loss = None
            status = "PROFILE_FAILURE"
            if optimized is not None:
                local = _local_specification(
                    root,
                    float(execution["candidates"][candidate]["normalized_gradient_tolerance"]),
                )
                diagnostics, _, _, _ = exact_state_diagnostics(objective, optimized, local)
                loss = float(objective(optimized).item())
                if diagnostics["local_minimum_gate"] == "PASS":
                    status = "PASS"
                    losses[offset] = loss
            points_rows.append(
                {
                    "h": h,
                    "sign": int(sign),
                    "offset": offset,
                    "start": "independent_common_theta0",
                    "status": status,
                    "loss_mean": loss,
                    "exact_diagnostics": diagnostics,
                    "optimization": optimization,
                    "elapsed_seconds": time.perf_counter() - point_started,
                }
            )
    curvatures = []
    for h in [float(value) for value in execution["h_values"]]:
        curvature = (
            m * (losses[h] - 2.0 * center_loss + losses[-h]) / (h * h)
            if h in losses and -h in losses
            else None
        )
        curvatures.append({"h": h, "curvature": curvature})
    by_h = {row["h"]: row["curvature"] for row in curvatures}
    finest = by_h[0.005]
    previous = by_h[0.01]
    exact_error = (
        abs(finest - exact_value) / max(abs(exact_value), 1.0e-8)
        if finest is not None and exact_value is not None
        else None
    )
    last_change = (
        abs(finest - previous) / max(abs(finest), 1.0e-8)
        if finest is not None and previous is not None
        else None
    )
    all_points_pass = len(points_rows) == 8 and all(row["status"] == "PASS" for row in points_rows)
    exact_pass = (
        exact["status"] == "PASS"
        and symmetry <= float(numerical["gold_standard"]["symmetry_relative_tolerance"])
    )
    record = {
        "schema_version": 1,
        "phase": "V5_2A_PROFILE_ENGINEERING",
        "role": "optimizer_candidate_development",
        "benchmark": benchmark,
        "seed": seed,
        "candidate": candidate,
        "status": "PASS" if all_points_pass and exact_pass else "PROFILE_FAILURE",
        "binding_valid": all_points_pass and exact_pass,
        "failure_stage": None if all_points_pass and exact_pass else "profile_or_exact",
        "failure_reason": None if all_points_pass and exact_pass else "one or more frozen numerical profile nodes failed",
        "config_hash": config_hash(execution),
        "source_hashes": {
            "checkpoint_manifest": sha256_file(
                root / "outputs/runs/v5/checkpoints/allen_cahn" / f"seed_{seed}" / "checkpoint_manifest.json"
            ),
            "model_state": manifest["model_state_hash"],
            **runtime_hashes,
        },
        "provenance": provenance,
        "gamma_alpha": float(execution["gamma_alpha"]),
        "gamma": gamma,
        "lambda_max": lambda_max,
        "diagnostic_set_hash": manifest["diagnostic_set_hash"],
        "m": m,
        "n_theta": int(theta0.numel()),
        "independent_start_from_common_theta0": True,
        "continuation_used": False,
        "center_loss_mean": center_loss,
        "exact_reference": {**exact, "full_hessian_symmetry_relative_error": symmetry},
        "H_red_exact_gamma": exact_value,
        "profile_points": points_rows,
        "curvatures": curvatures,
        "all_8_profile_points_pass": all_points_pass,
        "finest_profile_exact_relative_error": exact_error,
        "last_two_curvature_relative_change": last_change,
        "elapsed_seconds": time.perf_counter() - started,
        "selection_forbidden_metrics_computed": False,
    }
    write_json_atomic(destination / "result.json", record)
    return record


def run_profile_candidate_cohort(repo_root: str | Path) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    execution = _verify_freeze(root)
    provenance = environment_provenance(root, "float64", "cpu")
    if provenance["git_dirty"]:
        raise RuntimeError("V5.2A requires a clean committed executable")
    planned = [
        (candidate, seed)
        for candidate in execution["candidate_order"]
        for seed in CANDIDATE_SEEDS
    ]
    for candidate, seed in planned:
        destination = root / execution["output_root"] / "candidates" / candidate / f"seed_{seed}"
        if destination.exists():
            raise RuntimeError("V5.2A candidate cohort has prior output; rerun forbidden")
    return [
        run_profile_candidate_seed(root, candidate, seed, source_provenance=provenance)
        for candidate, seed in planned
    ]


def select_profile_candidate(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    execution = load_config(root / "configs/v5/profile_engineering_execution.yaml")
    summaries = []
    for order, candidate in enumerate(execution["candidate_order"]):
        rows = [
            json.loads(
                (
                    root
                    / execution["output_root"]
                    / "candidates"
                    / candidate
                    / f"seed_{seed}/result.json"
                ).read_text(encoding="utf-8")
            )
            for seed in CANDIDATE_SEEDS
        ]
        exact_errors = [
            row["finest_profile_exact_relative_error"]
            for row in rows
            if row["finest_profile_exact_relative_error"] is not None
        ]
        changes = [
            row["last_two_curvature_relative_change"]
            for row in rows
            if row["last_two_curvature_relative_change"] is not None
        ]
        summary = {
            "candidate": candidate,
            "complete_seed_count": sum(row["binding_valid"] for row in rows),
            "passing_point_count": sum(
                sum(point["status"] == "PASS" for point in row["profile_points"])
                for row in rows
            ),
            "median_finest_profile_exact_relative_error": statistics.median(exact_errors)
            if exact_errors
            else math.inf,
            "median_last_two_curvature_relative_change": statistics.median(changes)
            if changes
            else math.inf,
            "candidate_order": order,
        }
        summary["selection_key"] = [
            -summary["complete_seed_count"],
            -summary["passing_point_count"],
            summary["median_finest_profile_exact_relative_error"],
            summary["median_last_two_curvature_relative_change"],
            order,
        ]
        summaries.append(summary)
    selected = min(summaries, key=lambda row: row["selection_key"])["candidate"]
    return {
        "schema_version": 1,
        "phase": "V5_2A_PROFILE_ENGINEERING_SELECTION",
        "selected_candidate": selected,
        "selection_rule": execution["selection_rule"],
        "forbidden_metrics_read": False,
        "candidate_summaries": summaries,
    }
