"""Gamma-primary profiles with continuation and optimization-accuracy audits."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.core import explicit_tikhonov_operator
from saeps.p4_screening import _stationarity
from saeps.p5_confirmation import _runtime_config
from saeps.provenance import environment_provenance, make_run_id
from saeps.scalar import scalar_residual, solve_truth, train_scalar_checkpoint
from saeps.v3.foundation import full_hessian_references
from saeps.v31.local_minimum import optimize_state_local_minimum
from saeps.v31.pipeline import V2_SCALAR_SHA256, _krylov_gate, _mean_residual_objective


ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def _accuracy_local_specification(
    base: dict[str, Any], tolerance: float
) -> dict[str, Any]:
    specification = copy.deepcopy(base)
    specification["normalized_gradient_tolerance"] = tolerance
    specification["stopping"]["normalized_gradient"] = tolerance
    return specification


def _profile_level(
    residual_function: ResidualFunction,
    theta_center: torch.Tensor,
    parameter_center: torch.Tensor,
    gamma: float,
    matched: bool,
    h_values: list[float],
    local_specification: dict[str, Any],
    convergence_specification: dict[str, Any],
    accuracy_name: str,
) -> dict[str, Any]:
    residual_count = int(residual_function(theta_center, parameter_center).numel())
    center_objective = _mean_residual_objective(
        residual_function, parameter_center, theta_center, gamma, matched
    )
    center_loss = float(center_objective(theta_center).item())
    ascending = sorted(h_values)
    records: dict[float, dict[str, Any]] = {}
    branch_records: dict[str, list[dict[str, Any]]] = {"negative": [], "positive": []}

    for sign, branch_name in [(-1.0, "negative"), (1.0, "positive")]:
        parent_state: torch.Tensor | None = theta_center
        parent_offset = 0.0
        for h in ascending:
            offset = sign * h
            parameter = parameter_center + offset * torch.ones_like(parameter_center)
            if parent_state is None:
                record = {
                    "offset": offset,
                    "parent_offset": parent_offset,
                    "branch": branch_name,
                    "status": "NUMERICAL_FAILURE",
                    "failure_reason": "continuation parent failed; restart from center forbidden",
                    "loss_mean": None,
                    "optimization": None,
                }
            else:
                objective = _mean_residual_objective(
                    residual_function, parameter, theta_center, gamma, matched
                )
                optimized, optimization = optimize_state_local_minimum(
                    objective, parent_state, local_specification
                )
                record = {
                    "offset": offset,
                    "parent_offset": parent_offset,
                    "branch": branch_name,
                    "status": optimization["status"],
                    "failure_reason": optimization["failure_reason"],
                    "loss_mean": float(objective(optimized).item())
                    if optimized is not None
                    else None,
                    "optimization": optimization,
                }
                parent_state = optimized
            records[offset] = record
            branch_records[branch_name].append(record)
            parent_offset = offset

    estimates: list[dict[str, Any]] = []
    for h in h_values:
        negative = records[-h]
        positive = records[h]
        pair_pass = negative["status"] == "PASS" and positive["status"] == "PASS"
        curvature = (
            residual_count
            * (
                float(positive["loss_mean"])
                - 2.0 * center_loss
                + float(negative["loss_mean"])
            )
            / (h * h)
            if pair_pass
            else None
        )
        estimates.append(
            {
                "h": h,
                "curvature": curvature,
                "pair_status": "PASS" if pair_pass else "NUMERICAL_FAILURE",
            }
        )

    convergence = []
    floor = float(convergence_specification["denominator_absolute_floor"])
    tolerance = float(convergence_specification["relative_tolerance"])
    for coarse, fine in zip(estimates, estimates[1:]):
        if coarse["curvature"] is None or fine["curvature"] is None:
            change = None
            passed = False
        else:
            change = abs(float(fine["curvature"]) - float(coarse["curvature"])) / max(
                abs(float(fine["curvature"])), floor
            )
            passed = math.isfinite(change) and change <= tolerance
        convergence.append(
            {
                "coarse_h": coarse["h"],
                "fine_h": fine["h"],
                "relative_change": change,
                "pass": passed,
            }
        )
    required = int(convergence_specification["adjacent_pairs_required"])
    points = [records[offset] for offset in sorted(records)]
    points_pass = len(points) == 8 and all(point["status"] == "PASS" for point in points)
    multiscale_pass = len(convergence[-required:]) == required and all(
        item["pass"] for item in convergence[-required:]
    )
    return {
        "accuracy_level": accuracy_name,
        "gradient_tolerance": float(local_specification["normalized_gradient_tolerance"]),
        "continuation_order": "center_outward_independent_sign_branches",
        "branches": branch_records,
        "points": points,
        "passed_points": sum(point["status"] == "PASS" for point in points),
        "center_loss_mean": center_loss,
        "curvature_estimates_unnormalized": estimates,
        "adjacent_convergence": convergence,
        "finest_curvature": estimates[-1]["curvature"],
        "points_gate": "PASS" if points_pass else "FAIL",
        "multiscale_gate": "PASS" if multiscale_pass else "FAIL",
        "status": "PASS" if points_pass and multiscale_pass else "PROFILE_FAILURE",
    }


def run_accuracy_profile(
    residual_function: ResidualFunction,
    theta_center: torch.Tensor,
    parameter_center: torch.Tensor,
    gamma: float,
    local_specification: dict[str, Any],
    profile_specification: dict[str, Any],
    *,
    matched: bool,
) -> dict[str, Any]:
    h_values = [float(value) for value in profile_specification["h_values"]]
    levels = {}
    for name in ["nominal", "strict"]:
        tolerance = float(profile_specification["accuracy_levels"][name])
        levels[name] = _profile_level(
            residual_function,
            theta_center,
            parameter_center,
            gamma,
            matched,
            h_values,
            _accuracy_local_specification(local_specification, tolerance),
            profile_specification["convergence"],
            name,
        )

    nominal_by_h = {
        item["h"]: item["curvature"]
        for item in levels["nominal"]["curvature_estimates_unnormalized"]
    }
    strict_by_h = {
        item["h"]: item["curvature"]
        for item in levels["strict"]["curvature_estimates_unnormalized"]
    }
    accuracy_specification = profile_specification["accuracy_convergence"]
    finest_count = int(accuracy_specification["finest_scales_required"])
    finest_h = sorted(h_values)[:finest_count]
    floor = float(accuracy_specification["denominator_absolute_floor"])
    tolerance = float(accuracy_specification["relative_tolerance"])
    accuracy_rows = []
    for h in finest_h:
        nominal = nominal_by_h[h]
        strict = strict_by_h[h]
        if nominal is None or strict is None:
            change = None
            passed = False
        else:
            change = abs(float(strict) - float(nominal)) / max(abs(float(strict)), floor)
            passed = math.isfinite(change) and change <= tolerance
        accuracy_rows.append(
            {
                "h": h,
                "nominal_curvature": nominal,
                "strict_curvature": strict,
                "relative_change": change,
                "pass": passed,
            }
        )
    accuracy_pass = len(accuracy_rows) == finest_count and all(
        row["pass"] for row in accuracy_rows
    )
    strict = levels["strict"]
    primary_pass = (
        strict["points_gate"] == "PASS"
        and strict["multiscale_gate"] == "PASS"
        and accuracy_pass
    )
    return {
        "objective": "gamma_matched" if matched else "unregularized",
        "role": "PRIMARY" if matched else "SECONDARY_DIAGNOSTIC",
        "gamma": gamma if matched else 0.0,
        "objective_scaling": (
            "0.5*mean(r^2) + gamma/(2*m)*||theta-theta_center||^2"
            if matched
            else "0.5*mean(r^2)"
        ),
        "accuracy_levels": levels,
        "optimization_accuracy_convergence": accuracy_rows,
        "optimization_accuracy_gate": "PASS" if accuracy_pass else "FAIL",
        "status": "PASS" if primary_pass else "PROFILE_FAILURE",
        "failure_reason": None
        if primary_pass
        else "strict 8/8, strict multiscale, or optimization-accuracy gate failed",
    }


def _primary_comparison(
    jacobian_theta: torch.Tensor,
    jacobian_parameter: torch.Tensor,
    gamma: float,
    exact: dict[str, Any],
    gamma_profile: dict[str, Any],
) -> dict[str, Any]:
    raw = float((jacobian_parameter.T @ jacobian_parameter)[0, 0].item())
    gn = float(
        (
            jacobian_parameter.T
            @ explicit_tikhonov_operator(jacobian_theta, gamma)
            @ jacobian_parameter
        )[0, 0].item()
    )
    exact_value = float(exact["gamma_matched"]["reduced_hessian"][0][0])
    profile_value = float(
        gamma_profile["accuracy_levels"]["strict"]["finest_curvature"]
    )

    def relative(left: float, right: float) -> float:
        return abs(left - right) / max(abs(right), 1.0e-8)

    return {
        "Fraw": raw,
        "Fse_GN_gamma": gn,
        "Hred_exact_gamma": exact_value,
        "Hprofile_gamma": profile_value,
        "relative_error_GN_to_exact": relative(gn, exact_value),
        "relative_error_GN_to_profile": relative(gn, profile_value),
        "relative_error_exact_to_profile": relative(exact_value, profile_value),
        "relative_error_raw_to_profile": relative(raw, profile_value),
        "binding_agreement_threshold": None,
    }


def run_seed20_gamma_primary(
    config_path: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root)
    specification = load_config(config_path)
    if specification["confirmation_authorized"] is not False:
        raise ValueError("v3.2 confirmation must remain unauthorized")
    if int(specification["active_seed"]) != 20:
        raise ValueError("only seed 20 is authorized")
    locked_path = root / specification["source_scalar_config"]
    if hashlib.sha256(locked_path.read_bytes()).hexdigest() != V2_SCALAR_SHA256:
        raise RuntimeError("v2 scalar lock changed")
    locked = load_config(locked_path)
    runtime = _runtime_config(locked)
    provenance = environment_provenance(root, locked["dtype"], locked["device"])
    digest = config_hash(specification)
    run_id = make_run_id("V3-2-gamma-primary", 20, digest, provenance["timestamp"])
    destination = Path(output_root) / run_id
    destination.mkdir(parents=True, exist_ok=False)

    truth = solve_truth(runtime, "Burgers")
    checkpoint, points = train_scalar_checkpoint(runtime, "Burgers", 20, truth)
    residual_function: ResidualFunction = lambda theta, parameter: scalar_residual(
        theta, parameter, "Burgers", points, truth, runtime
    )
    parameter_center = checkpoint.log_parameter.detach().clone()
    center_objective = _mean_residual_objective(
        residual_function, parameter_center, checkpoint.theta, 0.0, False
    )
    theta_center, center = optimize_state_local_minimum(
        center_objective, checkpoint.theta, specification["local_minimum"]
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "phase": specification["phase"],
        "run_id": run_id,
        "seed": 20,
        "split": specification["split"],
        "config_hash": digest,
        "v2_scalar_lock_sha256": V2_SCALAR_SHA256,
        "provenance": provenance,
        "joint_training": {
            "training_seconds": checkpoint.elapsed_seconds,
            "training_loss_mean": checkpoint.training_loss,
            "learned_log_parameter": float(parameter_center[0].item()),
            "learned_parameter": float(torch.exp(parameter_center)[0].item()),
        },
        "common_center": center,
        "center_stationarity": None,
        "gamma": None,
        "gamma_matched_primary": None,
        "unregularized_secondary": None,
        "krylov_gate": None,
        "full_hessian": None,
        "primary_comparison": None,
        "confirmation_authorized": False,
    }

    center_pass = theta_center is not None
    if center_pass:
        linearization = ResidualLinearization(
            residual_function, theta_center, parameter_center
        )
        residual = linearization.residual()
        jacobian_theta, jacobian_parameter = linearization.explicit_jacobians()
        s_theta = _stationarity(jacobian_theta, residual)
        s_lambda = _stationarity(jacobian_parameter, residual)
        center_gradient = float(center["final"]["normalized_objective_gradient"])
        center_pass = (
            center_gradient < float(
                specification["center"]["required_objective_gradient_tolerance"]
            )
            and s_theta < float(specification["center"]["residual_stationarity_tolerance"])
            and center["final"]["hessian_pass"]
        )
        result["center_stationarity"] = {
            "G_theta": center_gradient,
            "G_theta_required_tolerance": float(
                specification["center"]["required_objective_gradient_tolerance"]
            ),
            "S_theta": s_theta,
            "S_theta_tolerance": float(
                specification["center"]["residual_stationarity_tolerance"]
            ),
            "S_lambda": s_lambda,
            "status": "PASS" if center_pass else "NUMERICAL_FAILURE",
        }

    if center_pass:
        gamma = float(specification["gamma"]["alpha"]) * float(
            torch.linalg.eigvalsh(jacobian_theta.T @ jacobian_theta).max().item()
        )
        result["gamma"] = gamma
        gamma_profile = run_accuracy_profile(
            residual_function,
            theta_center,
            parameter_center,
            gamma,
            specification["local_minimum"],
            specification["profile"],
            matched=True,
        )
        result["gamma_matched_primary"] = gamma_profile
        unregularized = run_accuracy_profile(
            residual_function,
            theta_center,
            parameter_center,
            gamma,
            specification["local_minimum"],
            specification["profile"],
            matched=False,
        )
        result["unregularized_secondary"] = unregularized
        krylov = _krylov_gate(linearization, gamma, specification["gamma"])
        result["krylov_gate"] = krylov
        exact = full_hessian_references(
            residual_function,
            theta_center,
            parameter_center,
            gamma,
            specification["full_hessian"],
        )
        result["full_hessian"] = exact
        gamma_exact_pass = exact["gamma_matched"]["status"] == "PASS"
        primary_components_pass = (
            gamma_profile["status"] == "PASS"
            and krylov["status"] == "PASS"
            and krylov["solver_failure_count"] == 0
            and gamma_exact_pass
        )
        if primary_components_pass:
            result["primary_comparison"] = _primary_comparison(
                jacobian_theta,
                jacobian_parameter,
                gamma,
                exact,
                gamma_profile,
            )
    else:
        primary_components_pass = False

    result.update(
        {
            "status": "PASS",
            "engineering_gate": "PASSED",
            "primary_chain_gate": "PASS" if center_pass and primary_components_pass else "FAIL",
            "unregularized_is_binding": False,
            "eligible_to_request_activation_of_seeds_21_24": bool(
                center_pass and primary_components_pass
            ),
            "scientific_gate": "NONE_DEVELOPMENT_ONLY",
        }
    )
    result_path = destination / "result.json"
    result_path.write_text(
        json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "records": [
            {
                "path": "result.json",
                "status": result["status"],
                "sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
            }
        ],
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result
