"""V5.1 finite-gamma and damping-dependent effective-rank audit."""

from __future__ import annotations

import copy
import json
import math
import time
from pathlib import Path
from typing import Any, Callable

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.io_utils import write_json_atomic
from saeps.provenance import environment_provenance
from saeps.scalar import ScalarPoints, scalar_residual, solve_truth
from saeps.v3.foundation import _reduce_hessian
from saeps.v35.engineering import scaled_augmented_lsqr_candidates
from saeps.v41.pipeline import _protected_v36
from saeps.v41.numerics import explicit_curvature_reference
from saeps.v43.pipeline import _protected_config
from saeps.v5.governance import sha256_file, validate_checkpoint_manifest


ALPHAS = [1.0e-10, 1.0e-8, 1.0e-6, 1.0e-4, 1.0e-2, 1.0, 1.0e2]
CHECKPOINTS = {"burgers": [45, 46, 47], "allen_cahn": [70, 71, 72]}
ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def _source_provenance(root: Path) -> dict[str, Any]:
    provenance = environment_provenance(root, "float64", "cpu")
    if provenance["git_dirty"]:
        raise RuntimeError("V5.1 requires a clean committed executable")
    return provenance


def _verify_freeze(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    authorization = json.loads(
        (root / "configs/v5/V5_EXECUTION_AUTHORIZATION.json").read_text(encoding="utf-8")
    )
    if authorization.get("authorized") is not True:
        raise RuntimeError("V5 scientific execution is not authorized")
    freeze = json.loads(
        (root / "configs/v5/FINITE_GAMMA_EXECUTABLE_FREEZE.json").read_text(encoding="utf-8")
    )
    if freeze.get("execution_authorized") is not True:
        raise RuntimeError("V5.1 executable freeze does not authorize execution")
    for relative, expected in freeze["file_sha256"].items():
        if sha256_file(root / relative) != expected:
            raise RuntimeError(f"V5.1 frozen file mismatch: {relative}")
    config = load_config(root / "configs/v5/finite_gamma_audit.yaml")
    if [float(value) for value in config["alpha_values"]] != ALPHAS:
        raise RuntimeError("V5.1 alpha registry changed")
    return config, authorization


def _runtime(root: Path, family: str) -> tuple[dict[str, Any], dict[str, str], str]:
    if family == "burgers":
        development = load_config(root / "configs/v4_1/post_confirmation_development.yaml")
        curvature = _protected_v36(root, development)
        scalar_path = curvature["source_files"]["scalar_config"]["path"]
        from saeps.p5_confirmation import _runtime_config

        runtime = _runtime_config(load_config(root / scalar_path))
        source_paths = ["configs/v4_1/post_confirmation_development.yaml", scalar_path]
        benchmark = "Burgers"
    else:
        development = load_config(root / "configs/v4_3/allen_cahn_development.yaml")
        runtime = copy.deepcopy(
            _protected_config(root, development["protected_sources"]["scalar_runtime"])
        )
        runtime["network"]["hidden_width"] = int(
            development["architecture_engineering"]["selected_width"]
        )
        source_paths = [
            "configs/v4_3/allen_cahn_development.yaml",
            development["protected_sources"]["scalar_runtime"]["path"],
        ]
        benchmark = "Allen-Cahn"
    return runtime, {path: sha256_file(root / path) for path in source_paths}, benchmark


def _load_checkpoint(
    root: Path, family: str, seed: int
) -> tuple[torch.Tensor, torch.Tensor, ScalarPoints, dict[str, Any], dict[str, Any]]:
    directory = root / "outputs/runs/v5/checkpoints" / family / f"seed_{seed}"
    manifest = validate_checkpoint_manifest(root, directory / "checkpoint_manifest.json")
    if manifest["status"] != "PASS":
        raise RuntimeError(f"V5.1 fixed checkpoint is not binding-valid: {family}/{seed}")
    payload = torch.load(root / manifest["model_state_path"], map_location="cpu", weights_only=True)
    points = ScalarPoints(**payload["points"])
    return payload["theta"], payload["coordinate"], points, manifest, payload


def _full_hessian_blocks(
    residual_function: ResidualFunction, theta: torch.Tensor, parameter: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
    n_theta = theta.numel()
    joint = torch.cat([theta, parameter]).detach()

    def loss(value: torch.Tensor) -> torch.Tensor:
        residual = residual_function(value[:n_theta], value[n_theta:])
        return 0.5 * torch.sum(residual.square())

    hessian = torch.func.hessian(loss)(joint)
    symmetry = float(torch.linalg.matrix_norm(hessian - hessian.T).item()) / max(
        float(torch.linalg.matrix_norm(hessian).item()), 1.0e-30
    )
    return (
        hessian[:n_theta, :n_theta],
        hessian[:n_theta, n_theta:],
        hessian[n_theta:, n_theta:],
        symmetry,
    )


def _alpha_slug(alpha: float) -> str:
    return f"{alpha:.0e}".replace("+", "p").replace("-", "m")


def _evaluate_checkpoint(
    root: Path,
    config: dict[str, Any],
    provenance: dict[str, Any],
    family: str,
    seed: int,
) -> list[dict[str, Any]]:
    theta, parameter, points, manifest, _ = _load_checkpoint(root, family, seed)
    runtime, runtime_hashes, benchmark = _runtime(root, family)
    truth = solve_truth(runtime, benchmark)
    residual_function: ResidualFunction = lambda state, coordinate: scalar_residual(
        state, coordinate, benchmark, points, truth, runtime
    )
    linearization = ResidualLinearization(residual_function, theta, parameter)
    residual = linearization.residual()
    jacobian_theta, jacobian_parameter = linearization.explicit_jacobians()
    singular_values = torch.linalg.svdvals(jacobian_theta)
    lambda_max = float(singular_values[0].square().item())
    raw = float(torch.dot(jacobian_parameter[:, 0], jacobian_parameter[:, 0]).item())
    h_tt, h_tl, h_ll, hessian_symmetry = _full_hessian_blocks(
        residual_function, theta, parameter
    )
    numerical = load_config(root / "configs/v3_6/locked_scalar_confirmation.yaml")
    solver_spec = numerical["curvature_solver"]
    gold_spec = numerical["gold_standard"]
    denominator_floor = float(numerical["errors"]["denominator_floor"])
    records: list[dict[str, Any]] = []
    for alpha in ALPHAS:
        started = time.perf_counter()
        gamma = alpha * lambda_max
        destination = (
            root
            / "outputs/runs/v5/finite_gamma"
            / family
            / f"seed_{seed}"
            / f"alpha_{_alpha_slug(alpha)}"
        )
        if destination.exists():
            raise RuntimeError(f"V5.1 terminal record already exists: {family}/{seed}/{alpha}")
        destination.mkdir(parents=True, exist_ok=False)
        record: dict[str, Any] = {
            "schema_version": 1,
            "phase": "V5_1_FINITE_GAMMA",
            "role": "descriptive_finite_gamma_audit",
            "family": family,
            "benchmark": benchmark,
            "seed": seed,
            "alpha": alpha,
            "gamma": gamma,
            "gamma_definition": "alpha_times_lambda_max_JthetaT_Jtheta",
            "config_hash": config_hash(config),
            "source_hashes": {
                "checkpoint_manifest": sha256_file(
                    root / "outputs/runs/v5/checkpoints" / family / f"seed_{seed}" / "checkpoint_manifest.json"
                ),
                "model_state": manifest["model_state_hash"],
                **runtime_hashes,
            },
            "provenance": provenance,
            "failure_stage": None,
            "failure_reason": None,
            "binding_valid": False,
            "status": "NUMERICAL_FAILURE",
            "m": int(residual.numel()),
            "n_theta": int(theta.numel()),
            "lambda_max": lambda_max,
            "singular_values_J_theta": singular_values.tolist(),
            "effective_rank": float(
                torch.sum(singular_values.square() / (singular_values.square() + gamma)).item()
            ),
            "effective_rank_definition": "sum_sigma2_over_sigma2_plus_gamma",
            "F_raw": raw,
        }
        try:
            explicit = explicit_curvature_reference(jacobian_theta, jacobian_parameter, gamma)
            candidates = scaled_augmented_lsqr_candidates(
                linearization,
                jacobian_parameter[:, 0],
                gamma,
                float(solver_spec["tolerance"]),
                int(solver_spec["max_iterations_per_pass"]),
                int(solver_spec["refinement_passes"]),
            )
            solved = candidates["scaled_LSQR_iterative_refinement"]
            fse_explicit = float(explicit["Fse_explicit"])
            fse_mf = float(solved["Fse"])
            mf_error = abs(fse_mf - fse_explicit) / max(abs(fse_explicit), 1.0e-30)
            identity = torch.eye(theta.numel(), dtype=theta.dtype)
            exact = _reduce_hessian(
                h_tt + gamma * identity,
                h_tl,
                h_tl.T,
                h_ll,
                gold_spec,
            )
            exact_value = (
                float(exact["reduced_hessian"][0][0])
                if exact["reduced_hessian"] is not None
                else None
            )
            solver_pass = (
                explicit["parameter_reference_status"] == "PASS"
                and solved["verified_original_relative_normal_residual"]
                <= float(solver_spec["verified_normal_residual_acceptance"])
                and mf_error <= float(solver_spec["explicit_reference_relative_acceptance"])
                and solved["total_iterations"] <= int(solver_spec["maximum_total_iterations"])
            )
            exact_pass = (
                exact["status"] == "PASS"
                and hessian_symmetry <= float(gold_spec["symmetry_relative_tolerance"])
            )
            finite = all(
                math.isfinite(value)
                for value in [raw, fse_explicit, fse_mf, gamma, record["effective_rank"]]
            ) and (exact_value is None or math.isfinite(exact_value))
            record.update(
                {
                    "F_se_GN_explicit": fse_explicit,
                    "F_se_GN_matrix_free": fse_mf,
                    "eta": fse_explicit / max(raw, 1.0e-30),
                    "H_red_exact_gamma": exact_value,
                    "E_SAEPS": None
                    if exact_value is None
                    else abs(fse_explicit - exact_value) / max(abs(exact_value), denominator_floor),
                    "E_raw": None
                    if exact_value is None
                    else abs(raw - exact_value) / max(abs(exact_value), denominator_floor),
                    "parameter_reference": explicit,
                    "matrix_free_solver": {
                        "status": "PASS" if solver_pass else "SOLVER_FAILURE",
                        "verified_original_relative_normal_residual": solved[
                            "verified_original_relative_normal_residual"
                        ],
                        "explicit_relative_error": mf_error,
                        "iterations": solved["total_iterations"],
                        "setup_jvp_count": candidates["setup_jvp_count"],
                        "passes": solved["passes"],
                    },
                    "exact_reference": {
                        **exact,
                        "full_hessian_symmetry_relative_error": hessian_symmetry,
                    },
                }
            )
            if not finite:
                record["failure_reason"] = "one or more finite-gamma quantities are non-finite"
            elif not solver_pass:
                record["failure_stage"] = "curvature_solver"
                record["failure_reason"] = "frozen V5.1 solver gate failed"
                record["status"] = "SOLVER_FAILURE"
            elif not exact_pass:
                record["failure_stage"] = "exact_reference"
                record["failure_reason"] = "exact finite-gamma reduction gate failed"
            else:
                record["status"] = "PASS"
                record["binding_valid"] = True
        except Exception as error:
            record["failure_stage"] = "finite_gamma_evaluation"
            record["failure_reason"] = f"{type(error).__name__}: {error}"
        record["elapsed_seconds"] = time.perf_counter() - started
        write_json_atomic(destination / "result.json", record)
        records.append(record)
    return records


def run_finite_gamma_audit(repo_root: str | Path) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    config, _ = _verify_freeze(root)
    provenance = _source_provenance(root)
    planned = [(family, seed) for family, seeds in CHECKPOINTS.items() for seed in seeds]
    for family, seed in planned:
        if (root / "outputs/runs/v5/finite_gamma" / family / f"seed_{seed}").exists():
            raise RuntimeError(f"V5.1 checkpoint already has output; rerun forbidden: {family}/{seed}")
    return [
        record
        for family, seed in planned
        for record in _evaluate_checkpoint(root, config, provenance, family, seed)
    ]
