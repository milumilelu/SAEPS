"""Validate v3.1 seed-20 evidence and strict serial stopping."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from saeps.config import config_hash, load_config


V2_SCALAR_SHA256 = "cb5c2e9e3eee2d5462dd92ac0b9cd3b2b607ea487367d9c83b18a3a8af9c5cf8"


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


def validate_v3_1_seed20(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    checks: dict[str, Any] = {}
    state: dict[str, Any] = {}

    def isolation() -> str:
        specification = load_config(root / "configs/v3_1/seed20_development.yaml")
        if specification["confirmation_authorized"] is not False:
            raise AssertionError("confirmation is unexpectedly authorized")
        if specification["active_seed"] != 20:
            raise AssertionError("active seed is not 20")
        if specification["inactive_development_seeds"] != [21, 22, 23, 24]:
            raise AssertionError("seeds 21-24 are not inactive")
        if specification["inactive_future_confirmation_seeds"] != list(range(30, 45)):
            raise AssertionError("future confirmation seed reservation changed")
        scalar = root / specification["source_scalar_config"]
        if hashlib.sha256(scalar.read_bytes()).hexdigest() != V2_SCALAR_SHA256:
            raise AssertionError("v2 scalar lock changed")
        state["specification"] = specification
        state["config_hash"] = config_hash(specification)
        return "only seed 20 active; v2 lock and all reserved seeds remain isolated"

    _check(checks, "protocol_isolation", isolation)

    def load_run() -> str:
        evidence = _json(root / "docs/evidence/v3_1_seed20_acceptance.json")
        run = root / "outputs/runs/v3_1_state_minimum" / evidence["run_id"]
        manifest = _json(run / "manifest.json")
        record = manifest["records"][0]
        result_path = run / record["path"]
        if not _portable_hash_matches(result_path, record["sha256"]):
            raise AssertionError("v3.1 raw result hash mismatch")
        result = _json(result_path)
        if result["seed"] != 20 or result["config_hash"] != state["config_hash"]:
            raise AssertionError("run seed or config hash mismatch")
        state["result"] = result
        return f"run {result['run_id']} manifest and config hash verified"

    _check(checks, "run_manifest", load_run)

    def center() -> str:
        result = state["result"]
        local = result["center_local_minimum"]
        if local["status"] != "PASS" or local["final"]["local_minimum_gate"] != "PASS":
            raise AssertionError("center did not pass the exact local-minimum gate")
        if local["final"]["normalized_objective_gradient"] > 1.0e-4:
            raise AssertionError("center objective-gradient tolerance failed")
        stationarity = result["center_residual_stationarity"]
        if stationarity["status"] != "PASS" or stationarity["S_theta"] > 1.0e-4:
            raise AssertionError("center residual stationarity failed")
        if not local["negative_direction_probes"]:
            raise AssertionError("saddle escape was not audited")
        return "center passes common gradient, residual stationarity and exact Hessian gates"

    _check(checks, "center_local_minimum", center)

    def unregularized_profile() -> str:
        profile = state["result"]["unregularized_profile"]
        if len(profile["points"]) != 8 or profile["passed_points"] != 8:
            raise AssertionError("unregularized profile is not 8/8 local-minimum valid")
        for point in profile["points"]:
            final = point["optimization"]["final"]
            if point["status"] != "PASS" or final["local_minimum_gate"] != "PASS":
                raise AssertionError("profile point failed first/second-order gate")
            if final["gradient_tolerance"] != 1.0e-4:
                raise AssertionError("center/profile gradient tolerance mismatch")
        if len(profile["curvature_estimates_unnormalized"]) != 4:
            raise AssertionError("four-scale curvature grid is incomplete")
        return f"8/8 points pass; multiscale status is retained as {profile['status']}"

    _check(checks, "unregularized_profile", unregularized_profile)

    def serial_stop() -> str:
        result = state["result"]
        if result["unregularized_profile"]["status"] == "PASS":
            raise AssertionError("accepted evidence unexpectedly has a passing unregularized profile")
        if result["serial_stop_stage"] != "UNREGULARIZED_PROFILE":
            raise AssertionError("serial stop stage is wrong")
        forbidden = [
            result["gamma_matched_profile"],
            result["krylov_gate"],
            result["full_hessian"],
            result["curvature_comparison"],
        ]
        if any(value is not None for value in forbidden):
            raise AssertionError("downstream stages ran after the binding profile failure")
        if result["full_chain_gate"] != "FAIL":
            raise AssertionError("full-chain failure was not retained")
        if result["eligible_to_request_activation_of_seeds_21_24"]:
            raise AssertionError("seeds 21-24 were incorrectly made eligible")
        return "binding profile failure stopped all downstream work and seed expansion"

    _check(checks, "serial_stop_discipline", serial_stop)

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
            raise AssertionError("formal-run commit is unavailable")
        return f"clean formal-run commit {info['git_commit']} verified"

    _check(checks, "provenance", provenance)
    status = "PASSED" if all(item["status"] == "PASS" for item in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V3_1_STATE_MINIMUM_DEVELOPMENT",
        "status": status,
        "checks": checks,
        "full_chain_gate": state.get("result", {}).get("full_chain_gate"),
        "confirmation_authorized": False,
        "seeds_21_24_authorized": False,
    }
