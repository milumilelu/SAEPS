"""Validate v3.2 gamma-primary seed-20 development evidence."""

from __future__ import annotations

import hashlib
import json
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
    variants = {data, canonical, canonical.replace(b"\n", b"\r\n")}
    return any(hashlib.sha256(value).hexdigest() == expected for value in variants)


def _check(checks: dict[str, Any], name: str, action: Callable[[], str]) -> None:
    try:
        checks[name] = {"status": "PASS", "detail": action()}
    except Exception as error:
        checks[name] = {
            "status": "FAIL",
            "detail": f"{type(error).__name__}: {error}",
        }


def validate_v3_2_seed20(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    checks: dict[str, Any] = {}
    state: dict[str, Any] = {}

    def isolation() -> str:
        specification = load_config(root / "configs/v3_2/seed20_gamma_primary.yaml")
        if specification["confirmation_authorized"] is not False:
            raise AssertionError("confirmation is unexpectedly authorized")
        if specification["active_seed"] != 20:
            raise AssertionError("active seed is not 20")
        if specification["inactive_development_seeds"] != [21, 22, 23, 24]:
            raise AssertionError("seeds 21-24 are not inactive")
        if specification["inactive_future_confirmation_seeds"] != list(range(30, 45)):
            raise AssertionError("confirmation seed reservation changed")
        scalar = root / specification["source_scalar_config"]
        if hashlib.sha256(scalar.read_bytes()).hexdigest() != V2_SCALAR_SHA256:
            raise AssertionError("v2 scalar lock changed")
        state["specification"] = specification
        state["config_hash"] = config_hash(specification)
        return "only seed 20 active; v2 and all reserved seeds remain isolated"

    _check(checks, "protocol_isolation", isolation)

    def load_run() -> str:
        evidence = _json(root / "docs/evidence/v3_2_seed20_acceptance.json")
        run = root / "outputs/runs/v3_2_gamma_primary" / evidence["run_id"]
        manifest = _json(run / "manifest.json")
        record = manifest["records"][0]
        result_path = run / record["path"]
        if not _portable_hash_matches(result_path, record["sha256"]):
            raise AssertionError("v3.2 raw result hash mismatch")
        result = _json(result_path)
        if result["seed"] != 20 or result["config_hash"] != state["config_hash"]:
            raise AssertionError("run seed or config hash mismatch")
        state["result"] = result
        return f"run {result['run_id']} manifest and config hash verified"

    _check(checks, "run_manifest", load_run)

    def center() -> str:
        result = state["result"]
        center = result["common_center"]
        stationarity = result["center_stationarity"]
        if center["status"] != "PASS" or center["final"]["local_minimum_gate"] != "PASS":
            raise AssertionError("common center local-minimum gate failed")
        if stationarity["status"] != "PASS":
            raise AssertionError("common center first-order gate failed")
        if stationarity["G_theta"] >= 1.0e-4 or stationarity["S_theta"] >= 1.0e-4:
            raise AssertionError("common center exceeds required tolerance")
        if stationarity.get("S_lambda") is None:
            raise AssertionError("S_lambda was not recorded")
        return "common center passes G_theta, S_theta and exact second-order gates; S_lambda recorded"

    _check(checks, "common_center", center)

    def profile_structure() -> str:
        result = state["result"]
        gamma_profile = result["gamma_matched_primary"]
        unregularized = result["unregularized_secondary"]
        if gamma_profile["role"] != "PRIMARY" or unregularized["role"] != "SECONDARY_DIAGNOSTIC":
            raise AssertionError("profile roles are incorrect")
        for profile in [gamma_profile, unregularized]:
            for level_name, tolerance in [("nominal", 1.0e-4), ("strict", 1.0e-6)]:
                level = profile["accuracy_levels"][level_name]
                if level["gradient_tolerance"] != tolerance:
                    raise AssertionError("accuracy-level gradient tolerance mismatch")
                if len(level["points"]) != 8 or level["passed_points"] != 8:
                    raise AssertionError("profile accuracy level is not 8/8")
                positive = level["branches"]["positive"]
                negative = level["branches"]["negative"]
                if [row["parent_offset"] for row in positive] != [0.0, 0.00625, 0.0125, 0.025]:
                    raise AssertionError("positive continuation lineage is wrong")
                if [row["parent_offset"] for row in negative] != [0.0, -0.00625, -0.0125, -0.025]:
                    raise AssertionError("negative continuation lineage is wrong")
        return "primary/secondary roles, 8/8 accuracy levels and both continuation lineages verified"

    _check(checks, "profile_structure", profile_structure)

    def primary_profile_result() -> str:
        profile = state["result"]["gamma_matched_primary"]
        strict = profile["accuracy_levels"]["strict"]
        if strict["points_gate"] != "PASS":
            raise AssertionError("strict gamma profile points unexpectedly failed")
        if profile["status"] != "PROFILE_FAILURE":
            raise AssertionError("binding gamma profile failure was not retained")
        if strict["multiscale_gate"] != "FAIL" or profile["optimization_accuracy_gate"] != "FAIL":
            raise AssertionError("gamma failure decomposition is incorrect")
        return "gamma 8/8 passes; multiscale and finest-scale accuracy failures retained separately"

    _check(checks, "gamma_primary_result", primary_profile_result)

    def solver_and_hessian() -> str:
        result = state["result"]
        krylov = result["krylov_gate"]
        exact = result["full_hessian"]
        if krylov["status"] != "SOLVER_FAILURE" or krylov["solver_failure_count"] == 0:
            raise AssertionError("Krylov failure was not retained")
        if exact["gamma_matched"]["status"] != "PASS":
            raise AssertionError("exact gamma-matched reduction did not pass")
        if exact["unregularized"]["status"] != "NUMERICAL_FAILURE":
            raise AssertionError("unregularized exact-Hessian diagnostic changed")
        return "standard CG/PCG failures and successful exact gamma reduction verified"

    _check(checks, "solver_and_exact_hessian", solver_and_hessian)

    def decision_mapping() -> str:
        result = state["result"]
        if result["unregularized_is_binding"] is not False:
            raise AssertionError("unregularized profile became binding")
        if result["primary_chain_gate"] != "FAIL" or result["primary_comparison"] is not None:
            raise AssertionError("primary failure mapping is incorrect")
        if result["eligible_to_request_activation_of_seeds_21_24"]:
            raise AssertionError("seed expansion was incorrectly made eligible")
        return "primary chain FAIL; secondary unregularized result is nonbinding; seed expansion forbidden"

    _check(checks, "decision_mapping", decision_mapping)

    def provenance() -> str:
        info = state["result"]["provenance"]
        if info["git_dirty"]:
            raise AssertionError("formal run used a dirty worktree")
        completed = subprocess.run(
            ["git", "cat-file", "-e", f"{info['git_commit']}^{{commit}}"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise AssertionError("formal-run commit unavailable")
        return f"clean formal-run commit {info['git_commit']} verified"

    _check(checks, "provenance", provenance)
    status = "PASSED" if all(item["status"] == "PASS" for item in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V3_2_GAMMA_PRIMARY_DEVELOPMENT",
        "status": status,
        "checks": checks,
        "primary_chain_gate": state.get("result", {}).get("primary_chain_gate"),
        "confirmation_authorized": False,
        "seeds_21_24_authorized": False,
    }
