"""Static validation for the v3.6 lock; this module never runs a seed."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from saeps.config import load_config


def _check(checks: dict[str, Any], name: str, action: Callable[[], str]) -> None:
    try:
        checks[name] = {"status": "PASS", "detail": action()}
    except Exception as error:
        checks[name] = {"status": "FAIL", "detail": f"{type(error).__name__}: {error}"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_v3_6_lock(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    config_path = root / "configs/v3_6/locked_scalar_confirmation.yaml"
    lock_record_path = root / "configs/v3_6/LOCK_RECORD.json"
    checks: dict[str, Any] = {}
    state: dict[str, Any] = {}

    def protocol() -> str:
        specification = load_config(config_path)
        if specification["protocol_locked"] is not True:
            raise AssertionError("protocol is not locked")
        if specification["execution_authorized"] is not False:
            raise AssertionError("this lock-only increment must not authorize execution")
        if specification["planned_seeds"] != list(range(30, 45)):
            raise AssertionError("planned seeds must be exactly 30--44")
        if len(set(specification["planned_seeds"])) != 15:
            raise AssertionError("planned seeds must be unique")
        if specification["scope"] != {
            "included": "scalar_curvature_only",
            "excluded": ["score", "parameter_update", "multi_parameter", "nonlinear_profile"],
        }:
            raise AssertionError("v3.6 scope changed")
        state["specification"] = specification
        return "locked, unauthorized, curvature-only protocol with exact seeds 30--44"

    _check(checks, "protocol_and_scope", protocol)

    def lineage() -> str:
        specification = state["specification"]
        for source in specification["source_files"].values():
            path = root / source["path"]
            if _sha256(path) != source["sha256"]:
                raise AssertionError(f"source hash changed: {source['path']}")
        choice = json.loads(
            (root / "configs/v3_5/locked_engineering_choice.json").read_text(encoding="utf-8")
        )
        if choice["selected_center"] != "baseline_then_enhanced_extended_exact_trust":
            raise AssertionError("center selection differs from v3.5 freeze")
        if choice["selected_solver"] != "scaled_LSQR_iterative_refinement":
            raise AssertionError("solver selection differs from v3.5 freeze")
        if choice["solver_refinement_passes"] != 2:
            raise AssertionError("refinement count differs from v3.5 freeze")
        return "all three source hashes and v3.5 frozen engineering choices match"

    _check(checks, "frozen_lineage", lineage)

    def numerical_chain() -> str:
        specification = state["specification"]
        if specification["center"]["policy"] != "baseline_then_frozen_enhanced_rescue":
            raise AssertionError("center policy changed")
        solver = specification["curvature_solver"]
        if solver["selected"] != "scaled_LSQR_iterative_refinement":
            raise AssertionError("solver changed")
        if solver["refinement_passes"] != 2 or solver["maximum_total_iterations"] != 1500:
            raise AssertionError("solver refinement budget changed")
        if specification["gamma"] != {
            "definition": "alpha_times_lambda_max_of_JthetaT_Jtheta_at_center",
            "alpha": 1.0e-8,
        }:
            raise AssertionError("gamma definition changed")
        if specification["gold_standard"]["quantity"] != "exact_finite_gamma_reduced_Hessian":
            raise AssertionError("gold standard changed")
        return "center, two-pass scaled-LSQR, gamma and exact finite-gamma gold are frozen"

    _check(checks, "numerical_chain", numerical_chain)

    def primary() -> str:
        specification = state["specification"]
        primary_spec = specification["primary"]
        expected = {
            "planned_denominator": 15,
            "minimum_valid_pairs": 12,
            "planned_seed_wins_required": 12,
            "valid_pair_median_D_must_be_positive": True,
            "test": "exact_one_sided_paired_sign_test",
            "null_success_probability": 0.5,
            "alpha": 0.05,
            "continuity_correction": False,
            "success_requires_all_primary_conditions": True,
        }
        for key, value in expected.items():
            if primary_spec[key] != value:
                raise AssertionError(f"primary rule changed: {key}")
        if not specification["valid_pair"]["invalid_seed_retained_in_planned_denominator"]:
            raise AssertionError("invalid planned seeds must remain in denominator")
        if specification["errors"]["D"] != "E_raw_minus_E_SAEPS":
            raise AssertionError("primary estimand changed")
        if specification["errors"]["Fse_GN_source"] != "selected_scaled_LSQR_iterative_refinement":
            raise AssertionError("primary SAEPS curvature source changed")
        return "paired D, 12/15 planned wins, positive median and exact one-sided sign test frozen"

    _check(checks, "primary_estimand_and_test", primary)

    def secondary_and_indicator() -> str:
        specification = state["specification"]
        secondary = specification["secondary"]
        if secondary["five_percent_is_universal_accuracy_requirement"] is not False:
            raise AssertionError("5% was incorrectly restored as universal gate")
        if secondary["IQR_definition"] != "q25_and_q75_numpy_linear_quantiles_then_q75_minus_q25":
            raise AssertionError("secondary IQR convention changed")
        indicator = specification["gn_indicator"]
        if indicator["name"] != "first_order_correction_relative_to_GN":
            raise AssertionError("indicator identity changed")
        if indicator["threshold"] != 0.05 or indicator["recalibration_forbidden"] is not True:
            raise AssertionError("indicator classification is not frozen")
        if indicator["role"] != "secondary_nonbinding_diagnostic":
            raise AssertionError("indicator was promoted to a primary gate")
        return "absolute SAEPS error and fixed 5% GN-indicator classification are secondary"

    _check(checks, "secondary_and_indicator", secondary_and_indicator)

    def lock_record() -> str:
        record = json.loads(lock_record_path.read_text(encoding="utf-8"))
        current_hash = _sha256(config_path)
        if record["locked_config_sha256"] != current_hash:
            raise AssertionError("locked config raw hash mismatch")
        commit = record["lock_commit"]
        completed = subprocess.run(
            ["git", "show", f"{commit}:configs/v3_6/locked_scalar_confirmation.yaml"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise AssertionError("lock commit does not contain the protocol")
        if hashlib.sha256(completed.stdout).hexdigest() != current_hash:
            raise AssertionError("current protocol differs from first locked commit")
        state["config_sha256"] = current_hash
        state["lock_commit"] = commit
        return "current bytes equal the separately recorded first lock commit"

    _check(checks, "immutable_lock_record", lock_record)

    def no_execution() -> str:
        run_root = root / "outputs/runs"
        existing = [
            str(path.relative_to(root))
            for path in run_root.glob("v3_6*")
            if path.exists()
        ]
        if existing:
            raise AssertionError(f"v3.6 run output exists during lock-only phase: {existing}")
        return "no v3.6 confirmation output directory exists"

    _check(checks, "no_confirmation_execution", no_execution)
    status = "PASSED" if all(row["status"] == "PASS" for row in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V3_6_SCALAR_CONFIRMATION_LOCK",
        "status": status,
        "checks": checks,
        "protocol_locked": True,
        "execution_authorized": False,
        "planned_seeds": list(range(30, 45)),
        "locked_config_sha256": state.get("config_sha256"),
        "lock_commit": state.get("lock_commit"),
        "confirmation_runs_executed": 0,
    }
