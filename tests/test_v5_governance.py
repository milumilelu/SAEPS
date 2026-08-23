import hashlib
import json
from pathlib import Path

import pytest
import torch

from saeps.config import load_config
from saeps.v5.governance import (
    RECONSTRUCTED_ROLE,
    adjudicate_profile_cohort,
    confirmation_prior_outputs,
    ensure_v5_write_path,
    relative_eigengap,
    validate_checkpoint_manifest,
    validate_aggregate_lineage,
    validate_historical_inventory,
    validate_seed_registry,
    validate_v5_governance,
)


ROOT = Path(__file__).resolve().parents[1]


def _profile_rows(evaluable: int, valid: int) -> list[dict[str, object]]:
    return [
        {
            "seed": seed,
            "profile_evaluable": index < evaluable,
            "profile_valid": index < valid,
        }
        for index, seed in enumerate(range(200, 205))
    ]


@pytest.mark.parametrize(
    ("evaluable", "valid", "expected"),
    [(3, 3, "INCONCLUSIVE"), (4, 4, "SUPPORTED"), (5, 4, "SUPPORTED"), (4, 3, "NOT_SUPPORTED"), (5, 0, "NOT_SUPPORTED")],
)
def test_profile_two_level_adjudication(evaluable: int, valid: int, expected: str) -> None:
    result = adjudicate_profile_cohort(_profile_rows(evaluable, valid))
    assert result["planned_denominator"] == 5
    assert result["scientific_status"] == expected


def test_profile_valid_requires_evaluable_and_planned_cohort() -> None:
    rows = _profile_rows(0, 0)
    rows[0]["profile_valid"] = True
    with pytest.raises(ValueError, match="PROFILE_VALID"):
        adjudicate_profile_cohort(rows)
    with pytest.raises(ValueError, match="denominator"):
        adjudicate_profile_cohort(rows[:-1])


def test_relative_eigengap_is_dimensionless_and_nonbinding() -> None:
    assert relative_eigengap([1.0, 3.0]) == pytest.approx(2.0 / 3.0)
    assert relative_eigengap([10.0, 30.0]) == pytest.approx(2.0 / 3.0)
    config = load_config(ROOT / "configs/v5/two_parameter.yaml")
    assert config["generalized_geometry"]["eigengap_threshold"] is None
    assert config["generalized_geometry"]["eigenvector_orientation_enters_adjudication"] is False


def test_seed_registry_and_historical_inventory_are_exact() -> None:
    registry = load_config(ROOT / "configs/v5/seed_registry.yaml")
    validate_seed_registry(registry)
    inventory = json.loads(
        (ROOT / "configs/v5/HISTORICAL_HASH_INVENTORY.json").read_text(encoding="utf-8")
    )
    validate_historical_inventory(ROOT, inventory)


def test_output_allowlist_rejects_historical_paths() -> None:
    allowlist = load_config(ROOT / "configs/v5/governance.yaml")["output_allowlist"]
    ensure_v5_write_path(ROOT, ROOT / "outputs/runs/v5/probe", allowlist)
    with pytest.raises(ValueError):
        ensure_v5_write_path(ROOT, ROOT / "outputs/runs/v4_2_corrected_confirmation/probe", allowlist)


def test_confirmation_prior_output_guard(tmp_path: Path) -> None:
    assert confirmation_prior_outputs(tmp_path, range(215, 225)) == []
    prior = tmp_path / "outputs/runs/v5/two_parameter/confirmation/seed_215"
    prior.mkdir(parents=True)
    assert confirmation_prior_outputs(tmp_path, range(215, 225)) == [
        "outputs/runs/v5/two_parameter/confirmation/seed_215"
    ]


def test_checkpoint_manifest_requires_reloadable_hashed_state(tmp_path: Path) -> None:
    schema_source = ROOT / "configs/v5/schemas/checkpoint_manifest.schema.json"
    schema_target = tmp_path / "configs/v5/schemas/checkpoint_manifest.schema.json"
    schema_target.parent.mkdir(parents=True)
    schema_target.write_bytes(schema_source.read_bytes())
    registry_source = ROOT / "configs/v5/seed_registry.yaml"
    registry_target = tmp_path / "configs/v5/seed_registry.yaml"
    registry_target.write_bytes(registry_source.read_bytes())
    source_config = tmp_path / "configs/v4_1/post_confirmation_development.yaml"
    source_config.parent.mkdir(parents=True)
    source_config.write_text("schema_version: 1\n", encoding="utf-8")
    artifact = tmp_path / "outputs/runs/v5/checkpoints/burgers/seed_45/model_state.pt"
    artifact.parent.mkdir(parents=True)
    torch.save({"theta": torch.tensor([1.0], dtype=torch.float64), "source_seed": 45}, artifact)
    manifest = {
        "schema_version": 1,
        "artifact_role": RECONSTRUCTED_ROLE,
        "source_protocol": "configs/v4_1/post_confirmation_development.yaml",
        "source_config_hash": hashlib.sha256(source_config.read_bytes()).hexdigest(),
        "source_seed": 45,
        "reconstruction_commit": "b" * 40,
        "model_state_path": artifact.relative_to(tmp_path).as_posix(),
        "model_state_hash": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "diagnostic_set_hash": "c" * 64,
        "dtype": "float64",
        "device": "cpu",
        "environment": {"packages": {"torch": torch.__version__}},
        "status": "PASS",
    }
    manifest_path = artifact.with_name("checkpoint_manifest.json")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    validate_checkpoint_manifest(tmp_path, manifest_path)
    artifact.unlink()
    with pytest.raises(ValueError, match="missing"):
        validate_checkpoint_manifest(tmp_path, manifest_path)


def test_raw_to_aggregate_lineage_rejects_hash_mismatch(tmp_path: Path) -> None:
    schema_source = ROOT / "configs/v5/schemas/aggregate.schema.json"
    schema_target = tmp_path / "configs/v5/schemas/aggregate.schema.json"
    schema_target.parent.mkdir(parents=True)
    schema_target.write_bytes(schema_source.read_bytes())
    raw = tmp_path / "outputs/runs/v5/profile/seed_200/result.json"
    raw.parent.mkdir(parents=True)
    raw.write_text('{"status":"PASS"}\n', encoding="utf-8")
    aggregate = {
        "schema_version": 1,
        "phase": "V5_2_PROFILE_BRIDGE",
        "planned_denominator": 5,
        "source_records": [
            {
                "path": raw.relative_to(tmp_path).as_posix(),
                "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
                "planned_identity": 200,
                "terminal_status": "PASS",
            }
        ],
        "status": "SUPPORTED",
    }
    validate_aggregate_lineage(tmp_path, aggregate)
    aggregate["source_records"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash"):
        validate_aggregate_lineage(tmp_path, aggregate)


def test_v5_governance_freeze_passes_without_scientific_output() -> None:
    result = validate_v5_governance(ROOT)
    assert result["status"] == "PASSED"
    assert result["scientific_execution_started"] is False
    assert result["ready_for_v5_execution"] is True
