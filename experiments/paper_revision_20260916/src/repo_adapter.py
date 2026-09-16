"""Read-only adapter that rebuilds frozen SAEPS evidence for the paper-revision experiments.

Every historical input is read with ``git show`` at an immutable commit, so the working
tree is never modified and the frozen record stays authoritative.  Nothing in this module
trains, writes over a historical artifact, or substitutes for a missing run: a gap is
reported as a gap.

Implements the input half of ``ADAPTER_CONTRACT.md``.  The loss convention is the
exported sum objective

    ell(theta, lambda) = 1/2 sum_i r_i(theta, lambda)^2,

which is the historical training objective ``1/2 mean_i r_i^2`` scaled by the residual
count m.  Callers that compare against a mean-scaled quantity must divide by m.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_REF = "jcp-submission-v1"
TWO_PARAMETER_SEEDS = tuple(range(215, 225))
SCALAR_COHORTS = {
    "Burgers": tuple(range(55, 70)),
    "Allen-Cahn": tuple(range(75, 85)),
}
TWO_PARAMETER_CHECKPOINT_ROOT = "outputs/runs/v5/checkpoints/two_parameter_confirmation"
SCALAR_POSTHOC_ROOT = "outputs/posthoc/exact_fixed_state_v3"
LOCKED_MULTI_CONFIG = "configs/locked/multi.yaml"
TWO_PARAMETER_EXECUTION_CONFIG = "configs/v5/two_parameter_development_execution.yaml"


def repo_root() -> Path:
    """Repository root implied by this file's location."""
    return Path(__file__).resolve().parents[3]


def git_bytes(repo: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=False
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace").strip())
    return proc.stdout


def resolve_commit(repo: Path, ref: str = DEFAULT_REF) -> str:
    return git_bytes(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()


def read_blob(repo: Path, commit: str, path: str) -> bytes:
    return git_bytes(repo, "show", f"{commit}:{path}")


def blob_sha256(repo: Path, commit: str, path: str) -> str:
    return hashlib.sha256(read_blob(repo, commit, path)).hexdigest()


def read_json(repo: Path, commit: str, path: str) -> Any:
    return json.loads(read_blob(repo, commit, path))


def list_paths(repo: Path, commit: str, prefix: str) -> list[str]:
    out = git_bytes(repo, "ls-tree", "-r", "--name-only", commit, "--", prefix)
    return out.decode().splitlines()


def load_checkpoint(repo: Path, commit: str, seed: int) -> dict[str, Any]:
    """Load one frozen two-parameter checkpoint without executing checkpoint code."""
    import torch

    path = f"{TWO_PARAMETER_CHECKPOINT_ROOT}/seed_{seed}/model_state.pt"
    raw = read_blob(repo, commit, path)
    state = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
    state["_path"] = path
    state["_sha256"] = hashlib.sha256(raw).hexdigest()
    return state


def two_parameter_config(repo: Path, commit: str) -> dict[str, Any]:
    """Locked benchmark values with the effective architecture override applied.

    ``configs/locked/multi.yaml`` declares ``hidden_width: 12``; the V5.3 two-parameter
    execution ran ``architecture_width: 6``.  The effective value is the override, and
    the checkpoint state size (2 * (4 * 6 + 1) = 50) confirms it.
    """
    import yaml

    config = copy.deepcopy(yaml.safe_load(read_blob(repo, commit, LOCKED_MULTI_CONFIG)))
    execution = yaml.safe_load(read_blob(repo, commit, TWO_PARAMETER_EXECUTION_CONFIG))
    declared = int(config["network"]["hidden_width"])
    effective = int(execution["architecture_width"])
    config["network"]["hidden_width"] = effective
    config["_declared_width"] = declared
    config["_effective_width"] = effective
    config["_gamma_alpha"] = float(execution["gamma_alpha"])
    return config


def rebuild_points(payload: dict[str, Any]) -> Any:
    """Rebuild the ``MultiPoints`` dataclass stored inside a checkpoint."""
    from saeps.multi import MultiPoints

    return MultiPoints(
        pde_x=payload["pde_x"],
        pde_t=payload["pde_t"],
        data_x=payload["data_x"],
        data_t=payload["data_t"],
        initial_x=payload["initial_x"],
        boundary_t=payload["boundary_t"],
    )


def regenerate_points(config: dict[str, Any], seed: int) -> Any:
    """Regenerate the sampling points from the protocol seed, for adapter validation."""
    from saeps.multi import make_multi_points

    return make_multi_points(config, seed)


def residual(theta: Any, coordinate_log: Any, points: Any, config: dict[str, Any]) -> Any:
    """Weighted stacked residual at log-coordinate ``coordinate_log``."""
    from saeps.multi import multi_residual

    return multi_residual(theta, coordinate_log, points, config)


def sum_objective(theta: Any, coordinate_log: Any, points: Any, config: dict[str, Any]) -> Any:
    """Exported sum objective ``1/2 sum_i r_i^2``."""
    r = residual(theta, coordinate_log, points, config)
    return 0.5 * torch_sum_square(r)


def torch_sum_square(r: Any) -> Any:
    return (r * r).sum()


def residual_count(theta: Any, coordinate_log: Any, points: Any, config: dict[str, Any]) -> int:
    return int(residual(theta, coordinate_log, points, config).numel())


def scalar_posthoc_record(repo: Path, commit: str, benchmark: str, seed: int) -> dict[str, Any]:
    folder = {"Burgers": "burgers", "Allen-Cahn": "allen_cahn"}[benchmark]
    path = f"{SCALAR_POSTHOC_ROOT}/{folder}/seed_{seed}.json"
    record = read_json(repo, commit, path)
    record["_path"] = path
    record["_sha256"] = blob_sha256(repo, commit, path)
    return record


def frozen_environment(repo: Path, commit: str) -> dict[str, Any]:
    return {
        "repository": str(repo),
        "ref": DEFAULT_REF,
        "commit": commit,
        "commit_subject": git_bytes(repo, "log", "-1", "--format=%s", commit)
        .decode()
        .strip(),
        "commit_date": git_bytes(repo, "log", "-1", "--format=%cI", commit)
        .decode()
        .strip(),
    }
