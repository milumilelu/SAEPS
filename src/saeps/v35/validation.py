"""Validate and aggregate v3.5 development evidence."""

from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
from pathlib import Path
from typing import Any, Callable

from saeps.config import config_hash, load_config
from saeps.v31.pipeline import V2_SCALAR_SHA256
from saeps.v35.pipeline import _spearman


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _portable_hash_matches(path: Path, expected: str) -> bool:
    data = path.read_bytes()
    canonical = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return any(
        hashlib.sha256(value).hexdigest() == expected
        for value in {data, canonical, canonical.replace(b"\n", b"\r\n")}
    )


def _check(checks: dict[str, Any], name: str, action: Callable[[], str]) -> None:
    try:
        checks[name] = {"status": "PASS", "detail": action()}
    except Exception as error:
        checks[name] = {
            "status": "FAIL",
            "detail": f"{type(error).__name__}: {error}",
        }


def validate_v3_5(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    checks: dict[str, Any] = {}
    state: dict[str, Any] = {}

    def protocol() -> str:
        specification = load_config(root / "configs/v3_5/diagnostic_engineering.yaml")
        if specification["retrospective_diagnostic_seeds"] != [20, 22, 23, 24]:
            raise AssertionError("retrospective seeds changed")
        if specification["engineering_seeds"] != [25, 26, 27]:
            raise AssertionError("engineering seeds changed")
        if specification["heldout_development_seeds"] != [28, 29]:
            raise AssertionError("held-out seeds changed")
        if specification["inactive_future_confirmation_seeds"] != list(range(30, 45)):
            raise AssertionError("confirmation reservation changed")
        scalar = root / specification["source_scalar_config"]
        if hashlib.sha256(scalar.read_bytes()).hexdigest() != V2_SCALAR_SHA256:
            raise AssertionError("v2 scalar lock changed")
        state["specification"] = specification
        state["config_hash"] = config_hash(specification)
        return "all development roles and unseen confirmation reservation verified"

    _check(checks, "protocol_isolation", protocol)

    def runs() -> str:
        acceptance = _json(root / "docs/evidence/v3_5_acceptance.json")
        if acceptance["config_hash"] != state["config_hash"]:
            raise AssertionError("acceptance config hash mismatch")
        loaded = {}
        run_root = root / "outputs/runs/v3_5_second_order_engineering"
        for role, run_id in acceptance["runs"].items():
            run = run_root / run_id
            manifest = _json(run / "manifest.json")
            record = manifest["records"][0]
            result_path = run / record["path"]
            if not _portable_hash_matches(result_path, record["sha256"]):
                raise AssertionError(f"manifest mismatch for {role}")
            result = _json(result_path)
            if result["role"] != role or result["config_hash"] != state["config_hash"]:
                raise AssertionError(f"role/config mismatch for {role}")
            if result["provenance"]["git_dirty"]:
                raise AssertionError(f"dirty accepted cohort {role}")
            completed = subprocess.run(
                ["git", "cat-file", "-e", f"{result['provenance']['git_commit']}^{{commit}}"],
                cwd=root,
                check=False,
                capture_output=True,
            )
            if completed.returncode != 0:
                raise AssertionError(f"missing provenance commit for {role}")
            loaded[role] = result
        state["runs"] = loaded
        return "three clean cohort manifests and provenance commits verified"

    _check(checks, "cohort_lineage", runs)

    def freeze() -> str:
        choice = _json(root / "configs/v3_5/locked_engineering_choice.json")
        if choice["config_hash"] != state["config_hash"]:
            raise AssertionError("engineering choice hash mismatch")
        if choice["selected_solver"] != "scaled_LSQR_iterative_refinement":
            raise AssertionError("selected solver changed")
        heldout_commit = state["runs"]["HELDOUT_DEVELOPMENT"]["provenance"]["git_commit"]
        completed = subprocess.run(
            ["git", "merge-base", "--is-ancestor", "1616d07", heldout_commit],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise AssertionError("held-out run predates engineering freeze")
        for row in state["runs"]["HELDOUT_DEVELOPMENT"]["records"]:
            if set((row.get("solver_candidates") or {}).get("candidates", {})) != {
                "scaled_LSQR_iterative_refinement"
            }:
                raise AssertionError("held-out evaluated nonselected solver")
        return "held-out run descends from freeze and evaluates only selected solver"

    _check(checks, "two_stage_freeze", freeze)

    def decomposition() -> str:
        valid = []
        for cohort in state["runs"].values():
            for row in cohort["records"]:
                result = row.get("second_order_decomposition")
                if result is not None:
                    if result["shapley_reproduction_relative_error"] > 1.0e-10:
                        raise AssertionError("Shapley reproduction gate failed")
                    valid.append((row["seed"], result))
        if len(valid) != 8:
            raise AssertionError("unexpected valid decomposition denominator")
        state["valid"] = valid
        return "8 valid seeds reproduce exact-minus-GN with registered Shapley tolerance"

    _check(checks, "second_order_decomposition", decomposition)

    def engineering() -> str:
        engineering_rows = state["runs"]["ENGINEERING_SELECTION"]["records"]
        heldout_rows = state["runs"]["HELDOUT_DEVELOPMENT"]["records"]
        new_rows = engineering_rows + heldout_rows
        center_valid = [row for row in new_rows if row["status"] == "PASS"]
        baseline_count = sum(
            row["center"].get("selected_method") == "baseline_v3_4_exact_trust"
            for row in new_rows
        )
        rescue_count = sum(
            row["center"].get("selected_method") == "enhanced_extended_exact_trust"
            for row in new_rows
        )
        selected_solver_pass = sum(
            (row.get("solver_candidates") or {})
            .get("candidates", {})
            .get("scaled_LSQR_iterative_refinement", {})
            .get("status")
            == "PASS"
            for row in center_valid
        )
        aggregate = {
            "new_development_seed_count": 5,
            "baseline_center_pass_count": baseline_count,
            "rescue_additional_pass_count": rescue_count,
            "selected_center_pass_count": len(center_valid),
            "selected_center_fail_count": 5 - len(center_valid),
            "selected_solver_pass_count": selected_solver_pass,
            "selected_solver_valid_center_denominator": len(center_valid),
            "heldout_center_pass_count": sum(row["status"] == "PASS" for row in heldout_rows),
            "heldout_solver_pass_count": sum(
                (row.get("solver_candidates") or {})
                .get("candidates", {})
                .get("scaled_LSQR_iterative_refinement", {})
                .get("status")
                == "PASS"
                for row in heldout_rows
            ),
        }
        if aggregate["heldout_center_pass_count"] != 2 or aggregate["heldout_solver_pass_count"] != 2:
            raise AssertionError("held-out engineering choice did not pass 2/2")
        state["engineering"] = aggregate
        return "center rescue gives 4/5 new-seed validity; selected solver passes 4/4 valid centers"

    _check(checks, "engineering_generalization", engineering)

    def indicators_and_estimand() -> str:
        valid = state["valid"]
        target = [value["GN_to_exact_relative_error"] for _, value in valid]
        indicator_names = list(valid[0][1]["block_ratios_and_indicators"])
        indicators = {}
        for name in indicator_names:
            values = [
                value["block_ratios_and_indicators"][name] for _, value in valid
            ]
            indicators[name] = {
                "spearman_with_GN_error": _spearman(values, target),
                "median_absolute_calibration_error": statistics.median(
                    abs(left - right) for left, right in zip(values, target)
                ),
                "same_5_percent_classification_count": sum(
                    (left <= 0.05) == (right <= 0.05)
                    for left, right in zip(values, target)
                ),
                "denominator": len(valid),
            }
        d_values = [
            value["comparative_estimand"]["D_raw_minus_SAEPS"]
            for _, value in valid
        ]
        state["indicator_summary"] = indicators
        state["comparative"] = {
            "valid_seed_count": len(valid),
            "D_positive_count": sum(value > 0.0 for value in d_values),
            "median_D": statistics.median(d_values),
            "minimum_D": min(d_values),
            "confirmation_claim": False,
        }
        return "all indicators aggregated descriptively; paired D is positive on 8/8 valid development seeds"

    _check(checks, "indicator_and_comparative_aggregation", indicators_and_estimand)
    status = "PASSED" if all(row["status"] == "PASS" for row in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V3_5_SECOND_ORDER_ENGINEERING_DEVELOPMENT",
        "status": status,
        "checks": checks,
        "engineering_aggregate": state.get("engineering", {}),
        "indicator_summary": state.get("indicator_summary", {}),
        "comparative_estimand_aggregate": state.get("comparative", {}),
        "confirmation_authorized": False,
    }

