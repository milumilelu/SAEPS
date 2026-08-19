"""Repository-level validation for the v3 foundation development run."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from saeps.config import config_hash, load_config


V2_SCALAR_SHA256 = "cb5c2e9e3eee2d5462dd92ac0b9cd3b2b607ea487367d9c83b18a3a8af9c5cf8"
FINAL_STATUSES = {
    "PASS",
    "CHECKPOINT_INVALID",
    "PROFILE_FAILURE",
    "SOLVER_FAILURE",
    "NUMERICAL_FAILURE",
}


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_matches_with_portable_newlines(path: Path, expected: str) -> bool:
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


def validate_v3_foundation(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    checks: dict[str, Any] = {}
    state: dict[str, Any] = {}

    def isolation() -> str:
        specification = load_config(root / "configs/v3/foundation_development.yaml")
        if specification["confirmation_authorized"] is not False:
            raise AssertionError("v3 confirmation is unexpectedly authorized")
        if specification["foundation_validation_seed"] != 20:
            raise AssertionError("foundation seed must be 20")
        if set(specification["reserved_development_seeds"]) & set(range(10, 20)):
            raise AssertionError("v3 development overlaps v2 confirmation seeds")
        scalar = root / specification["source_scalar_config"]
        if hashlib.sha256(scalar.read_bytes()).hexdigest() != V2_SCALAR_SHA256:
            raise AssertionError("v2 scalar lock hash changed")
        state["specification"] = specification
        state["config_hash"] = config_hash(specification)
        return "v3 remains development-only; seed and v2 lock isolation verified"

    _check(checks, "protocol_isolation", isolation)

    def v2_snapshot() -> str:
        snapshot = _json(root / "docs/evidence/v2_data_snapshot.json")
        for item in snapshot["files"]:
            path = root / item["path"]
            if not path.is_file():
                raise AssertionError(f"v2 snapshot path missing: {item['path']}")
            canonical = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            if len(canonical) != item["canonical_lf_bytes"]:
                raise AssertionError(f"v2 canonical size changed: {item['path']}")
            if hashlib.sha256(canonical).hexdigest() != item["canonical_lf_sha256"]:
                raise AssertionError(f"v2 snapshot hash changed: {item['path']}")
        return f"{len(snapshot['files'])} immutable v2 raw/artifact files verified"

    _check(checks, "v2_snapshot", v2_snapshot)

    def load_run() -> str:
        evidence = _json(root / "docs/evidence/v3_foundation_acceptance.json")
        run = root / "outputs/runs/v3_foundation" / evidence["run_id"]
        manifest = _json(run / "manifest.json")
        if len(manifest["records"]) != 1:
            raise AssertionError("foundation manifest must contain exactly one result")
        record = manifest["records"][0]
        result_path = run / record["path"]
        if not _hash_matches_with_portable_newlines(result_path, record["sha256"]):
            raise AssertionError("foundation result hash mismatch")
        result = _json(result_path)
        if result["status"] not in FINAL_STATUSES:
            raise AssertionError("illegal foundation result status")
        state["result"] = result
        return f"run {result['run_id']} manifest and raw hash verified"

    _check(checks, "run_manifest", load_run)

    def common_base() -> str:
        result = state["result"]
        base = result["common_base_refinement"]
        if result["engineering_gate"] != "PASSED" or base["status"] != "PASS":
            raise AssertionError("common base engineering gate did not pass")
        required = [
            "initial_normalized_state_gradient",
            "refined_normalized_state_gradient",
            "delta_theta_relative",
            "delta_loss_relative",
            "theta_stationarity_residual_normalized",
        ]
        if any(base.get(key) is None for key in required):
            raise AssertionError("common base metrics are incomplete")
        return "one refined common base supplies every v3 curvature calculation"

    _check(checks, "common_base", common_base)

    def curvature_references() -> str:
        result = state["result"]
        gauss_newton = result["gauss_newton"]
        if any(gauss_newton.get(key) is None for key in ["Fraw", "Fse_explicit"]):
            raise AssertionError("Gauss-Newton reference is incomplete")
        hessian = result["full_hessian"]
        if hessian.get("symmetry_relative_error") is None:
            raise AssertionError("full-Hessian symmetry was not audited")
        for name in ["unregularized", "gamma_matched"]:
            reduced = hessian[name]
            required = [
                "minimum_state_eigenvalue",
                "maximum_state_eigenvalue",
                "nonpositive_eigenvalue_count",
                "status",
            ]
            if any(key not in reduced for key in required):
                raise AssertionError(f"full-Hessian diagnostics missing for {name}")
        return "Gauss-Newton and both exact full-Hessian reductions are machine-readable"

    _check(checks, "curvature_references", curvature_references)

    def profiles() -> str:
        result = state["result"]
        expected_h = [0.05, 0.025, 0.0125, 0.00625]
        for name in ["unregularized", "gamma_matched"]:
            profile = result["profiles"][name]
            if len(profile["points"]) != 8:
                raise AssertionError(f"{name} does not contain eight planned points")
            if not profile["all_points_have_final_status"]:
                raise AssertionError(f"{name} contains a point without final status")
            if any(point["status"] not in FINAL_STATUSES for point in profile["points"]):
                raise AssertionError(f"{name} contains an illegal point status")
            observed_h = [item["h"] for item in profile["curvature_estimates_unnormalized"]]
            if observed_h != expected_h or len(profile["adjacent_convergence"]) != 3:
                raise AssertionError(f"{name} multiscale grid is incomplete")
        matched = result["profiles"]["gamma_matched"]
        if matched["objective_scaling"] != (
            "0.5*mean(r^2) + gamma/(2*m)*||theta-theta_base||^2"
        ):
            raise AssertionError("gamma-matched mean-loss scaling is wrong")
        return "dual profiles and the registered multiscale convergence grid verified"

    _check(checks, "dual_multiscale_profiles", profiles)

    def provenance() -> str:
        result = state["result"]
        info = result["provenance"]
        if info["git_dirty"]:
            raise AssertionError("formal v3 run used a dirty worktree")
        commit = info["git_commit"]
        completed = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError("formal-run git commit is not available")
        if result["config_hash"] != state["config_hash"]:
            raise AssertionError("formal-run configuration hash changed")
        return f"clean formal-run commit {commit} and configuration hash verified"

    _check(checks, "provenance", provenance)
    status = "PASSED" if all(item["status"] == "PASS" for item in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V3_FOUNDATION_DEVELOPMENT",
        "status": status,
        "checks": checks,
        "scientific_failure_is_engineering_failure": False,
        "confirmation_authorized": False,
    }
