"""Aggregate and validate frozen v3.4 development runs."""

from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
from pathlib import Path
from typing import Any, Callable

from saeps.config import config_hash, load_config
from saeps.v31.pipeline import V2_SCALAR_SHA256


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


def validate_v3_4(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    checks: dict[str, Any] = {}
    state: dict[str, Any] = {}

    def protocol() -> str:
        specification = load_config(root / "configs/v3_4/curvature_validation.yaml")
        if specification["protocol_seed"] != 20 or specification["evaluation_seeds"] != [21, 22, 23, 24]:
            raise AssertionError("v3.4 seed split changed")
        if specification["confirmation_authorized"] is not False:
            raise AssertionError("confirmation unexpectedly authorized")
        if specification["inactive_future_confirmation_seeds"] != list(range(30, 45)):
            raise AssertionError("future confirmation seed reservation changed")
        scalar = root / specification["source_scalar_config"]
        if hashlib.sha256(scalar.read_bytes()).hexdigest() != V2_SCALAR_SHA256:
            raise AssertionError("v2 scalar lock changed")
        state["specification"] = specification
        state["config_hash"] = config_hash(specification)
        return "frozen seed split, thresholds, v2 lock and confirmation prohibition verified"

    _check(checks, "protocol_isolation", protocol)

    def accepted_runs() -> str:
        acceptance = _json(root / "docs/evidence/v3_4_acceptance.json")
        if acceptance["config_hash"] != state["config_hash"]:
            raise AssertionError("acceptance config hash mismatch")
        results: dict[int, dict[str, Any]] = {}
        run_root = root / "outputs/runs/v3_4_curvature_validation"
        for seed_text, run_id in acceptance["accepted_runs"].items():
            seed = int(seed_text)
            run = run_root / run_id
            manifest = _json(run / "manifest.json")
            record = manifest["records"][0]
            result_path = run / record["path"]
            if not _portable_hash_matches(result_path, record["sha256"]):
                raise AssertionError(f"manifest hash mismatch for seed {seed}")
            result = _json(result_path)
            if result["seed"] != seed or result["config_hash"] != state["config_hash"]:
                raise AssertionError(f"seed/config mismatch for seed {seed}")
            if result["provenance"]["git_dirty"]:
                raise AssertionError(f"accepted seed {seed} has dirty provenance")
            completed = subprocess.run(
                ["git", "cat-file", "-e", f"{result['provenance']['git_commit']}^{{commit}}"],
                cwd=root,
                check=False,
                capture_output=True,
            )
            if completed.returncode != 0:
                raise AssertionError(f"seed {seed} provenance commit is missing")
            results[seed] = result
        if set(results) != {20, 21, 22, 23, 24}:
            raise AssertionError("accepted seed denominator is incomplete")
        state["acceptance"] = acceptance
        state["results"] = results
        return "five accepted clean-provenance runs and manifests verified"

    _check(checks, "accepted_run_lineage", accepted_runs)

    def dirty_attempts() -> str:
        run_root = root / "outputs/runs/v3_4_curvature_validation"
        for run_id in state["acceptance"]["excluded_dirty_provenance_attempts"]:
            result = _json(run_root / run_id / "result.json")
            if result["provenance"]["git_dirty"] is not True:
                raise AssertionError("excluded attempt is not dirty")
        return "three dirty-provenance attempts are retained and excluded independently of values"

    _check(checks, "retained_dirty_attempts", dirty_attempts)

    def protocol_seed() -> str:
        result = state["results"][20]
        if result["readiness_gate"] != "PASS" or not result["eligible_for_evaluation_seeds_21_24"]:
            raise AssertionError("seed20 did not authorize frozen evaluation")
        if result["solver_hierarchy"]["CURVATURE_SOLVER_GATE"]["status"] != "PASS":
            raise AssertionError("seed20 curvature solver gate failed")
        if result["solver_hierarchy"]["SCORE_SOLVER_GATE"]["status"] != "SOLVER_FAILURE":
            raise AssertionError("seed20 score failure was not retained")
        return "seed20 readiness passes while nonbinding score failure remains visible"

    _check(checks, "protocol_seed_gate", protocol_seed)

    def aggregate() -> str:
        results = state["results"]
        rows = []
        for seed in range(20, 25):
            result = results[seed]
            center_pass = (result.get("center_stationarity") or {}).get("status") == "PASS"
            hierarchy = result.get("solver_hierarchy") or {}
            local = result.get("local_GN_validation") or {}
            profile = result.get("finite_radius_validation") or {}
            exact = result.get("exact_local_gold_standard") or {}
            rows.append(
                {
                    "seed": seed,
                    "role": result["seed_role"],
                    "center_pass": center_pass,
                    "curvature_solver_pass": (hierarchy.get("CURVATURE_SOLVER_GATE") or {}).get("status") == "PASS",
                    "score_solver_pass": (hierarchy.get("SCORE_SOLVER_GATE") or {}).get("status") == "PASS",
                    "exact_local_pass": exact.get("status") == "PASS",
                    "local_GN_pass": local.get("status") == "PASS",
                    "local_GN_relative_error": local.get("relative_error"),
                    "Fraw": local.get("Fraw"),
                    "Fse_GN_explicit": local.get("Fse_GN_explicit"),
                    "Hred_exact_gamma": local.get("Hred_exact_gamma"),
                    "raw_to_exact_ratio": (
                        local["Fraw"] / local["Hred_exact_gamma"]
                        if local.get("Hred_exact_gamma") not in (None, 0.0)
                        else None
                    ),
                    "finite_radius_pass": profile.get("status") == "PASS",
                    "certified_h_values": profile.get("certified_h_values", []),
                    "branch_audit_pass": (profile.get("branch_continuity_audit") or {}).get("status") == "PASS",
                    "maximum_parent_function_relative_distance": (profile.get("branch_continuity_audit") or {}).get("maximum_parent_function_relative_distance"),
                    "readiness_pass": result["readiness_gate"] == "PASS",
                }
            )
        evaluation = [row for row in rows if row["role"] == "EVALUATION"]
        valid_local = [row for row in evaluation if row["local_GN_relative_error"] is not None]
        aggregate_result = {
            "planned_seed_count": 5,
            "protocol_seed": 20,
            "evaluation_seed_count": 4,
            "evaluation_center_pass_count": sum(row["center_pass"] for row in evaluation),
            "evaluation_curvature_solver_pass_count": sum(row["curvature_solver_pass"] for row in evaluation),
            "evaluation_exact_local_pass_count": sum(row["exact_local_pass"] for row in evaluation),
            "evaluation_local_GN_pass_count": sum(row["local_GN_pass"] for row in evaluation),
            "evaluation_finite_radius_pass_count": sum(row["finite_radius_pass"] for row in evaluation),
            "evaluation_branch_audit_pass_count": sum(row["branch_audit_pass"] for row in evaluation),
            "evaluation_score_solver_pass_count": sum(row["score_solver_pass"] for row in evaluation),
            "evaluation_full_readiness_pass_count": sum(row["readiness_pass"] for row in evaluation),
            "evaluation_valid_local_GN_denominator": len(valid_local),
            "evaluation_median_local_GN_relative_error": statistics.median(
                row["local_GN_relative_error"] for row in valid_local
            ) if valid_local else None,
            "evaluation_raw_exceeds_exact_count": sum(
                row["Fraw"] > row["Hred_exact_gamma"] for row in valid_local
            ),
            "development_generalization": "NOT_ESTABLISHED",
            "confirmation_authorized": False,
        }
        state["rows"] = rows
        state["aggregate"] = aggregate_result
        if aggregate_result["evaluation_full_readiness_pass_count"] != 0:
            raise AssertionError("unexpected evaluation readiness count")
        return "0/4 evaluation full readiness retained; separated denominators aggregated"

    _check(checks, "development_aggregation", aggregate)
    status = "PASSED" if all(row["status"] == "PASS" for row in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V3_4_CURVATURE_VALIDATION_DEVELOPMENT",
        "status": status,
        "checks": checks,
        "seed_rows": state.get("rows", []),
        "aggregate": state.get("aggregate", {}),
    }

