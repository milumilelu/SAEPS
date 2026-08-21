"""One-shot, paired V4.8 robustness execution on real PINN residuals."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

import torch

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.p4_screening import _stationarity
from saeps.p5_confirmation import _runtime_config
from saeps.provenance import environment_provenance
from saeps.scalar import scalar_residual, solve_truth, train_scalar_checkpoint
from saeps.v3.foundation import full_hessian_references
from saeps.v31.pipeline import _mean_residual_objective
from saeps.v35.engineering import center_with_registered_rescue, scaled_augmented_lsqr_candidates
from saeps.v35.second_order import second_order_reduced_decomposition
from saeps.v36.pipeline import _center_specs, _relative
from saeps.v41.numerics import explicit_curvature_reference
from saeps.v41.pipeline import _protected_v36


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _evaluate(
    *, seed: int, label: str, runtime: dict[str, Any], truth: Any,
    v36: dict[str, Any], exact_required: bool, provenance: dict[str, Any],
    config_digest: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    record: dict[str, Any] = {
        "schema_version": 1, "phase": "V4_8_PAIRED_ROBUSTNESS",
        "seed": seed, "condition": label, "config_hash": config_digest,
        "git_commit": provenance["git_commit"], "status": "NUMERICAL_FAILURE",
        "binding_valid": False, "failure_reason": None,
        "exact_required": exact_required,
        "noise": float(runtime.get("observation_noise", 0.0)),
        "observation_fraction": float(runtime.get("observation_fraction", 1.0)),
        "architecture_width": int(runtime["network"]["hidden_width"]),
        "statuses": {"center_status": "NOT_COMPUTED", "parameter_reference_status": "NOT_COMPUTED",
                     "curvature_solver_status": "NOT_COMPUTED", "exact_reference_status": "NOT_REQUIRED",
                     "finite_curvature_status": "NOT_COMPUTED", "score_solver_status": "NOT_RUN_NONBINDING"},
        "F_raw": None, "F_se_explicit": None, "F_se_GN": None, "eta": None,
        "H_red_exact_gamma": None, "E_raw": None, "E_SAEPS": None, "D": None,
        "center": None, "center_stationarity": None, "curvature_solver": None,
        "exact_hessian": None, "training": None, "elapsed_seconds": None,
    }
    try:
        checkpoint, points = train_scalar_checkpoint(runtime, "Burgers", seed, truth)
        residual_function = lambda theta, parameter: scalar_residual(
            theta, parameter, "Burgers", points, truth, runtime
        )
        parameter = checkpoint.log_parameter.detach().clone()
        objective = _mean_residual_objective(residual_function, parameter, checkpoint.theta, 0.0, False)
        local, enhanced = _center_specs(v36)
        theta, center = center_with_registered_rescue(objective, checkpoint.theta, local, enhanced)
        record["training"] = {"seconds": checkpoint.elapsed_seconds, "stop_reason": checkpoint.stop_reason,
                              "state_rmse_validation_only": checkpoint.state_rmse}
        record["center"] = center
        if theta is None:
            record["statuses"]["center_status"] = "CHECKPOINT_INVALID"
            record.update(status="CHECKPOINT_INVALID", failure_reason="frozen center policy failed")
            return record

        linearization = ResidualLinearization(residual_function, theta, parameter)
        residual = linearization.residual()
        jt, jl = linearization.explicit_jacobians()
        selected = center["baseline"] if center["selected_method"] == "baseline_v3_4_exact_trust" else center["enhanced"]
        g_theta = float(selected["final"]["normalized_objective_gradient"])
        s_theta, s_lambda = _stationarity(jt, residual), _stationarity(jl, residual)
        center_pass = g_theta < float(v36["center"]["required_objective_gradient_tolerance"]) and s_theta < float(v36["center"]["residual_stationarity_tolerance"])
        record["center_stationarity"] = {"G_theta": g_theta, "S_theta": s_theta, "S_lambda": s_lambda}
        record["statuses"]["center_status"] = "PASS" if center_pass else "CHECKPOINT_INVALID"
        if not center_pass:
            record.update(status="CHECKPOINT_INVALID", failure_reason="frozen center stationarity gate failed")
            return record

        gamma = float(v36["gamma"]["alpha"]) * float(torch.linalg.eigvalsh(jt.T @ jt).max().item())
        record["gamma"] = gamma
        record["F_raw"] = float(torch.dot(jl[:, 0], jl[:, 0]).item())
        reference = explicit_curvature_reference(jt, jl, gamma)
        record["statuses"]["parameter_reference_status"] = reference["parameter_reference_status"]
        record["F_se_explicit"] = float(reference["Fse_explicit"])

        solver_spec = v36["curvature_solver"]
        candidates = scaled_augmented_lsqr_candidates(
            linearization, jl[:, 0], gamma, float(solver_spec["tolerance"]),
            int(solver_spec["max_iterations_per_pass"]), int(solver_spec["refinement_passes"]),
        )
        solved = candidates["scaled_LSQR_iterative_refinement"]
        fse = float(solved["Fse"])
        comparison = _relative(fse, float(record["F_se_explicit"]))
        solver_pass = (
            float(solved["verified_original_relative_normal_residual"]) <= float(solver_spec["verified_normal_residual_acceptance"])
            and comparison <= float(solver_spec["explicit_reference_relative_acceptance"])
            and int(solved["total_iterations"]) <= int(solver_spec["maximum_total_iterations"])
        )
        record["statuses"]["curvature_solver_status"] = "PASS" if solver_pass else "SOLVER_FAILURE"
        record["F_se_GN"] = fse
        record["eta"] = fse / record["F_raw"] if record["F_raw"] != 0.0 else None
        record["curvature_solver"] = {
            "verified_original_relative_normal_residual": solved["verified_original_relative_normal_residual"],
            "selected_vs_explicit_relative_error": comparison, "iterations": solved["total_iterations"],
            "setup_jvp_count": candidates["setup_jvp_count"], "passes": solved["passes"],
        }

        if exact_required:
            full = full_hessian_references(residual_function, theta, parameter, gamma, v36["gold_standard"])
            decomposition = second_order_reduced_decomposition(
                residual_function, theta, parameter, gamma, float(v36["errors"]["denominator_floor"])
            )
            gold = full["gamma_matched"]
            h_exact = float(gold["reduced_hessian"][0][0]) if gold["reduced_hessian"] is not None else None
            cross = _relative(float(decomposition["Hred_exact_gamma"]), h_exact) if h_exact is not None else None
            exact_pass = (
                full["symmetry_relative_error"] <= float(v36["gold_standard"]["symmetry_relative_tolerance"])
                and gold["status"] == "PASS" and cross is not None
                and cross <= float(v36["gold_standard"]["solve_relative_tolerance"])
            )
            record["statuses"]["exact_reference_status"] = "PASS" if exact_pass else "NUMERICAL_FAILURE"
            record["H_red_exact_gamma"] = h_exact
            record["exact_hessian"] = {"symmetry_relative_error": full["symmetry_relative_error"],
                                       "gamma_matched": gold, "decomposition_crosscheck_relative_error": cross}
            if h_exact is not None:
                denominator = abs(h_exact) + float(v36["errors"]["denominator_floor"])
                record["E_raw"] = abs(record["F_raw"] - h_exact) / denominator
                record["E_SAEPS"] = abs(fse - h_exact) / denominator
                record["D"] = record["E_raw"] - record["E_SAEPS"]

        finite = all(value is not None and math.isfinite(float(value)) for value in (record["F_raw"], record["F_se_explicit"], record["F_se_GN"], record["eta"]))
        record["statuses"]["finite_curvature_status"] = "PASS" if finite else "NUMERICAL_FAILURE"
        binding = center_pass and reference["parameter_reference_status"] == "PASS" and solver_pass and finite
        if exact_required:
            binding = binding and record["statuses"]["exact_reference_status"] == "PASS"
        record["binding_valid"] = binding
        record["status"] = "PASS" if binding else ("SOLVER_FAILURE" if not solver_pass else "NUMERICAL_FAILURE")
        record["failure_reason"] = None if binding else "one or more binding curvature nodes failed"
        return record
    except Exception as error:
        record["status"] = "NUMERICAL_FAILURE"
        record["failure_reason"] = f"{type(error).__name__}: {error}"
        return record
    finally:
        record["elapsed_seconds"] = time.perf_counter() - started


def run_robustness_seed(root: Path, family: str, seed: int) -> dict[str, Any]:
    root = root.resolve()
    config_path = root / "configs/v4_8/robustness.yaml"
    specification = load_config(config_path)
    if not specification["protocol_locked"] or not specification["execution_authorized"]:
        raise RuntimeError("V4.8 execution is not authorized")
    families = {"noise_sparsity": specification["noise_sparsity"]["seeds"],
                "architecture": specification["architecture"]["seeds"]}
    if family not in families or seed not in families[family]:
        raise ValueError("family/seed is outside the locked V4.8 namespace")
    destination = root / "outputs/runs/v4_8_robustness" / family / f"seed_{seed}"
    if destination.exists():
        raise RuntimeError("one-shot family/seed output already exists")

    v41 = load_config(root / specification["source_v4_1_config"])
    v36 = _protected_v36(root, v41)
    scalar = load_config(root / v36["source_files"]["scalar_config"]["path"])
    base = _runtime_config(scalar)
    provenance = environment_provenance(root, scalar["dtype"], scalar["device"])
    if provenance["git_dirty"]:
        raise RuntimeError("formal V4.8 execution requires clean provenance")
    truth = solve_truth(base, "Burgers")
    digest = config_hash(specification)
    destination.mkdir(parents=True)
    records_dir = destination / "records"
    records_dir.mkdir()
    records: list[dict[str, Any]] = []
    if family == "noise_sparsity":
        anchors = {tuple(map(float, item)) for item in specification["noise_sparsity"]["exact_anchor_cells"]}
        conditions = [(float(n), float(f), None) for n in specification["noise_sparsity"]["noise_levels"] for f in specification["noise_sparsity"]["observation_fractions"]]
    else:
        conditions = [(0.0, 1.0, (int(width), str(label))) for width, label in zip(specification["architecture"]["widths"], specification["architecture"]["labels"], strict=True)]
        anchors = set()
    manifest = []
    for index, (noise, fraction, architecture) in enumerate(conditions):
        runtime = copy.deepcopy(base)
        runtime["observation_noise"] = noise
        runtime["observation_fraction"] = fraction
        if architecture is None:
            label = f"noise={noise:g}_fraction={fraction:g}"
        else:
            width, name = architecture
            runtime["network"] = {"architecture": f"tanh_mlp_2x{width}x1", "hidden_width": width}
            label = f"architecture={name}"
        record = _evaluate(seed=seed, label=label, runtime=runtime, truth=truth, v36=v36,
                           exact_required=(noise, fraction) in anchors and architecture is None,
                           provenance=provenance, config_digest=digest)
        path = records_dir / f"condition_{index:02d}.json"
        _write(path, record)
        manifest.append({"condition": label, "status": record["status"], "binding_valid": record["binding_valid"],
                         "path": str(path.relative_to(destination)).replace("\\", "/"), "sha256": _sha256(path)})
        records.append(record)
    summary = {"schema_version": 1, "phase": specification["phase"], "family": family, "seed": seed,
               "config_hash": digest, "provenance": provenance, "planned": len(conditions), "completed": len(records),
               "binding_valid_count": sum(row["binding_valid"] for row in records),
               "status_counts": {status: sum(row["status"] == status for row in records)
                                 for status in ("PASS", "CHECKPOINT_INVALID", "SOLVER_FAILURE", "NUMERICAL_FAILURE")},
               "scientific_gate": "DESCRIPTIVE_ONLY"}
    _write(destination / "summary.json", summary)
    _write(destination / "manifest.json", {"schema_version": 1, "records": manifest})
    return summary
