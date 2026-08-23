"""Machine-auditable V5.0 governance without scientific execution."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Iterable

import torch

from saeps.config import load_config


PARENT_PROTOCOL_SHA256 = "6abb0864cddb40fd63f29a24d97004c539727744d35b2ac9821888d0a90d0f12"
RECONSTRUCTED_ROLE = "V5_RECONSTRUCTED_ENGINEERING_CHECKPOINT"
NEW_CHECKPOINT_ROLE = "V5_NEW_SCIENTIFIC_CHECKPOINT"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(
    repo_root: Path,
    relative_root: str,
    *,
    excluded_prefixes: Iterable[str] = (),
) -> tuple[int, str]:
    root = repo_root / relative_root
    prefixes = tuple(prefix.rstrip("/") + "/" for prefix in excluded_prefixes)
    rows: list[str] = []
    if root.is_dir():
        for path in sorted(
            (candidate for candidate in root.rglob("*") if candidate.is_file()),
            key=lambda candidate: candidate.relative_to(repo_root).as_posix(),
        ):
            relative = path.relative_to(repo_root).as_posix()
            if any(relative.startswith(prefix) for prefix in prefixes):
                continue
            rows.append(f"{relative}\t{sha256_file(path)}\n")
    return len(rows), hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def validate_historical_inventory(repo_root: Path, inventory: dict[str, Any]) -> None:
    if inventory.get("historical_excluded_prefix") != "outputs/runs/v5":
        raise ValueError("historical inventory must exclude only the V5 output prefix")
    for row in inventory["tree_digests"]:
        observed_count, observed_digest = tree_digest(
            repo_root,
            row["path"],
            excluded_prefixes=["outputs/runs/v5"],
        )
        if observed_count != row["file_count"] or observed_digest != row["sha256"]:
            raise ValueError(f"historical tree changed: {row['path']}")
    for relative in inventory["required_absent_paths"]:
        if (repo_root / relative).exists():
            raise ValueError(f"protected inactive cohort unexpectedly exists: {relative}")


def validate_seed_registry(registry: dict[str, Any]) -> None:
    expected = {
        "profile_heldout": list(range(200, 205)),
        "two_parameter_development": list(range(210, 213)),
        "two_parameter_heldout": list(range(213, 215)),
        "two_parameter_confirmation": list(range(215, 225)),
    }
    if registry.get("replacement_forbidden") is not True:
        raise ValueError("V5 seed replacement must be forbidden")
    scientific = registry["v5_scientific"]
    for name, seeds in expected.items():
        if scientific.get(name) != seeds:
            raise ValueError(f"incorrect V5 seed cohort: {name}")
    reconstruction = registry["reconstruction"]
    if reconstruction["burgers"]["seeds"] != [45, 46, 47]:
        raise ValueError("Burgers reconstruction seeds changed")
    if reconstruction["allen_cahn"]["seeds"] != [70, 71, 72, 73, 74]:
        raise ValueError("Allen reconstruction seeds changed")
    if reconstruction["scalability_base"]["seeds"] != [120]:
        raise ValueError("scalability base source changed")
    all_scientific = [seed for seeds in scientific.values() for seed in seeds]
    protected = [
        seed
        for seeds in registry["historical_protected"].values()
        for seed in seeds
    ]
    if len(all_scientific) != len(set(all_scientific)):
        raise ValueError("V5 scientific seed cohorts overlap")
    if set(all_scientific) & set(protected):
        raise ValueError("V5 scientific seeds overlap protected history")
    if registry["planned_denominators"] != {
        "profile_heldout": 5,
        "two_parameter_confirmation": 10,
    }:
        raise ValueError("planned denominators changed")


def ensure_v5_write_path(repo_root: Path, destination: Path, allowlist: list[str]) -> None:
    root = repo_root.resolve()
    target = destination.resolve()
    allowed = [(root / relative).resolve() for relative in allowlist]
    if not any(target == base or target.is_relative_to(base) for base in allowed):
        raise ValueError(f"V5 write path is outside the allowlist: {destination}")
    historical = (root / "outputs/runs").resolve()
    v5_outputs = (root / "outputs/runs/v5").resolve()
    if target.is_relative_to(historical) and not target.is_relative_to(v5_outputs):
        raise ValueError("V5 must never write into historical output paths")


def confirmation_prior_outputs(repo_root: Path, seeds: Iterable[int]) -> list[str]:
    output_root = repo_root / "outputs/runs/v5"
    if not output_root.is_dir():
        return []
    names = {f"seed_{seed}" for seed in seeds}
    return sorted(
        path.relative_to(repo_root).as_posix()
        for path in output_root.rglob("*")
        if path.name in names or path.stem in names
    )


def adjudicate_profile_cohort(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) != 5:
        raise ValueError("profile planned denominator must be exactly 5")
    identities = [int(row["seed"]) for row in rows]
    if sorted(identities) != list(range(200, 205)) or len(set(identities)) != 5:
        raise ValueError("profile rows must be the unreplaced planned seeds 200--204")
    evaluable_count = sum(bool(row["profile_evaluable"]) for row in rows)
    valid_count = sum(bool(row["profile_valid"]) for row in rows)
    if any(bool(row["profile_valid"]) and not bool(row["profile_evaluable"]) for row in rows):
        raise ValueError("PROFILE_VALID requires PROFILE_EVALUABLE")
    if evaluable_count < 4:
        status = "INCONCLUSIVE"
    elif valid_count >= 4:
        status = "SUPPORTED"
    else:
        status = "NOT_SUPPORTED"
    return {
        "planned_denominator": 5,
        "n_evaluable": evaluable_count,
        "n_profile_valid": valid_count,
        "scientific_status": status,
    }


def relative_eigengap(eigenvalues: Iterable[float]) -> float:
    values = sorted(float(value) for value in eigenvalues)
    if len(values) != 2 or not all(math.isfinite(value) for value in values):
        raise ValueError("V5 two-parameter eigengap requires two finite eigenvalues")
    return abs(values[1] - values[0]) / max(abs(values[0]), abs(values[1]), 1.0e-30)


def validate_checkpoint_manifest(repo_root: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = _load_json(manifest_path)
    schema = _load_json(repo_root / "configs/v5/schemas/checkpoint_manifest.schema.json")
    missing = [name for name in schema["required"] if name not in manifest]
    if missing:
        raise ValueError(f"checkpoint manifest missing fields: {missing}")
    if manifest["artifact_role"] not in {RECONSTRUCTED_ROLE, NEW_CHECKPOINT_ROLE}:
        raise ValueError("invalid V5 checkpoint artifact role")
    registry = load_config(repo_root / "configs/v5/seed_registry.yaml")
    source_seed = int(manifest["source_seed"])
    if manifest["artifact_role"] == RECONSTRUCTED_ROLE:
        expected_configs = {
            int(seed): group["source_config"]
            for group in registry["reconstruction"].values()
            for seed in group["seeds"]
        }
        if source_seed not in expected_configs:
            raise ValueError("unregistered reconstruction source seed")
        expected_config = repo_root / expected_configs[source_seed]
        if manifest["source_config_hash"] != sha256_file(expected_config):
            raise ValueError("reconstruction source config hash mismatch")
    else:
        scientific_seeds = {
            int(seed)
            for seeds in registry["v5_scientific"].values()
            for seed in seeds
        }
        if source_seed not in scientific_seeds:
            raise ValueError("unregistered new scientific checkpoint seed")
    if not isinstance(manifest["source_protocol"], str) or not manifest["source_protocol"]:
        raise ValueError("source protocol is missing")
    commit = manifest["reconstruction_commit"]
    if not isinstance(commit, str) or len(commit) != 40 or any(
        character not in "0123456789abcdef" for character in commit.lower()
    ):
        raise ValueError("reconstruction commit is invalid")
    artifact = (repo_root / manifest["model_state_path"]).resolve()
    checkpoint_root = (repo_root / "outputs/runs/v5/checkpoints").resolve()
    if not artifact.is_relative_to(checkpoint_root):
        raise ValueError("checkpoint artifact is outside V5 checkpoint root")
    if not artifact.is_file():
        raise ValueError("reloadable model artifact is missing")
    observed_hash = sha256_file(artifact)
    if observed_hash != manifest["model_state_hash"]:
        raise ValueError("model state hash mismatch")
    payload = torch.load(artifact, map_location="cpu", weights_only=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("theta"), torch.Tensor):
        raise ValueError("model state payload must contain a theta tensor")
    theta = payload["theta"]
    if theta.numel() == 0 or not bool(torch.all(torch.isfinite(theta)).item()):
        raise ValueError("model theta must be nonempty and finite")
    diagnostic_hash = manifest["diagnostic_set_hash"]
    if (
        not isinstance(diagnostic_hash, str)
        or len(diagnostic_hash) != 64
        or any(character not in "0123456789abcdef" for character in diagnostic_hash.lower())
    ):
        raise ValueError("diagnostic set hash is invalid")
    if not isinstance(manifest["environment"], dict) or "packages" not in manifest["environment"]:
        raise ValueError("checkpoint environment provenance is incomplete")
    return manifest


def validate_checkpoint_inventory(repo_root: Path) -> int:
    checkpoint_root = repo_root / "outputs/runs/v5/checkpoints"
    if not checkpoint_root.exists():
        return 0
    manifests = sorted(checkpoint_root.rglob("checkpoint_manifest.json"))
    nonempty_directories = {
        path.parent
        for path in checkpoint_root.rglob("*")
        if path.is_file()
    }
    manifest_directories = {path.parent for path in manifests}
    if nonempty_directories - manifest_directories:
        raise ValueError("V5 checkpoint directory has files but no checkpoint manifest")
    reconstructed_sources: list[int] = []
    for manifest in manifests:
        record = validate_checkpoint_manifest(repo_root, manifest)
        if record["artifact_role"] == RECONSTRUCTED_ROLE:
            reconstructed_sources.append(int(record["source_seed"]))
    if len(reconstructed_sources) != len(set(reconstructed_sources)):
        raise ValueError("a reconstruction source seed has more than one artifact")
    return len(manifests)


def validate_aggregate_lineage(repo_root: Path, aggregate: dict[str, Any]) -> None:
    schema = _load_json(repo_root / "configs/v5/schemas/aggregate.schema.json")
    missing = [name for name in schema["required"] if name not in aggregate]
    if missing:
        raise ValueError(f"aggregate missing fields: {missing}")
    for source in aggregate["source_records"]:
        path = (repo_root / source["path"]).resolve()
        raw_root = (repo_root / "outputs/runs/v5").resolve()
        if not path.is_relative_to(raw_root) or not path.is_file():
            raise ValueError("aggregate source must be a V5 raw record")
        if sha256_file(path) != source["sha256"]:
            raise ValueError("aggregate source hash mismatch")


def _check(condition: bool, detail: str) -> dict[str, str]:
    return {"status": "PASS" if condition else "FAIL", "detail": detail}


def validate_v5_governance(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    checks: dict[str, dict[str, Any]] = {}
    governance = load_config(root / "configs/v5/governance.yaml")
    registry = load_config(root / "configs/v5/seed_registry.yaml")
    validate_seed_registry(registry)
    checks["seed_registry"] = _check(True, "all V5 and protected cohorts are exact and disjoint")

    inventory = _load_json(root / "configs/v5/HISTORICAL_HASH_INVENTORY.json")
    validate_historical_inventory(root, inventory)
    checks["historical_immutability"] = _check(True, "all pre-V5 run bytes match the frozen tree digest")

    for relative in governance["output_allowlist"]:
        ensure_v5_write_path(root, root / relative / "probe", governance["output_allowlist"])
    try:
        ensure_v5_write_path(root, root / "outputs/runs/v4_2_corrected_confirmation/probe", governance["output_allowlist"])
    except ValueError:
        historical_rejected = True
    else:
        historical_rejected = False
    checks["output_allowlist"] = _check(historical_rejected, "V5 paths accepted and historical writes rejected")

    confirmation = registry["v5_scientific"]["two_parameter_confirmation"]
    existing_confirmation = confirmation_prior_outputs(root, confirmation)
    checks["confirmation_prior_output_guard"] = _check(
        not existing_confirmation,
        f"prior confirmation paths: {existing_confirmation}",
    )

    config_paths = [
        "configs/v5/finite_gamma_audit.yaml",
        "configs/v5/profile_bridge.yaml",
        "configs/v5/two_parameter.yaml",
        "configs/v5/residual_scalability.yaml",
    ]
    phase_configs = [load_config(root / path) for path in config_paths]
    checks["scientific_execution_closed"] = _check(
        governance["scientific_execution_authorized"] is False
        and governance["confirmation_authorized"] is False
        and all(config["execution_authorized"] is False for config in phase_configs)
        and phase_configs[2]["confirmation_authorized"] is False,
        "all V5 scientific execution flags are false",
    )

    graph = _load_json(root / "configs/v5/semantic_gate_graph.json")
    checks["nonbinding_eigenvectors"] = _check(
        graph["generalized_eigenvectors_binding"] is False
        and phase_configs[2]["generalized_geometry"]["eigengap_threshold"] is None
        and phase_configs[2]["generalized_geometry"]["eigenvector_orientation_enters_adjudication"] is False,
        "eigenvectors and eigengap are secondary and non-binding",
    )

    profile = phase_configs[1]
    profile_semantics = (
        profile["planned_denominator"] == 5
        and profile["adjudication"]["minimum_evaluable_for_scientific_decision"] == 4
        and profile["adjudication"]["minimum_profile_valid_for_supported"] == 4
        and profile["rescue_cohort_authorized"] is False
    )
    checks["profile_semantics"] = _check(profile_semantics, "two-level 4-of-5 adjudication is frozen")

    reconstructed = sum(
        len(value["seeds"])
        for value in registry["reconstruction"].values()
    )
    checks["compute_ceiling"] = _check(
        reconstructed == 9
        and governance["reconstruction_training_ceiling"] == 9
        and governance["total_new_or_reconstructed_training_ceiling"] == 29,
        "9 reconstruction and 29 total training ceilings are frozen",
    )

    checkpoint_count = validate_checkpoint_inventory(root)
    checks["checkpoint_persistence"] = _check(
        checkpoint_count == 0,
        "checkpoint validator active; zero artifacts exist before scientific execution",
    )

    v5_output_root = root / "outputs/runs/v5"
    scientific_files = sorted(
        path.relative_to(root).as_posix()
        for path in v5_output_root.rglob("*")
        if path.is_file()
    ) if v5_output_root.exists() else []
    checks["no_v5_scientific_output"] = _check(
        not scientific_files,
        f"V5 scientific files: {scientific_files}",
    )

    freeze = _load_json(root / "configs/v5/V5_GOVERNANCE_FREEZE.json")
    parent = subprocess.run(
        [
            "git",
            "show",
            f"{freeze['freeze_parent_commit']}:V5_JCP_MINIMAL_PROTOCOL.md",
        ],
        cwd=root,
        capture_output=True,
        check=False,
    )
    parent_hash = hashlib.sha256(parent.stdout).hexdigest() if parent.returncode == 0 else None
    amendment_hash = sha256_file(root / "docs/v5/V5_PROTOCOL_AMENDMENT_001.md")
    composite_bytes = (
        f"parent_sha256={parent_hash}\n"
        f"amendment_sha256={amendment_hash}\n"
        "precedence=amendment_over_parent_on_conflict\n"
    ).encode("utf-8")
    composite_hash = hashlib.sha256(composite_bytes).hexdigest()
    checks["effective_protocol"] = _check(
        parent_hash == freeze["parent_protocol_original_sha256"] == PARENT_PROTOCOL_SHA256
        and amendment_hash == freeze["amendment_sha256"]
        and composite_hash == freeze["effective_protocol_composite_sha256"],
        "parent, amendment, precedence and composite hashes match",
    )
    frozen_rows = []
    for relative, expected in freeze["file_sha256"].items():
        actual = sha256_file(root / relative)
        frozen_rows.append({"path": relative, "expected": expected, "actual": actual})
    checks["frozen_files"] = _check(
        all(row["expected"] == row["actual"] for row in frozen_rows),
        f"{len(frozen_rows)} governance files match frozen hashes",
    )
    checks["frozen_files"]["files"] = frozen_rows

    status = "PASSED" if all(row["status"] == "PASS" for row in checks.values()) else "FAILED"
    return {
        "schema_version": 1,
        "phase": "V5_0_GOVERNANCE",
        "status": status,
        "scientific_execution_started": False,
        "ready_for_v5_execution": status == "PASSED",
        "checks": checks,
    }
