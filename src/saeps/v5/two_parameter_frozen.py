"""Byte-frozen V5.3B/C coupled two-parameter executable."""

from __future__ import annotations

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
from saeps.v5.two_parameter_development import (
    _center_specification,
    _relative,
    _runtime,
)


HELDOUT_SEEDS = [213, 214]
CONFIRMATION_SEEDS = list(range(215, 225))


def _verify(root: Path, role: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    freeze = json.loads(
        (root / "configs/v5/TWO_PARAMETER_FROZEN_EXECUTABLE_FREEZE.json").read_text(
            encoding="utf-8"
        )
    )
    if freeze.get("heldout_execution_authorized") is not True:
        raise RuntimeError("V5.3B held-out is not authorized")
    for relative, expected in freeze["file_sha256"].items():
        if sha256_file(root / relative) != expected:
            raise RuntimeError(f"V5.3 frozen file mismatch: {relative}")
    development_audit = json.loads(
        (root / "docs/evidence/v5/V5_TWO_PARAMETER_DEVELOPMENT_AUDIT.json").read_text(
            encoding="utf-8"
        )
    )
    if development_audit.get("heldout_authorized") is not True:
        raise RuntimeError("V5.3A did not authorize held-out")
    if role == "confirmation":
        authorization_path = root / "configs/v5/TWO_PARAMETER_CONFIRMATION_AUTHORIZATION.json"
        if not authorization_path.is_file():
            raise RuntimeError("V5.3C confirmation authorization is absent")
        authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
        if authorization.get("confirmation_authorized") is not True:
            raise RuntimeError("V5.3C confirmation is not authorized")
        if authorization.get("frozen_executable_sha256") != sha256_file(
            root / "src/saeps/v5/two_parameter_frozen.py"
        ):
            raise RuntimeError("V5.3C authorization does not match frozen executable")
    execution = load_config(root / "configs/v5/two_parameter_frozen_execution.yaml")
    development = load_config(root / "configs/v5/two_parameter_development_execution.yaml")
    inherited = load_config(root / "configs/v4_6/two_parameter_development.yaml")
    return execution, development, inherited


def _whiten(matrix: torch.Tensor, cholesky: torch.Tensor) -> torch.Tensor:
    left = torch.linalg.solve_triangular(cholesky, matrix, upper=False)
    return torch.linalg.solve_triangular(cholesky, left.T, upper=False).T


def _primary_metrics(
    raw: torch.Tensor,
    fse: torch.Tensor,
    exact: torch.Tensor,
    specification: dict[str, Any],
) -> dict[str, Any]:
    tau = float(specification["tau_relative"]) * max(
        float(torch.trace(raw).item()) / 2.0, 1.0
    )
    metric = 0.5 * (raw + raw.T) + tau * torch.eye(2, dtype=raw.dtype)
    cholesky = torch.linalg.cholesky(metric)
    whitened_exact = _whiten(exact, cholesky)
    denominator = float(torch.linalg.matrix_norm(whitened_exact).item()) + float(
        specification["denominator_floor"]
    )
    e_raw = float(torch.linalg.matrix_norm(_whiten(raw - exact, cholesky)).item()) / denominator
    e_saeps = float(torch.linalg.matrix_norm(_whiten(fse - exact, cholesky)).item()) / denominator
    return {
        "tau": tau,
        "B": metric.tolist(),
        "B_whitened_exact": whitened_exact.tolist(),
        "E_raw2": e_raw,
        "E_SAEPS2": e_saeps,
        "D2": e_raw - e_saeps,
    }


def _generalized_geometry(
    fse: torch.Tensor, exact: torch.Tensor, metric: torch.Tensor
) -> dict[str, Any]:
    cholesky = torch.linalg.cholesky(metric)
    transformed = _whiten(fse, cholesky)
    eigenvalues, q = torch.linalg.eigh(0.5 * (transformed + transformed.T))
    vectors = torch.linalg.solve_triangular(cholesky.T, q, upper=True)
    norms = torch.sqrt(torch.sum(vectors * (metric @ vectors), dim=0))
    vectors = vectors / norms
    values = eigenvalues.tolist()
    gap = abs(values[1] - values[0]) / max(abs(values[0]), abs(values[1]), 1.0e-30)
    directional = []
    for index in range(2):
        vector = vectors[:, index]
        directional.append(
            {
                "index": index,
                "B_norm": float(vector @ metric @ vector),
                "SAEPS_curvature": float(vector @ fse @ vector),
                "exact_curvature": float(vector @ exact @ vector),
            }
        )
    return {
        "role": "secondary_nonbinding",
        "eigenvalues": values,
        "eigenvectors_columns": vectors.tolist(),
        "metric_normalization": (vectors.T @ metric @ vectors).tolist(),
        "relative_eigengap": gap,
        "eigengap_threshold": None,
        "directional_curvatures": directional,
        "orientation_enters_adjudication": False,
        "cross_seed_direction_claim_forbidden": True,
    }


def _save_checkpoint(
    root: Path,
    role: str,
    seed: int,
    theta: torch.Tensor,
    coordinate: torch.Tensor,
    points: Any,
    status: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    directory = root / f"outputs/runs/v5/checkpoints/two_parameter_{role}/seed_{seed}"
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
            "model_metadata": {"hidden_width": 6, "cohort": f"V5.3_{role}"},
        },
        artifact,
    )
    manifest = {
        "schema_version": 1,
        "artifact_role": NEW_CHECKPOINT_ROLE,
        "source_protocol": "configs/v5/two_parameter_frozen_execution.yaml",
        "source_config_hash": sha256_file(root / "configs/v5/two_parameter_frozen_execution.yaml"),
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
    role: str,
    seed: int,
    provenance: dict[str, Any],
    execution: dict[str, Any],
    development: dict[str, Any],
    inherited: dict[str, Any],
) -> dict[str, Any]:
    destination = root / execution["output_root"] / role / f"seed_{seed}"
    if destination.exists():
        raise RuntimeError("V5.3 frozen seed already has output; rerun forbidden")
    destination.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    runtime = _runtime(root, inherited, int(development["architecture_width"]))
    checkpoint, points = train_multi_checkpoint(runtime, seed)
    residual_function = lambda state, coordinate: multi_residual(state, coordinate, points, runtime)
    residual_at = lambda state: residual_function(state, checkpoint.coordinate)
    objective = lambda state: 0.5 * torch.mean(residual_at(state).square())
    local, center_spec = _center_specification(root, development)
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
        role,
        seed,
        theta,
        checkpoint.coordinate,
        points,
        "PASS" if center_valid else "CHECKPOINT_INVALID",
        provenance,
    )
    record: dict[str, Any] = {
        "schema_version": 1,
        "phase": "V5_3B_TWO_PARAMETER_HELDOUT"
        if role == "heldout"
        else "V5_3C_TWO_PARAMETER_CONFIRMATION",
        "role": role,
        "seed": seed,
        "status": "CHECKPOINT_INVALID",
        "binding_valid": False,
        "failure_stage": "center",
        "failure_reason": "frozen center gate failed",
        "config_hash": config_hash(execution),
        "source_hashes": {
            "frozen_execution": sha256_file(root / "configs/v5/two_parameter_frozen_execution.yaml"),
            "checkpoint_manifest": sha256_file(
                root / f"outputs/runs/v5/checkpoints/two_parameter_{role}/seed_{seed}/checkpoint_manifest.json"
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
        "F_raw": None,
        "F_se_GN_explicit": None,
        "F_se_GN_matrix_free": None,
        "H_red_exact_gamma": None,
        "primary": None,
        "generalized_geometry": None,
        "solver": None,
        "exact_hessian": None,
        "coupling": None,
    }
    if center_valid:
        lambda_max = float(torch.linalg.svdvals(jt)[0].square().item())
        gamma = float(development["gamma_alpha"]) * lambda_max
        raw = jl.T @ jl
        identity = torch.eye(theta.numel(), dtype=theta.dtype)
        explicit = raw - jl.T @ jt @ torch.linalg.solve(
            jt.T @ jt + gamma * identity, jt.T @ jl
        )
        rhs_vectors = [jl[:, 0], jl[:, 1], jl[:, 0] + jl[:, 1]]
        candidates = [
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
        solved = [row["scaled_LSQR_iterative_refinement"] for row in candidates]
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
        primary = None
        generalized = None
        if binding and gold is not None:
            primary = _primary_metrics(
                raw, explicit, gold, execution["primary_metric"]
            )
            metric = torch.tensor(primary["B"], dtype=theta.dtype)
            generalized = _generalized_geometry(explicit, gold, metric)
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
                else "frozen V5.3 numerical or coupling gate failed",
                "gamma": gamma,
                "lambda_max": lambda_max,
                "F_raw": raw.tolist(),
                "F_se_GN_explicit": explicit.tolist(),
                "F_se_GN_matrix_free": matrix_free.tolist(),
                "H_red_exact_gamma": gold.tolist() if gold is not None else None,
                "primary": primary,
                "generalized_geometry": generalized,
                "solver": {
                    "status": "PASS" if solver_pass else "SOLVER_FAILURE",
                    "verified_residuals": residuals,
                    "iterations": iterations,
                    "matrix_free_vs_explicit_relative_error": solver_error,
                    "polarization_rhs": ["column_0", "column_1", "column_0_plus_column_1"],
                    "setup_jvp_counts": [row["setup_jvp_count"] for row in candidates],
                },
                "exact_hessian": exact,
                "coupling": coupling,
                "coupling_status": "PASS" if coupling_pass else "NUMERICAL_FAILURE",
            }
        )
    record["elapsed_seconds"] = time.perf_counter() - started
    write_json_atomic(destination / "result.json", record)
    return record


def run_two_parameter_frozen_cohort(repo_root: str | Path, role: str) -> list[dict[str, Any]]:
    if role not in {"heldout", "confirmation"}:
        raise ValueError("V5.3 frozen role must be heldout or confirmation")
    root = Path(repo_root).resolve()
    execution, development, inherited = _verify(root, role)
    seeds = HELDOUT_SEEDS if role == "heldout" else CONFIRMATION_SEEDS
    provenance = environment_provenance(root, "float64", "cpu")
    if provenance["git_dirty"]:
        raise RuntimeError("V5.3 frozen cohort requires a clean committed executable")
    for seed in seeds:
        if (root / execution["output_root"] / role / f"seed_{seed}").exists() or (
            root / f"outputs/runs/v5/checkpoints/two_parameter_{role}/seed_{seed}"
        ).exists():
            raise RuntimeError("V5.3 frozen cohort has prior output; rerun forbidden")
    return [
        _run_seed(root, role, seed, provenance, execution, development, inherited)
        for seed in seeds
    ]
