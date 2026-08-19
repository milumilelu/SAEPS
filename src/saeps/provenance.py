"""Run identifiers and environment provenance."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch


def _git_value(repo_root: Path, *args: str) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def git_provenance(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    commit = _git_value(root, "rev-parse", "HEAD")
    branch = _git_value(root, "branch", "--show-current")
    status = _git_value(root, "status", "--porcelain")
    return {
        "git_commit": commit,
        "git_branch": branch,
        "git_dirty": bool(status),
        "git_status_porcelain": status or "",
    }


def package_versions(names: tuple[str, ...] = ("numpy", "PyYAML", "torch")) -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "NOT_INSTALLED"
    return versions


def environment_provenance(repo_root: str | Path, dtype: str, device: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "dtype": dtype,
        "device": device,
        "torch_cuda_available": torch.cuda.is_available(),
        "packages": package_versions(),
    }
    payload.update(git_provenance(repo_root))
    return payload


def make_run_id(phase: str, seed: int, config_digest: str, timestamp: str) -> str:
    identity = json.dumps(
        {"phase": phase, "seed": seed, "config_hash": config_digest, "timestamp": timestamp},
        sort_keys=True,
        separators=(",", ":"),
    )
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    compact_time = timestamp.replace("-", "").replace(":", "").replace("+00:00", "Z")
    return f"{phase.lower()}-s{seed}-{compact_time}-{suffix}"

