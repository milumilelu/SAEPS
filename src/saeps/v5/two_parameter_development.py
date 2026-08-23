"""V5.3A center-only development for coupled two-parameter geometry."""

from __future__ import annotations

import copy
import json
import math
import time
from pathlib import Path
from typing import Any

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.io_utils import write_json_atomic
from saeps.multi import multi_residual, train_multi_checkpoint
from saeps.p4_screening import _stationarity
from saeps.provenance import environment_provenance
from saeps.v3.foundation import full_hessian_references
from saeps.v31.local_minimum import exact_state_diagnostics
from saeps.v35.engineering import scaled_augmented_lsqr_candidates
from saeps.v43.center import allen_center_candidates
from saeps.v5.governance import NEW_CHECKPOINT_ROLE, sha256_file
from saeps.v5.reconstruction import _point_tensors, _tensor_digest


SEEDS = [210, 211, 212]


def _relative(first: torch.Tensor, second: torch.Tensor) -> float:
    return float(torch.linalg.matrix_norm(first - second).item()) / max(
        float(torch.linalg.matrix_norm(second).item()), 1.0e-30
    )


def _verify(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    freeze = json.loads(
        (root / "configs/v5/TWO_PARAMETER_DEVELOPMENT_EXECUTABLE_FREEZE.json").read_text(
            encoding="utf-8"
        )
    )
    if freeze.get("execution_authorized") is not True:
        raise RuntimeError("V5.3A executable is not authorized")
    for relative, expected in freeze["file_sha256"].items():
        if sha256_file(root / relative) != expected:
            raise RuntimeError(f"V5.3A frozen file mismatch: {relative}")
    execution = load_config(root / "configs/v5/two_parameter_development_execution.yaml")
    inherited = load_config(root / "configs/v4_6/two_parameter_development.yaml")
    return execution, inherited


def _runtime(root: Path, inherited: dict[str, Any], width: int) -> dict[str, Any]:
    for relative, expected in inherited["protected_sources"].items():
        if sha256_file(root / relative) != expected:
            raise RuntimeError(f"V5.3 protected source mismatch: {relative}")
    runtime = load_config(root / inherited["source_config"])
    runtime["network"]["hidden_width"] = width
    runtime["network"]["architecture"] = f"two_channel_tanh_mlp_2x{width}x1"
    return runtime


def _center_specification(
    root: Path, execution: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    local = copy.deepcopy(load_config(root / "configs/v3_4/curvature_validation.yaml")["local_minimum"])
    local["optimizer"]["outer_steps_max"] = int(
        execution["local_optimizer_extension"]["optimizer_outer_steps_max"]
    )
    local["polish_optimizer"]["outer_steps_max"] = int(
        execution["local_optimizer_extension"]["polish_outer_steps_max"]
    )
    return local, copy.deepcopy(execution["center_policy"])


def _save_checkpoint(
    root: Path,
    seed: int,
    theta: torch.Tensor,
    coordinate: torch.Tensor,
    points: Any,
    status: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    directory = root / f"outputs/runs/v5/checkpoints/two_parameter_development/seed_{seed}"
    directory.mkdir(parents=True, exist_ok=False)
    artifact = directory / "model_state.pt"
    tensors = _point_tensors(points)
    torch.save(
        {
            "theta": theta.detach().cpu().clone(),
            "coordinate": coordinate.detach().cpu().clone(),
            "source_seed": seed,
            "benchmark": "coupled_manufactured_reaction_diffusion",
            "points": tensors,
            "model_metadata": {"hidden_width": 6, "cohort": "V5.3A_development"},
        },
        artifact,
    )
    manifest = {
        "schema_version": 1,
        "artifact_role": NEW_CHECKPOINT_ROLE,
        "source_protocol": "configs/v5/two_parameter_development_execution.yaml",
        "source_config_hash": sha256_file(root / "configs/v5/two_parameter_development_execution.yaml"),
        "source_seed": seed,
        "reconstruction_commit": provenance["git_commit"],
        "model_state_path": artifact.relative_to(root).as_posix(),
        "model_state_hash": sha256_file(artifact),
        "diagnostic_set_hash": _tensor_digest(tensors),
        "dtype": str(theta.dtype).removeprefix("torch."),
        "device": str(theta.device),
        "environment": provenance,
        "status": status,
        "attempt": 1,
        "retry_permitted": False,
        "replacement_permitted": False,
    }
    write_json_atomic(directory / "checkpoint_manifest.json", manifest)
    return manifest


def _run_seed(
    root: Path,
    seed: int,
    provenance: dict[str, Any],
    execution: dict[str, Any],
    inherited: dict[str, Any],
) -> dict[str, Any]:
    destination = root / execution["output_root"] / f"seed_{seed}"
    if destination.exists():
        raise RuntimeError("V5.3A seed already has output; rerun forbidden")
    destination.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    runtime = _runtime(root, inherited, int(execution["architecture_width"]))
    checkpoint, points = train_multi_checkpoint(runtime, seed)
    residual_function = lambda state, coordinate: multi_residual(state, coordinate, points, runtime)
    residual_at = lambda state: residual_function(state, checkpoint.coordinate)
    objective = lambda state: 0.5 * torch.mean(residual_at(state).square())
    local, center_spec = _center_specification(root, execution)
    baseline, _, _, _ = exact_state_diagnostics(objective, checkpoint.theta, local)
    theta = checkpoint.theta
    enhanced = None
    method = "inherited_baseline"
    if baseline["local_minimum_gate"] != "PASS":
        candidate, enhanced = allen_center_candidates(
            residual_at, objective, checkpoint.theta, seed, local, center_spec
        )
        if candidate is not None:
            theta = candidate
            method = center_spec["name"]
    final_center, _, _, _ = exact_state_diagnostics(objective, theta, local)
    linearization = ResidualLinearization(residual_function, theta, checkpoint.coordinate)
    residual = linearization.residual()
    jt, jl = linearization.explicit_jacobians()
    theta_stationarity = _stationarity(jt, residual)
    center_valid = (
        final_center["local_minimum_gate"] == "PASS"
        and theta_stationarity <= 1.0e-4
        and checkpoint.state_rmse
        <= float(inherited["architecture_engineering"]["state_rmse_max_validation_only"])
    )
    manifest = _save_checkpoint(
        root,
        seed,
        theta,
        checkpoint.coordinate,
        points,
        "PASS" if center_valid else "CHECKPOINT_INVALID",
        provenance,
    )
    record: dict[str, Any] = {
        "schema_version": 1,
        "phase": "V5_3A_TWO_PARAMETER_DEVELOPMENT",
        "role": "center_only_development",
        "seed": seed,
        "status": "CHECKPOINT_INVALID",
        "binding_valid": False,
        "failure_stage": "center",
        "failure_reason": "frozen enhanced center gate failed",
        "config_hash": config_hash(execution),
        "source_hashes": {
            "execution": sha256_file(root / "configs/v5/two_parameter_development_execution.yaml"),
            "inherited_protocol": sha256_file(root / "configs/v4_6/two_parameter_development.yaml"),
            "checkpoint_manifest": sha256_file(
                root / f"outputs/runs/v5/checkpoints/two_parameter_development/seed_{seed}/checkpoint_manifest.json"
            ),
            "model_state": manifest["model_state_hash"],
        },
        "provenance": provenance,
        "training": {
            "loss_mean": checkpoint.training_loss,
            "state_rmse_validation_only": checkpoint.state_rmse,
            "parameter_relative_errors_validation_only": list(checkpoint.parameter_relative_errors),
            "seconds": checkpoint.elapsed_seconds,
            "stop_reason": checkpoint.stop_reason,
        },
        "center": {
            "method": method,
            "baseline": baseline,
            "enhanced": enhanced,
            "final": final_center,
            "theta_stationarity": theta_stationarity,
        },
        "solver": None,
        "exact_hessian": None,
        "coupling": None,
        "F_raw": None,
        "F_se_GN_explicit": None,
        "F_se_GN_matrix_free": None,
        "H_red_exact_gamma": None,
        "scientific_comparison": None,
        "selection_forbidden_metrics_computed": False,
    }
    if center_valid:
        lambda_max = float(torch.linalg.svdvals(jt)[0].square().item())
        gamma = float(execution["gamma_alpha"]) * lambda_max
        raw = jl.T @ jl
        identity = torch.eye(theta.numel(), dtype=theta.dtype)
        explicit = raw - jl.T @ jt @ torch.linalg.solve(
            jt.T @ jt + gamma * identity, jt.T @ jl
        )
        rhs_vectors = [jl[:, 0], jl[:, 1], jl[:, 0] + jl[:, 1]]
        solved_rows = [
            scaled_augmented_lsqr_candidates(
                linearization,
                rhs,
                gamma,
                float(inherited["curvature_solver"]["tolerance"]),
                int(inherited["curvature_solver"]["max_iterations_per_pass"]),
                int(inherited["curvature_solver"]["refinement_passes"]),
            )
            for rhs in rhs_vectors
        ]
        solved = [row["scaled_LSQR_iterative_refinement"] for row in solved_rows]
        values = [float(row["Fse"]) for row in solved]
        off_diagonal = 0.5 * (values[2] - values[0] - values[1])
        matrix_free = torch.tensor(
            [[values[0], off_diagonal], [off_diagonal, values[1]]], dtype=theta.dtype
        )
        residuals = [float(row["verified_original_relative_normal_residual"]) for row in solved]
        iterations = [int(row["total_iterations"]) for row in solved]
        solver_error = _relative(matrix_free, explicit)
        solver_pass = (
            max(residuals)
            <= float(inherited["curvature_solver"]["verified_normal_residual_acceptance"])
            and solver_error
            <= float(inherited["curvature_solver"]["explicit_reference_relative_acceptance"])
            and max(iterations) <= int(inherited["curvature_solver"]["maximum_total_iterations"])
        )
        exact = full_hessian_references(
            residual_function,
            theta,
            checkpoint.coordinate,
            gamma,
            inherited["exact_hessian"],
        )
        matched = exact["gamma_matched"]
        exact_pass = matched["status"] == "PASS"
        gold = (
            torch.tensor(matched["reduced_hessian"], dtype=theta.dtype) if exact_pass else None
        )
        coupling = (
            abs(float(gold[0, 1].item()))
            / math.sqrt(
                max(abs(float(gold[0, 0].item() * gold[1, 1].item())), 1.0e-30)
            )
            if gold is not None
            else None
        )
        coupling_pass = coupling is not None and coupling >= float(inherited["nontrivial_coupling_min"])
        binding = solver_pass and exact_pass and coupling_pass
        record.update(
            {
                "status": "PASS"
                if binding
                else "SOLVER_FAILURE"
                if not solver_pass
                else "NUMERICAL_FAILURE",
                "binding_valid": binding,
                "failure_stage": None
                if binding
                else "curvature_solver"
                if not solver_pass
                else "exact_or_coupling",
                "failure_reason": None
                if binding
                else "frozen V5.3A numerical or coupling gate failed",
                "gamma": gamma,
                "lambda_max": lambda_max,
                "F_raw": raw.tolist(),
                "F_se_GN_explicit": explicit.tolist(),
                "F_se_GN_matrix_free": matrix_free.tolist(),
                "H_red_exact_gamma": gold.tolist() if gold is not None else None,
                "solver": {
                    "status": "PASS" if solver_pass else "SOLVER_FAILURE",
                    "verified_residuals": residuals,
                    "iterations": iterations,
                    "matrix_free_vs_explicit_relative_error": solver_error,
                    "polarization_rhs": ["column_0", "column_1", "column_0_plus_column_1"],
                },
                "exact_hessian": exact,
                "coupling": coupling,
                "coupling_status": "PASS" if coupling_pass else "NUMERICAL_FAILURE",
            }
        )
    record["elapsed_seconds"] = time.perf_counter() - started
    write_json_atomic(destination / "result.json", record)
    return record


def run_two_parameter_development(repo_root: str | Path) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    execution, inherited = _verify(root)
    provenance = environment_provenance(root, "float64", "cpu")
    if provenance["git_dirty"]:
        raise RuntimeError("V5.3A requires a clean committed executable")
    for seed in SEEDS:
        if (root / execution["output_root"] / f"seed_{seed}").exists() or (
            root / f"outputs/runs/v5/checkpoints/two_parameter_development/seed_{seed}"
        ).exists():
            raise RuntimeError("V5.3A cohort has prior output; rerun forbidden")
    return [_run_seed(root, seed, provenance, execution, inherited) for seed in SEEDS]
