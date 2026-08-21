"""Fresh-seed two-parameter exact reduced-geometry pipeline."""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.multi import multi_residual, train_multi_checkpoint
from saeps.p4_screening import _stationarity
from saeps.provenance import environment_provenance
from saeps.v3.foundation import full_hessian_references
from saeps.v31.local_minimum import exact_state_diagnostics
from saeps.v35.engineering import scaled_augmented_lsqr_candidates
from saeps.v43.center import allen_center_candidates


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _relative(first: torch.Tensor, second: torch.Tensor) -> float:
    return float(torch.linalg.matrix_norm(first - second).item()) / max(float(torch.linalg.matrix_norm(second).item()), 1.0e-30)


def _generalized(curvature: torch.Tensor, raw: torch.Tensor, tau_relative: float) -> dict[str, Any]:
    tau = tau_relative * max(float(torch.trace(raw).item()) / raw.shape[0], 1.0)
    metric = 0.5 * (raw + raw.T) + tau * torch.eye(raw.shape[0], dtype=raw.dtype)
    cholesky = torch.linalg.cholesky(metric)
    left = torch.linalg.solve_triangular(cholesky, curvature, upper=False)
    transformed = torch.linalg.solve_triangular(cholesky, left.T, upper=False).T
    eigenvalues, q = torch.linalg.eigh(0.5 * (transformed + transformed.T))
    vectors = torch.linalg.solve_triangular(cholesky.T, q, upper=True)
    norms = torch.sqrt(torch.sum(vectors * (metric @ vectors), dim=0))
    vectors = vectors / norms
    return {"tau": tau, "eigenvalues": eigenvalues.tolist(), "eigenvectors_columns": vectors.tolist(), "metric_normalization": (vectors.T @ metric @ vectors).tolist()}


def run_v46_engineering_seed(root: Path, seed: int) -> dict[str, Any]:
    specification = load_config(root / "configs/v4_6/two_parameter_development.yaml")
    if seed not in specification["engineering_seeds"]:
        raise ValueError("only registered v4.6 engineering seeds are authorized")
    revision = str(specification["output_revision"])
    destination = root / f"outputs/runs/v4_6_two_parameter/{revision}/seed_{seed}"
    if destination.exists():
        raise RuntimeError("seed output exists; rerun forbidden")
    for relative, expected in specification["protected_sources"].items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"protected source mismatch: {relative}")
    runtime = load_config(root / specification["source_config"])
    runtime["network"]["hidden_width"] = int(
        specification["architecture_engineering"]["selected_width"]
    )
    runtime["network"]["architecture"] = (
        f"two_channel_tanh_mlp_2x{runtime['network']['hidden_width']}x1"
    )
    local = load_config(root / "configs/v3_4/curvature_validation.yaml")["local_minimum"]
    provenance = environment_provenance(root, runtime["dtype"], runtime["device"])
    started = time.perf_counter()
    checkpoint, points = train_multi_checkpoint(runtime, seed)

    def residual_at(state: torch.Tensor) -> torch.Tensor:
        return multi_residual(state, checkpoint.coordinate, points, runtime)

    def objective(state: torch.Tensor) -> torch.Tensor:
        return 0.5 * torch.mean(residual_at(state).square())

    baseline, _, _, _ = exact_state_diagnostics(objective, checkpoint.theta, local)
    theta = checkpoint.theta
    enhanced = None
    method = "inherited_baseline"
    if baseline["local_minimum_gate"] != "PASS":
        candidate, enhanced = allen_center_candidates(residual_at, objective, theta, seed, local, specification["center_engineering"])
        if candidate is not None:
            theta = candidate
            method = "deterministic_enhanced"
    final_center, _, _, _ = exact_state_diagnostics(objective, theta, local)
    residual_function = lambda state, coordinate: multi_residual(state, coordinate, points, runtime)
    linearization = ResidualLinearization(residual_function, theta, checkpoint.coordinate)
    residual = linearization.residual()
    jt, jl = linearization.explicit_jacobians()
    theta_stationarity = _stationarity(jt, residual)
    center_valid = (
        final_center["local_minimum_gate"] == "PASS"
        and theta_stationarity <= 1.0e-4
        and checkpoint.state_rmse
        <= float(specification["architecture_engineering"]["state_rmse_max_validation_only"])
    )
    record: dict[str, Any] = {
        "schema_version": 1, "phase": specification["phase"], "role": "engineering", "seed": seed,
        "status": "CHECKPOINT_INVALID", "binding_valid": False, "failure_reason": "center gate failed",
        "config_hash": config_hash(specification), "git_commit": provenance["git_commit"], "provenance": provenance,
        "training": checkpoint.__dict__ | {"theta": None, "coordinate": checkpoint.coordinate.tolist()},
        "center": {"method": method, "baseline": baseline, "enhanced": enhanced, "final": final_center, "theta_stationarity": theta_stationarity},
        "F_raw": None, "F_se_GN_explicit": None, "F_se_GN_matrix_free": None, "H_red_exact_gamma": None,
        "solver": None, "exact_hessian": None, "generalized_eigen": None, "coupling": None,
        "E_raw": None, "E_SAEPS": None, "D": None,
        "selection_forbidden_metrics_not_used": specification["selection_forbidden_metrics"],
        "architecture": runtime["network"],
    }
    if center_valid:
        lambda_max = float(torch.linalg.eigvalsh(jt.T @ jt).max().item())
        gamma = float(specification["gamma_alpha"]) * lambda_max
        raw = jl.T @ jl
        identity = torch.eye(theta.numel(), dtype=theta.dtype)
        explicit = raw - jl.T @ jt @ torch.linalg.solve(jt.T @ jt + gamma * identity, jt.T @ jl)
        rhs_vectors = [jl[:, 0], jl[:, 1], jl[:, 0] + jl[:, 1]]
        solved_rows = [scaled_augmented_lsqr_candidates(linearization, rhs, gamma, float(specification["curvature_solver"]["tolerance"]), int(specification["curvature_solver"]["max_iterations_per_pass"]), int(specification["curvature_solver"]["refinement_passes"])) for rhs in rhs_vectors]
        values = [float(row["scaled_LSQR_iterative_refinement"]["Fse"]) for row in solved_rows]
        mf = torch.tensor([[values[0], 0.5 * (values[2] - values[0] - values[1])], [0.5 * (values[2] - values[0] - values[1]), values[1]]], dtype=theta.dtype)
        residuals = [float(row["scaled_LSQR_iterative_refinement"]["verified_original_relative_normal_residual"]) for row in solved_rows]
        iterations = [int(row["scaled_LSQR_iterative_refinement"]["total_iterations"]) for row in solved_rows]
        solver_error = _relative(mf, explicit)
        solver_pass = max(residuals) <= float(specification["curvature_solver"]["verified_normal_residual_acceptance"]) and solver_error <= float(specification["curvature_solver"]["explicit_reference_relative_acceptance"]) and max(iterations) <= int(specification["curvature_solver"]["maximum_total_iterations"])
        exact = full_hessian_references(residual_function, theta, checkpoint.coordinate, gamma, specification["exact_hessian"])
        gamma_exact = exact["gamma_matched"]
        exact_pass = gamma_exact["status"] == "PASS"
        gold = torch.tensor(gamma_exact["reduced_hessian"], dtype=theta.dtype) if exact_pass else None
        if solver_pass and gold is not None:
            e_raw = _relative(raw, gold)
            e_saeps = _relative(explicit, gold)
            coupling = abs(float(gold[0, 1].item())) / math.sqrt(max(abs(float(gold[0, 0].item() * gold[1, 1].item())), 1.0e-30))
            record.update(status="PASS", binding_valid=True, failure_reason=None, F_raw=raw.tolist(), F_se_GN_explicit=explicit.tolist(), F_se_GN_matrix_free=mf.tolist(), H_red_exact_gamma=gold.tolist(), gamma=gamma, solver={"status": "PASS", "verified_residuals": residuals, "iterations": iterations, "matrix_free_vs_explicit_relative_error": solver_error, "polarization_rhs": ["column_0", "column_1", "column_0_plus_column_1"]}, exact_hessian=exact, generalized_eigen={"SAEPS_vs_raw": _generalized(explicit, raw, float(specification["generalized_eigen_tau_relative"])), "exact_vs_raw": _generalized(gold, raw, float(specification["generalized_eigen_tau_relative"]))}, coupling=coupling, E_raw=e_raw, E_SAEPS=e_saeps, D=e_raw-e_saeps)
        else:
            record.update(status="SOLVER_FAILURE" if not solver_pass else "NUMERICAL_FAILURE", failure_reason="two-column solver or exact gamma reduction failed", gamma=gamma, solver={"status": "PASS" if solver_pass else "SOLVER_FAILURE", "verified_residuals": residuals, "iterations": iterations, "matrix_free_vs_explicit_relative_error": solver_error}, exact_hessian=exact)
    record["elapsed_seconds"] = time.perf_counter() - started
    result_path = destination / "result.json"
    _write(result_path, record)
    _write(destination / "manifest.json", {"schema_version": 1, "seed": seed, "status": record["status"], "binding_valid": record["binding_valid"], "result_path": "result.json", "result_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest()})
    return record
