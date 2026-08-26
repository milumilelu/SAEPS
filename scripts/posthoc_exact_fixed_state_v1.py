#!/usr/bin/env python3
"""One-shot post-hoc exact fixed-state curvature decomposition.

This runner reconstructs the historical scalar centers with frozen repository
code and writes only to outputs/posthoc/exact_fixed_state_v1. It never changes
historical confirmation evidence or its scientific adjudication.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.metadata
import json
import math
import platform
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
import yaml

from saeps.autodiff import ResidualLinearization
from saeps.config import config_hash, load_config
from saeps.p4_screening import _stationarity
from saeps.p5_confirmation import _runtime_config
from saeps.scalar import scalar_residual, solve_truth, train_scalar_checkpoint
from saeps.v31.pipeline import _mean_residual_objective
from saeps.v3.foundation import full_hessian_references
from saeps.v35.engineering import center_with_registered_rescue, scaled_augmented_lsqr_candidates
from saeps.v36.pipeline import _center_specs
from saeps.v41.numerics import explicit_curvature_reference
from saeps.v43.center import allen_center_candidates


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/posthoc_exact_fixed_state_v1.yaml"
OUTPUT_ROOT = ROOT / "outputs/posthoc/exact_fixed_state_v1"
CLAIM_PATH = OUTPUT_ROOT / "execution_claim.json"
PREFLIGHT_PATH = OUTPUT_ROOT / "preflight.json"
RUNNER_PATH = Path(__file__).resolve()
TEST_PATH = ROOT / "tests/test_posthoc_exact_fixed_state_v1.py"
CLASSIFICATION = "POSTHOC_NONBINDING_MECHANISM_ANALYSIS"
ResidualFunction = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


def environment() -> dict[str, Any]:
    packages = {
        name: importlib.metadata.version(name) for name in ("torch", "numpy", "PyYAML")
    }
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "packages": packages,
        "device": "cpu",
        "dtype": "float64",
        "torch_cuda_available": torch.cuda.is_available(),
        "torch_num_threads": torch.get_num_threads(),
        "git_commit": git("rev-parse", "HEAD"),
        "git_branch": git("branch", "--show-current"),
        "git_status_porcelain": git("status", "--porcelain"),
    }


def _expected_environment(config: dict[str, Any]) -> dict[str, Any]:
    observed = environment()
    expected = config["expected_environment"]
    checks = {
        "python": observed["python_version"] == str(expected["python"]),
        "torch": observed["packages"]["torch"].split("+")[0] == str(expected["torch"]),
        "numpy": observed["packages"]["numpy"] == str(expected["numpy"]),
        "PyYAML": observed["packages"]["PyYAML"] == str(expected["PyYAML"]),
        "cpu": not observed["torch_cuda_available"],
        "float64": torch.get_default_dtype() == torch.float64,
    }
    if not all(checks.values()):
        raise RuntimeError(f"historical environment mismatch: {checks}; observed={observed}")
    return {"observed": observed, "checks": checks}


def _manifest_state(config: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, cohort in config["cohorts"].items():
        manifest_path = ROOT / cohort["frozen_manifest"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        execution_claim_path = ROOT / cohort["frozen_execution_claim"]
        execution_claim = json.loads(execution_claim_path.read_text(encoding="utf-8"))
        frozen_config_path = ROOT / cohort["frozen_config"]
        lock_path = ROOT / cohort["frozen_lock"]
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        if sha256(frozen_config_path) != lock["locked_config_sha256"]:
            raise RuntimeError(f"{name} locked config hash mismatch")
        if execution_claim["locked_config_sha256"] != lock["locked_config_sha256"]:
            raise RuntimeError(f"{name} execution claim/config lineage mismatch")
        planned = [int(row["seed"]) for row in manifest["records"]]
        valid = [int(row["seed"]) for row in manifest["records"] if row["binding_valid"]]
        invalid = [int(row["seed"]) for row in manifest["records"] if not row["binding_valid"]]
        if planned != [int(seed) for seed in cohort["planned_seeds"]]:
            raise RuntimeError(f"{name} planned seed mismatch")
        if valid != [int(seed) for seed in cohort["expected_original_valid"]]:
            raise RuntimeError(f"{name} original binding-valid seed mismatch")
        for row in manifest["records"]:
            record_path = manifest_path.parent / row["path"]
            if sha256(record_path) != row["sha256"]:
                raise RuntimeError(f"frozen record hash mismatch: {record_path}")
        result[name] = {
            "planned": planned,
            "valid": valid,
            "invalid": invalid,
            "manifest_path": cohort["frozen_manifest"],
            "manifest_sha256": sha256(manifest_path),
            "raw_records_sha256": manifest["raw_records_sha256"],
            "execution_claim_path": cohort["frozen_execution_claim"],
            "execution_claim_sha256": sha256(execution_claim_path),
            "frozen_config_path": cohort["frozen_config"],
            "frozen_config_sha256": sha256(frozen_config_path),
            "frozen_lock_path": cohort["frozen_lock"],
            "frozen_lock_sha256": sha256(lock_path),
        }
    return result


def _historical_source_state(config: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, cohort in config["cohorts"].items():
        commit = str(cohort["historical_runner_commit"])
        rows = []
        for relative in config["historical_source_files"]:
            path = ROOT / relative
            exists_at_commit = subprocess.run(
                ["git", "-C", str(ROOT), "cat-file", "-e", f"{commit}:{relative}"],
                capture_output=True,
            ).returncode == 0
            if not exists_at_commit:
                continue
            historical = subprocess.run(
                ["git", "-C", str(ROOT), "show", f"{commit}:{relative}"],
                capture_output=True,
                check=True,
            ).stdout
            current = path.read_bytes()
            if historical != current:
                raise RuntimeError(f"{name} historical source mismatch: {relative}")
            rows.append({"path": relative, "sha256": hashlib.sha256(current).hexdigest()})
        result[name] = {"historical_runner_commit": commit, "files": rows}
    return result


def _relerr(left: float, right: float, floor: float) -> float:
    return abs(left - right) / max(abs(left), abs(right), floor)


def _close(left: float, right: float, rtol: float, atol: float) -> bool:
    return abs(left - right) <= atol + rtol * abs(right)


def curvature_blocks(
    residual_function: ResidualFunction,
    theta: torch.Tensor,
    parameter: torch.Tensor,
    gamma: float,
) -> dict[str, Any]:
    linearization = ResidualLinearization(residual_function, theta, parameter)
    residual = linearization.residual()
    jt, jl = linearization.explicit_jacobians()
    gtt = jt.T @ jt
    gtl = jt.T @ jl
    glt = gtl.T
    gll = jl.T @ jl
    theta_size = theta.numel()
    joint = torch.cat([theta, parameter]).detach()

    def sum_loss(current: torch.Tensor) -> torch.Tensor:
        current_residual = residual_function(current[:theta_size], current[theta_size:])
        return 0.5 * torch.sum(current_residual.square())

    hessian = torch.func.hessian(sum_loss)(joint)
    htt = hessian[:theta_size, :theta_size]
    htl = hessian[:theta_size, theta_size:]
    hlt = hessian[theta_size:, :theta_size]
    hll = hessian[theta_size:, theta_size:]
    htt_sym = 0.5 * (htt + htt.T)
    eye = torch.eye(theta_size, dtype=theta.dtype, device=theta.device)
    m = gtt + gamma * eye
    a = htt_sym + gamma * eye
    gn_solution = torch.linalg.solve(m, gtl)
    exact_solution = torch.linalg.solve(a, htl)
    c_gn = glt @ gn_solution
    fse = gll - c_gn
    c_exact = hlt @ exact_solution
    hred = hll - c_exact
    return {
        "residual": residual,
        "G_tt_tensor": gtt,
        "G_tl_tensor": gtl,
        "G_lt_tensor": glt,
        "G_ll_tensor": gll,
        "H_tt_tensor": htt,
        "H_tt_sym_tensor": htt_sym,
        "H_tl_tensor": htl,
        "H_lt_tensor": hlt,
        "H_ll_tensor": hll,
        "M_tensor": m,
        "A_tensor": a,
        "C_relax_GN_tensor": c_gn,
        "F_SAEPS_tensor": fse,
        "C_relax_exact_tensor": c_exact,
        "H_red_exact_tensor": hred,
        "gn_solution_tensor": gn_solution,
        "exact_solution_tensor": exact_solution,
    }


def _matrix_payload(value: torch.Tensor) -> list[Any]:
    return value.detach().cpu().tolist()


def _norms(value: torch.Tensor) -> dict[str, float]:
    return {
        "frobenius": float(torch.linalg.matrix_norm(value).item()),
        "spectral": float(torch.linalg.matrix_norm(value, ord=2).item()),
    }


def _scalar(value: torch.Tensor) -> float:
    if value.numel() != 1:
        raise ValueError("expected scalar block")
    return float(value.reshape(-1)[0].item())


def _numeric_analysis(
    blocks: dict[str, Any],
    gamma: float,
    original: dict[str, Any],
    selected_fse: float,
    config: dict[str, Any],
) -> dict[str, Any]:
    tol = config["tolerances"]
    rtol = float(tol["algebraic_relative"])
    floor = float(tol["algebraic_absolute_floor"])
    eps = float(tol["denominator_floor"])
    gtt, gtl, glt, gll = (blocks[key] for key in ("G_tt_tensor", "G_tl_tensor", "G_lt_tensor", "G_ll_tensor"))
    htt, htts, htl, hlt, hll = (blocks[key] for key in ("H_tt_tensor", "H_tt_sym_tensor", "H_tl_tensor", "H_lt_tensor", "H_ll_tensor"))
    cgn = _scalar(blocks["C_relax_GN_tensor"])
    fraw = _scalar(gll)
    fse_explicit = _scalar(blocks["F_SAEPS_tensor"])
    cexact = _scalar(blocks["C_relax_exact_tensor"])
    hfix = _scalar(hll)
    hred = _scalar(blocks["H_red_exact_tensor"])
    delta_gn_fix = fraw - hfix
    delta_relax = cgn - cexact
    identity_left = selected_fse - hred
    identity_right = delta_gn_fix - delta_relax
    m = blocks["M_tensor"]
    a = blocks["A_tensor"]
    gn_residual = m @ blocks["gn_solution_tensor"] - gtl
    exact_residual = a @ blocks["exact_solution_tensor"] - htl
    hessian_symmetry = float(torch.linalg.matrix_norm(torch.cat([torch.cat([htt, htl], dim=1), torch.cat([hlt, hll], dim=1)], dim=0) - torch.cat([torch.cat([htt, htl], dim=1), torch.cat([hlt, hll], dim=1)], dim=0).T).item()) / max(float(torch.linalg.matrix_norm(torch.cat([torch.cat([htt, htl], dim=1), torch.cat([hlt, hll], dim=1)], dim=0)).item()), floor)
    checks = {
        "F_raw_equals_G_ll": _close(fraw, _scalar(gll), rtol, floor),
        "F_SAEPS_explicit_identity": _close(fse_explicit, fraw - cgn, rtol, floor),
        "C_relax_GN_identity": _close(cgn, fraw - fse_explicit, rtol, floor),
        "H_red_exact_identity": _close(hred, hfix - cexact, rtol, floor),
        "C_relax_exact_identity": _close(cexact, hfix - hred, rtol, floor),
        "exact_error_identity": _close(identity_left, identity_right, rtol, floor),
        "hessian_symmetry": hessian_symmetry <= rtol,
        "GN_solve_residual": float(torch.linalg.vector_norm(gn_residual).item()) / max(float(torch.linalg.vector_norm(gtl).item()), floor) <= rtol,
        "exact_solve_residual": float(torch.linalg.vector_norm(exact_residual).item()) / max(float(torch.linalg.vector_norm(htl).item()), floor) <= rtol,
    }
    s_tt = htts - gtt
    t_tl = htl - gtl
    r_ll = hll - gll
    eig_m = torch.linalg.eigvalsh(0.5 * (m + m.T))
    eig_a = torch.linalg.eigvalsh(0.5 * (a + a.T))
    lambda_min_m = float(eig_m[0].item())
    norm_minv = 1.0 / lambda_min_m if lambda_min_m > 0.0 else None
    norm_stt = float(torch.linalg.matrix_norm(s_tt, ord=2).item())
    norm_ttl = float(torch.linalg.matrix_norm(t_tl, ord=2).item())
    norm_rll = float(torch.linalg.matrix_norm(r_ll, ord=2).item())
    norm_gtl = float(torch.linalg.matrix_norm(gtl, ord=2).item())
    delta = norm_minv * norm_stt if norm_minv is not None else None
    actual = abs(hred - fse_explicit)
    bound = None
    if delta is not None and delta < 1.0:
        bound = norm_rll + (norm_gtl**2 * norm_minv**2 * norm_stt) / (1.0 - delta) + ((2.0 * norm_gtl * norm_ttl + norm_ttl**2) * norm_minv) / (1.0 - delta)
    bound_check = None if bound is None else actual <= bound + floor + rtol * max(bound, 1.0)
    denom_red = abs(hred) + eps
    small_relax = abs(cexact) <= float(tol["relaxation_denominator_small"])
    metrics = {
        "E_raw": abs(fraw - hred) / denom_red,
        "E_SAEPS": abs(selected_fse - hred) / denom_red,
        "E_fix_exact_to_reduced": abs(hfix - hred) / denom_red,
        "E_GN_fix_native": abs(delta_gn_fix) / (abs(hfix) + eps),
        "E_GN_fix_reduced_scale": abs(delta_gn_fix) / denom_red,
        "E_relax": None if small_relax else abs(cgn - cexact) / (abs(cexact) + eps),
        "rho_relax": None if small_relax else cgn / cexact,
        "abs_rho_error": None if small_relax else abs(cgn / cexact - 1.0),
        "R_freezing_to_GN": abs(cexact) / (abs(delta_gn_fix) + eps),
        "R_total_improvement": abs(fraw - hred) / (abs(selected_fse - hred) + eps),
    }
    return {
        "rerun": {"F_raw": fraw, "F_SAEPS": selected_fse, "F_SAEPS_explicit": fse_explicit, "H_red_exact": hred},
        "exact_blocks": {"H_tt": _matrix_payload(htt), "H_tt_sym": _matrix_payload(htts), "H_tl": _matrix_payload(htl), "H_lt": _matrix_payload(hlt), "H_ll": _matrix_payload(hll)},
        "GN_blocks": {"G_tt": _matrix_payload(gtt), "G_tl": _matrix_payload(gtl), "G_lt": _matrix_payload(glt), "G_ll": _matrix_payload(gll)},
        "block_diagnostics": {
            "shapes": {key: list(value.shape) for key, value in {"H_tt": htt, "H_tl": htl, "H_lt": hlt, "H_ll": hll, "G_tt": gtt, "G_tl": gtl, "G_lt": glt, "G_ll": gll}.items()},
            "norms": {key: _norms(value) for key, value in {"H_tt": htt, "H_tl": htl, "H_lt": hlt, "H_ll": hll, "G_tt": gtt, "G_tl": gtl, "G_lt": glt, "G_ll": gll}.items()},
            "hessian_symmetry_relative_error": hessian_symmetry,
            "H_tt_raw_symmetry_relative_error": float(torch.linalg.matrix_norm(htt - htt.T).item()) / max(float(torch.linalg.matrix_norm(htt).item()), floor),
            "H_ll_raw_symmetry_relative_error": float(torch.linalg.matrix_norm(hll - hll.T).item()) / max(float(torch.linalg.matrix_norm(hll).item()), floor),
            "H_tt_plus_gamma_min_eigenvalue": float(eig_a[0].item()),
            "H_tt_plus_gamma_max_eigenvalue": float(eig_a[-1].item()),
            "G_tt_plus_gamma_min_eigenvalue": lambda_min_m,
            "G_tt_plus_gamma_max_eigenvalue": float(eig_m[-1].item()),
            "GN_solve_relative_residual": float(torch.linalg.vector_norm(gn_residual).item()) / max(float(torch.linalg.vector_norm(gtl).item()), floor),
            "exact_solve_relative_residual": float(torch.linalg.vector_norm(exact_residual).item()) / max(float(torch.linalg.vector_norm(htl).item()), floor),
        },
        "decomposition": {"H_fix_exact": hfix, "C_relax_exact": cexact, "C_relax_GN": cgn, "Delta_GN_fix": delta_gn_fix, "Delta_relax": delta_relax, "exact_error_identity_left": identity_left, "exact_error_identity_right": identity_right, "identity_relative_residual": _relerr(identity_left, identity_right, floor)},
        "metrics": metrics,
        "relaxation_denominator_status": "RELAXATION_DENOMINATOR_SMALL" if small_relax else "AVAILABLE",
        "GN_remainder_diagnostics": {"norm_S_tt_2": norm_stt, "norm_T_tl_2": norm_ttl, "norm_R_ll_2": norm_rll, "norm_G_tl_2": norm_gtl, "norm_Minv": norm_minv, "delta": delta, "bound_applicable": bound is not None, "bound": bound, "actual_GN_remainder": actual, "bound_ratio": actual / bound if bound not in (None, 0.0) else None, "bound_check": bound_check},
        "numerical_checks": checks,
        "numerical_status": "PASS" if all(value is True for value in checks.values()) and bound_check is not False else "NUMERICAL_FAILURE",
    }


def preflight_payload() -> dict[str, Any]:
    torch.set_default_dtype(torch.float64)
    theta = torch.tensor([0.3, -0.2], dtype=torch.float64)
    parameter = torch.tensor([math.log(1.4)], dtype=torch.float64)
    gamma = 0.07

    def residual(t: torch.Tensor, p: torch.Tensor) -> torch.Tensor:
        physical = torch.exp(p[0])
        return torch.stack([t[0] * physical + t[1] ** 2 - 0.4, torch.sin(t[0]) + physical * t[1] + 0.2])

    blocks = curvature_blocks(residual, theta, parameter, gamma)
    historical = full_hessian_references(
        residual,
        theta,
        parameter,
        gamma,
        {
            "positive_eigenvalue_relative_tolerance": 1.0e-12,
            "solve_relative_tolerance": 1.0e-10,
            "symmetry_relative_tolerance": 1.0e-10,
        },
    )
    fraw = _scalar(blocks["G_ll_tensor"])
    cgn = _scalar(blocks["C_relax_GN_tensor"])
    fse = _scalar(blocks["F_SAEPS_tensor"])
    hll = _scalar(blocks["H_ll_tensor"])
    cexact = _scalar(blocks["C_relax_exact_tensor"])
    hred = _scalar(blocks["H_red_exact_tensor"])
    mean_objective = _mean_residual_objective(residual, parameter, theta, 0.0, False)
    residual_count = residual(theta, parameter).numel()
    sum_loss = 0.5 * torch.sum(residual(theta, parameter).square())
    syntax_tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"))
    inverse_calls = [
        node
        for node in ast.walk(syntax_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"inv", "inverse"}
    ]
    checks = {
        "F_raw_equals_G_ll": fraw == _scalar(blocks["G_ll_tensor"]),
        "F_SAEPS_schur": _close(fse, fraw - cgn, 1.0e-12, 1.0e-12),
        "H_red_exact_schur": _close(hred, hll - cexact, 1.0e-12, 1.0e-12),
        "historical_full_hessian_parameter_block": _close(
            hll, float(historical["exact_parameter_block"][0][0]), 1.0e-12, 1.0e-12
        ),
        "historical_full_hessian_gamma_scaling": _close(
            hred,
            float(historical["gamma_matched"]["reduced_hessian"][0][0]),
            1.0e-12,
            1.0e-12,
        ),
        "mean_to_sum_scaling": _close(float(mean_objective(theta).item()) * residual_count, float(sum_loss.item()), 1.0e-12, 1.0e-12),
        "log_parameter_coordinate": _close(float(torch.exp(parameter)[0].item()), 1.4, 1.0e-12, 1.0e-12),
        "solve_not_inverse": not inverse_calls,
        "float64": all(value.dtype == torch.float64 for value in (theta, parameter, blocks["H_tt_tensor"])),
    }
    return {"schema_version": 1, "analysis_classification": CLASSIFICATION, "study_seeds_used": [], "gamma": gamma, "checks": checks, "status": "PASSED" if all(checks.values()) else "FAILED", "timestamp": datetime.now(UTC).isoformat()}


def run_preflight() -> None:
    config = load_config(CONFIG_PATH)
    torch.set_default_dtype(torch.float64)
    env = _expected_environment(config)
    manifests = _manifest_state(config)
    sources = _historical_source_state(config)
    payload = preflight_payload()
    validator = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_repository.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        validator_payload = json.loads(validator.stdout)
    except json.JSONDecodeError:
        validator_payload = {
            "status": "FAILED",
            "stdout": validator.stdout,
            "stderr": validator.stderr,
            "returncode": validator.returncode,
        }
    payload.update(
        environment=env,
        frozen_manifests=manifests,
        historical_sources=sources,
        pre_run_repository_validator=validator_payload,
    )
    if validator.returncode != 0 or validator_payload.get("status") != "PASSED":
        payload["status"] = "FAILED"
    write_json(PREFLIGHT_PATH, payload)
    if payload["status"] != "PASSED":
        raise RuntimeError("preflight failed")
    print(json.dumps({"status": payload["status"], "path": str(PREFLIGHT_PATH)}, indent=2))


def initialize_claim() -> None:
    config = load_config(CONFIG_PATH)
    if CLAIM_PATH.exists():
        raise RuntimeError("execution claim already exists")
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if preflight["status"] != "PASSED":
        raise RuntimeError("preflight is not PASSED")
    env = environment()
    if env["git_status_porcelain"]:
        raise RuntimeError(f"claim requires clean git status: {env['git_status_porcelain']}")
    manifests = _manifest_state(config)
    sources = _historical_source_state(config)
    claim = {
        "schema_version": 1,
        "analysis_name": config["analysis_name"],
        "analysis_classification": CLASSIFICATION,
        "baseline_repo_commit": config["baseline_repo_commit"],
        "current_execution_commit": env["git_commit"],
        "git_status": env["git_status_porcelain"],
        "environment": env,
        "protocol_sha256": sha256(CONFIG_PATH),
        "runner_sha256": sha256(RUNNER_PATH),
        "test_sha256": sha256(TEST_PATH),
        "preflight_sha256": sha256(PREFLIGHT_PATH),
        "source_frozen_evidence": manifests,
        "historical_sources": sources,
        "burgers_planned_seeds": manifests["burgers"]["planned"],
        "allen_cahn_planned_seeds": manifests["allen_cahn"]["planned"],
        "original_valid_seed_sets": {name: value["valid"] for name, value in manifests.items()},
        "original_invalid_seed_sets": {name: value["invalid"] for name, value in manifests.items()},
        "replacement_forbidden": True,
        "rerun_after_scientific_result_forbidden": True,
        "primary_confirmation_claims_changed": False,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    write_json(CLAIM_PATH, claim)
    print(json.dumps({"status": "CLAIMED", "path": str(CLAIM_PATH)}, indent=2))


def _source_record(name: str, seed: int) -> tuple[Path, dict[str, Any]]:
    if name == "burgers":
        path = ROOT / f"outputs/runs/v4_2_corrected_confirmation/records/seed_{seed}.json"
    else:
        path = ROOT / f"outputs/runs/v4_4_allen_cahn_confirmation/architecture_w8/seed_{seed}/result.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def _base_record(name: str, seed: int, original_path: Path, original: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "analysis_classification": CLASSIFICATION,
        "seed": seed,
        "benchmark": "Burgers" if name == "burgers" else "Allen-Cahn",
        "original_status": original["status"],
        "original_binding_valid": bool(original["binding_valid"]),
        "rerun_center_status": "NOT_COMPUTED",
        "reproduction_status": "NOT_COMPUTED",
        "analysis_valid": False,
        "source_frozen_record_path": original_path.relative_to(ROOT).as_posix(),
        "source_frozen_record_sha256": sha256(original_path),
        "environment": claim["environment"],
        "code_config_hashes": {"protocol": claim["protocol_sha256"], "runner": claim["runner_sha256"], "test": claim["test_sha256"]},
        "gamma": None,
        "alpha": None,
        "lambda_max_G_tt": None,
        "original": {key: original.get(source) for key, source in {"F_raw": "F_raw", "F_SAEPS": "F_se_GN", "H_red_exact": "H_red_exact_gamma", "E_raw": "E_raw", "E_SAEPS": "E_SAEPS"}.items()},
        "rerun": None,
        "exact_blocks": None,
        "GN_blocks": None,
        "decomposition": None,
        "metrics": None,
        "GN_remainder_diagnostics": None,
        "numerical_checks": None,
        "failure_reason": None,
    }


def _center_burgers(seed: int) -> tuple[torch.Tensor | None, torch.Tensor | None, ResidualFunction | None, dict[str, Any], dict[str, Any]]:
    v42 = load_config(ROOT / "configs/v4_2/locked_corrected_confirmation.yaml")
    v36 = load_config(ROOT / v42["source_v3_6_scientific_protocol"]["path"])
    scalar = load_config(ROOT / v36["source_files"]["scalar_config"]["path"])
    runtime = _runtime_config(scalar)
    truth = solve_truth(runtime, "Burgers")
    checkpoint, points = train_scalar_checkpoint(runtime, "Burgers", seed, truth)
    residual_function: ResidualFunction = lambda theta, parameter: scalar_residual(theta, parameter, "Burgers", points, truth, runtime)
    parameter = checkpoint.log_parameter.detach().clone()
    objective = _mean_residual_objective(residual_function, parameter, checkpoint.theta, 0.0, False)
    local, enhanced = _center_specs(v36)
    theta, center = center_with_registered_rescue(objective, checkpoint.theta, local, enhanced)
    return theta, parameter, residual_function, center, v36


def _center_allen(seed: int) -> tuple[torch.Tensor | None, torch.Tensor | None, ResidualFunction | None, dict[str, Any], dict[str, Any]]:
    specification = load_config(ROOT / "configs/v4_4/locked_allen_cahn_confirmation.yaml")
    runtime = load_config(ROOT / specification["protected_sources"]["scalar_runtime"]["path"])
    curvature = load_config(ROOT / specification["protected_sources"]["curvature_protocol"]["path"])
    runtime["network"]["hidden_width"] = 8
    truth = solve_truth(runtime, "Allen-Cahn")
    checkpoint, points = train_scalar_checkpoint(runtime, "Allen-Cahn", seed, truth)
    residual_function: ResidualFunction = lambda theta, parameter: scalar_residual(theta, parameter, "Allen-Cahn", points, truth, runtime)
    parameter = checkpoint.log_parameter.detach().clone()
    objective = _mean_residual_objective(residual_function, parameter, checkpoint.theta, 0.0, False)
    local, _ = _center_specs(curvature)
    theta, center = allen_center_candidates(lambda state: residual_function(state, parameter), objective, checkpoint.theta, seed, local, specification["center_engineering"])
    return theta, parameter, residual_function, center, curvature


def _center_valid(name: str, theta: torch.Tensor, parameter: torch.Tensor, residual_function: ResidualFunction, center: dict[str, Any], curvature: dict[str, Any]) -> tuple[bool, dict[str, float]]:
    linearization = ResidualLinearization(residual_function, theta, parameter)
    residual = linearization.residual()
    jt, jl = linearization.explicit_jacobians()
    if name == "burgers":
        selected = center["baseline"] if center["selected_method"] == "baseline_v3_4_exact_trust" else center["enhanced"]
        gtheta = float(selected["final"]["normalized_objective_gradient"])
    else:
        selected = center["candidates"][int(center["selected_candidate"])]
        gtheta = float(selected["final_exact_diagnostics"]["normalized_objective_gradient"])
    stheta = _stationarity(jt, residual)
    slambda = _stationarity(jl, residual)
    passed = gtheta < float(curvature["center"]["required_objective_gradient_tolerance"]) and stheta < float(curvature["center"]["residual_stationarity_tolerance"])
    return passed, {"G_theta": gtheta, "S_theta": stheta, "S_lambda": slambda}


def run_seed(name: str, seed: int, config: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    original_path, original = _source_record(name, seed)
    record = _base_record(name, seed, original_path, original, claim)
    try:
        if name == "burgers":
            theta, parameter, residual_function, center, curvature = _center_burgers(seed)
        else:
            theta, parameter, residual_function, center, curvature = _center_allen(seed)
        record["center_diagnostics"] = center
        if theta is None or parameter is None or residual_function is None:
            record["rerun_center_status"] = "CHECKPOINT_INVALID"
            record["reproduction_status"] = "REPRODUCTION_MISMATCH" if original["binding_valid"] else "NOT_APPLICABLE_ORIGINAL_INVALID"
            record["failure_reason"] = "frozen center policy failed"
            return record
        center_pass, stationarity = _center_valid(name, theta, parameter, residual_function, center, curvature)
        record["center_stationarity"] = stationarity
        record["rerun_center_status"] = "PASS" if center_pass else "CHECKPOINT_INVALID"
        if not center_pass:
            record["reproduction_status"] = "REPRODUCTION_MISMATCH" if original["binding_valid"] else "NOT_APPLICABLE_ORIGINAL_INVALID"
            record["failure_reason"] = "frozen center stationarity gate failed"
            return record
        linearization = ResidualLinearization(residual_function, theta, parameter)
        jt, jl = linearization.explicit_jacobians()
        lambda_max = float(torch.linalg.eigvalsh(jt.T @ jt).max().item())
        alpha = float(curvature["gamma"]["alpha"])
        gamma = alpha * lambda_max
        record.update(alpha=alpha, lambda_max_G_tt=lambda_max, gamma=gamma)
        solver_spec = curvature["curvature_solver"]
        candidates = scaled_augmented_lsqr_candidates(linearization, jl[:, 0], gamma, float(solver_spec["tolerance"]), int(solver_spec["max_iterations_per_pass"]), int(solver_spec["refinement_passes"]))
        selected = candidates["scaled_LSQR_iterative_refinement"]
        selected_fse = float(selected["Fse"])
        blocks = curvature_blocks(residual_function, theta, parameter, gamma)
        explicit_reference = explicit_curvature_reference(jt, jl, gamma)
        analysis = _numeric_analysis(blocks, gamma, original, selected_fse, config)
        record.update({key: analysis[key] for key in ("rerun", "exact_blocks", "GN_blocks", "block_diagnostics", "decomposition", "metrics", "relaxation_denominator_status", "GN_remainder_diagnostics", "numerical_checks", "numerical_status")})
        record["SAEPS_implementation_crosscheck"] = {"existing_explicit": float(explicit_reference["Fse_explicit"]), "existing_LSQR": selected_fse, "new_explicit": analysis["rerun"]["F_SAEPS_explicit"], "explicit_relative_error": _relerr(float(explicit_reference["Fse_explicit"]), analysis["rerun"]["F_SAEPS_explicit"], float(config["tolerances"]["algebraic_absolute_floor"])), "LSQR_vs_explicit_relative_error": _relerr(selected_fse, analysis["rerun"]["F_SAEPS_explicit"], float(config["tolerances"]["algebraic_absolute_floor"]))}
        if original["binding_valid"]:
            rtol = float(config["tolerances"]["reproduction_relative"])
            atol = float(config["tolerances"]["reproduction_absolute"])
            reproduction = {key: {"original": float(record["original"][key]), "rerun": float(record["rerun"][key]), "absolute_error": abs(float(record["rerun"][key]) - float(record["original"][key])), "relative_error": _relerr(float(record["rerun"][key]), float(record["original"][key]), atol), "pass": _close(float(record["rerun"][key]), float(record["original"][key]), rtol, atol)} for key in ("F_raw", "F_SAEPS", "H_red_exact")}
            record["reproduction_checks"] = reproduction
            reproduction_pass = all(row["pass"] for row in reproduction.values())
            record["reproduction_status"] = "REPRODUCTION_PASS" if reproduction_pass else "REPRODUCTION_MISMATCH"
        else:
            reproduction_pass = False
            record["reproduction_status"] = "ORIGINAL_INVALID_RERUN_VALID"
        numerical_pass = analysis["numerical_status"] == "PASS" and record["SAEPS_implementation_crosscheck"]["LSQR_vs_explicit_relative_error"] <= float(config["tolerances"]["algebraic_relative"])
        record["analysis_valid"] = bool(original["binding_valid"] and reproduction_pass and numerical_pass)
        if not numerical_pass:
            record["failure_reason"] = "algebraic or numerical check failed"
        elif original["binding_valid"] and not reproduction_pass:
            record["failure_reason"] = "reproduction mismatch"
        return record
    except Exception as error:
        record["rerun_center_status"] = "NUMERICAL_FAILURE" if record["rerun_center_status"] == "NOT_COMPUTED" else record["rerun_center_status"]
        record["reproduction_status"] = "REPRODUCTION_MISMATCH" if original["binding_valid"] else "NOT_APPLICABLE_ORIGINAL_INVALID"
        record["failure_reason"] = f"{type(error).__name__}: {error}"
        return record
    finally:
        record["runtime_seconds"] = time.perf_counter() - started


def run_study() -> None:
    if not CLAIM_PATH.exists():
        raise RuntimeError("execution claim is absent")
    config = load_config(CONFIG_PATH)
    claim = json.loads(CLAIM_PATH.read_text(encoding="utf-8"))
    for path, expected in ((CONFIG_PATH, claim["protocol_sha256"]), (RUNNER_PATH, claim["runner_sha256"]), (TEST_PATH, claim["test_sha256"]), (PREFLIGHT_PATH, claim["preflight_sha256"])):
        if sha256(path) != expected:
            raise RuntimeError(f"frozen post-hoc file changed: {path}")
    _manifest_state(config)
    _historical_source_state(config)
    torch.set_default_dtype(torch.float64)
    for name, cohort in config["cohorts"].items():
        cohort_dir = OUTPUT_ROOT / name
        for seed_value in cohort["planned_seeds"]:
            seed = int(seed_value)
            path = cohort_dir / f"seed_{seed}.json"
            if path.exists():
                raise RuntimeError(f"formal seed output already exists; rerun forbidden: {path}")
            record = run_seed(name, seed, config, claim)
            write_json(path, record)
            print(json.dumps({"cohort": name, "seed": seed, "original_status": record["original_status"], "rerun_center_status": record["rerun_center_status"], "reproduction_status": record["reproduction_status"], "analysis_valid": record["analysis_valid"], "runtime_seconds": record["runtime_seconds"]}))


def _quantile(values: list[float], probability: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=float), probability, method="linear"))


def _summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    return {"n": len(values), "median": statistics.median(values), "Q25": _quantile(values, 0.25), "Q75": _quantile(values, 0.75), "min": min(values), "max": max(values)}


def aggregate() -> None:
    config = load_config(CONFIG_PATH)
    output: dict[str, Any] = {"schema_version": 1, "analysis_classification": CLASSIFICATION, "baseline_repo_commit": config["baseline_repo_commit"], "primary_confirmation_claims_changed": False, "cohorts": {}}
    csv_rows: list[dict[str, Any]] = []
    metric_names = ["E_raw", "E_SAEPS", "E_fix_exact_to_reduced", "E_GN_fix_native", "E_GN_fix_reduced_scale", "E_relax", "rho_relax", "R_freezing_to_GN", "delta"]
    for name, cohort in config["cohorts"].items():
        records = [json.loads((OUTPUT_ROOT / name / f"seed_{int(seed)}.json").read_text(encoding="utf-8")) for seed in cohort["planned_seeds"]]
        valid = [record for record in records if record["analysis_valid"]]
        summaries = {}
        for metric in metric_names:
            values = []
            for record in valid:
                value = record["GN_remainder_diagnostics"]["delta"] if metric == "delta" else record["metrics"][metric]
                if value is not None:
                    values.append(float(value))
            summaries[metric] = _summary(values)
        output["cohorts"][name] = {
            "planned": len(records),
            "original_binding_valid": sum(record["original_binding_valid"] for record in records),
            "rerun_center_valid_among_original_valid": sum(record["original_binding_valid"] and record["rerun_center_status"] == "PASS" for record in records),
            "reproduction_pass": sum(record["reproduction_status"] == "REPRODUCTION_PASS" for record in records),
            "analysis_valid": len(valid),
            "reproduction_mismatch_seeds": [record["seed"] for record in records if record["reproduction_status"] == "REPRODUCTION_MISMATCH"],
            "original_invalid_rerun_valid_seeds": [record["seed"] for record in records if record["reproduction_status"] == "ORIGINAL_INVALID_RERUN_VALID"],
            "algebraic_or_numerical_failure_seeds": [record["seed"] for record in records if record.get("numerical_status") == "NUMERICAL_FAILURE"],
            "metrics": summaries,
            "descriptive_counts": {
                "E_fix_gt_E_GN_fix_reduced_scale": sum(record["metrics"]["E_fix_exact_to_reduced"] > record["metrics"]["E_GN_fix_reduced_scale"] for record in valid),
                "E_relax_lt_0_1": sum(record["metrics"]["E_relax"] is not None and record["metrics"]["E_relax"] < 0.1 for record in valid),
                "E_relax_lt_0_25": sum(record["metrics"]["E_relax"] is not None and record["metrics"]["E_relax"] < 0.25 for record in valid),
                "rho_relax_0_75_to_1_25": sum(record["metrics"]["rho_relax"] is not None and 0.75 <= record["metrics"]["rho_relax"] <= 1.25 for record in valid),
                "GN_bound_applicable": sum(record["GN_remainder_diagnostics"]["bound_applicable"] for record in valid),
            },
        }
        for record in records:
            row = {"cohort": name, "seed": record["seed"], "original_status": record["original_status"], "original_binding_valid": record["original_binding_valid"], "rerun_center_status": record["rerun_center_status"], "reproduction_status": record["reproduction_status"], "analysis_valid": record["analysis_valid"], "failure_reason": record["failure_reason"]}
            for metric in metric_names:
                row[metric] = (record.get("GN_remainder_diagnostics") or {}).get("delta") if metric == "delta" else (record.get("metrics") or {}).get(metric)
            csv_rows.append(row)
    json_path = ROOT / "docs/evidence/posthoc_exact_fixed_state_v1.json"
    csv_path = ROOT / "docs/evidence/posthoc_exact_fixed_state_v1.csv"
    write_json(json_path, output)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(json.dumps({"json": str(json_path), "csv": str(csv_path), "cohorts": output["cohorts"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preflight", "initialize-claim", "run-study", "aggregate"))
    args = parser.parse_args()
    {"preflight": run_preflight, "initialize-claim": initialize_claim, "run-study": run_study, "aggregate": aggregate}[args.command]()


if __name__ == "__main__":
    main()
