"""Validate v3.3 seed-20 numerical-decomposition evidence."""

from __future__ import annotations

import hashlib
import json
import math
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


def _relative(left: float, right: float) -> float:
    return abs(left - right) / max(abs(right), 1.0e-8)


def validate_v3_3_seed20(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    checks: dict[str, Any] = {}
    state: dict[str, Any] = {}

    def isolation() -> str:
        specification = load_config(
            root / "configs/v3_3/seed20_numerical_decomposition.yaml"
        )
        if specification["confirmation_authorized"] is not False:
            raise AssertionError("confirmation is unexpectedly authorized")
        if specification["active_seed"] != 20:
            raise AssertionError("active seed is not 20")
        if specification["inactive_development_seeds"] != [21, 22, 23, 24]:
            raise AssertionError("seeds 21-24 are not inactive")
        if specification["inactive_future_confirmation_seeds"] != list(range(30, 45)):
            raise AssertionError("reserved confirmation seeds changed")
        if specification["diagnostic_reporting_scope"] != "NONBINDING_DIAGNOSTIC_ONLY":
            raise AssertionError("diagnostic reporting scope became binding")
        scalar = root / specification["source_scalar_config"]
        if hashlib.sha256(scalar.read_bytes()).hexdigest() != V2_SCALAR_SHA256:
            raise AssertionError("v2 scalar lock changed")
        state["specification"] = specification
        state["config_hash"] = config_hash(specification)
        return "only seed 20 active; v2 and all reserved seeds remain isolated"

    _check(checks, "protocol_isolation", isolation)

    def load_run() -> str:
        evidence = _json(root / "docs/evidence/v3_3_seed20_acceptance.json")
        run = root / "outputs/runs/v3_3_numerical_decomposition" / evidence["run_id"]
        manifest = _json(run / "manifest.json")
        record = manifest["records"][0]
        result_path = run / record["path"]
        if not _portable_hash_matches(result_path, record["sha256"]):
            raise AssertionError("v3.3 raw result hash mismatch")
        result = _json(result_path)
        if result["config_hash"] != state["config_hash"] or result["seed"] != 20:
            raise AssertionError("run config hash or seed mismatch")
        state["result"] = result
        return f"run {result['run_id']} manifest and config hash verified"

    _check(checks, "run_manifest", load_run)

    def center() -> str:
        result = state["result"]
        if result["common_center"]["status"] != "PASS":
            raise AssertionError("common center optimizer failed")
        stationarity = result["center_stationarity"]
        if stationarity["status"] != "PASS":
            raise AssertionError("common center gate failed")
        if stationarity["G_theta"] >= 1.0e-4 or stationarity["S_theta"] >= 1.0e-4:
            raise AssertionError("center first-order tolerance failed")
        return "common center passes first- and exact second-order numerical gates"

    _check(checks, "common_center", center)

    def nodes_and_failures() -> str:
        result = state["result"]
        decomposition = result["development_decomposition"]
        required = {
            "Fse_GN_matrix_free_CG",
            "Fse_GN_explicit_direct",
            "Fse_GN_augmented_LSQR",
            "Hred_exact_gamma",
            "Hprofile_gamma",
        }
        if not required.issubset(decomposition["nodes"]):
            raise AssertionError("one or more registered nodes are missing")
        if decomposition["reporting_scope"] != "NONBINDING_DIAGNOSTIC_ONLY":
            raise AssertionError("decomposition is not marked nonbinding")
        statuses = decomposition["status_by_node"]
        if statuses["Fse_GN_matrix_free_CG"] != "SOLVER_FAILURE":
            raise AssertionError("CG failure was not retained")
        if statuses["Fse_GN_augmented_LSQR"] != "SOLVER_FAILURE":
            raise AssertionError("LSQR auxiliary-RHS failure was not retained")
        if statuses["Hred_exact_gamma"] != "PASS":
            raise AssertionError("exact gamma reduction did not pass")
        if statuses["Hprofile_gamma"] != "PROFILE_FAILURE":
            raise AssertionError("profile failure was not retained")
        return "all nodes retained with explicit solver, exact and profile statuses"

    _check(checks, "four_node_statuses", nodes_and_failures)

    def recompute_segments() -> str:
        decomposition = state["result"]["development_decomposition"]
        nodes = decomposition["nodes"]
        expected = {
            "solver_error_CG_to_explicit": _relative(
                nodes["Fse_GN_matrix_free_CG"], nodes["Fse_GN_explicit_direct"]
            ),
            "solver_error_Jacobi_PCG_to_explicit": _relative(
                nodes["Fse_GN_matrix_free_Jacobi_PCG"],
                nodes["Fse_GN_explicit_direct"],
            ),
            "solver_error_augmented_LSQR_to_explicit": _relative(
                nodes["Fse_GN_augmented_LSQR"], nodes["Fse_GN_explicit_direct"]
            ),
            "GN_approximation_error_explicit_to_exact": _relative(
                nodes["Fse_GN_explicit_direct"], nodes["Hred_exact_gamma"]
            ),
            "nonlinear_profile_error_exact_to_profile": _relative(
                nodes["Hred_exact_gamma"], nodes["Hprofile_gamma"]
            ),
            "total_GN_to_profile_discrepancy": _relative(
                nodes["Fse_GN_explicit_direct"], nodes["Hprofile_gamma"]
            ),
        }
        for name, value in expected.items():
            recorded = decomposition["segment_relative_errors"][name]
            if not math.isclose(recorded, value, rel_tol=1.0e-12, abs_tol=1.0e-15):
                raise AssertionError(f"segment {name} does not reproduce")
        return "all six segment errors reproduce exactly from raw node values"

    _check(checks, "decomposition_reproduction", recompute_segments)

    def decision_mapping() -> str:
        result = state["result"]
        if result["registered_chain_gate"] != "FAIL":
            raise AssertionError("registered failure mapping changed")
        if result["paper_facing_comparison"] is not None:
            raise AssertionError("failed chain produced paper-facing comparison")
        if result["eligible_to_request_activation_of_seeds_21_24"]:
            raise AssertionError("seed expansion was incorrectly enabled")
        return "diagnostic retained; paper-facing output suppressed; seed expansion forbidden"

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
    status = "PASSED" if all(row["status"] == "PASS" for row in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V3_3_NUMERICAL_DECOMPOSITION_DEVELOPMENT",
        "status": status,
        "checks": checks,
        "registered_chain_gate": state.get("result", {}).get("registered_chain_gate"),
        "diagnostic_reporting_scope": "NONBINDING_DIAGNOSTIC_ONLY",
        "confirmation_authorized": False,
        "seeds_21_24_authorized": False,
    }

