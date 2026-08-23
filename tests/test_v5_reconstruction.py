import hashlib
import json
from pathlib import Path

import pytest

from saeps.config import load_config
from saeps.v5.reconstruction import reconstruct_all_checkpoints, reconstruct_checkpoint


ROOT = Path(__file__).resolve().parents[1]


def test_reconstruction_registry_is_fixed_and_capped() -> None:
    config = load_config(ROOT / "configs/v5/reconstruction.yaml")
    assert config["sources"]["burgers"]["seeds"] == [45, 46, 47]
    assert config["sources"]["allen_cahn"]["seeds"] == [70, 71, 72, 73, 74]
    assert config["sources"]["scalability_base"]["seeds"] == [120]
    assert sum(len(group["seeds"]) for group in config["sources"].values()) == 9
    assert config["maximum_attempts_per_source_seed"] == 1
    assert config["replacement_forbidden"] is True


def test_reconstruction_executable_freeze_hashes() -> None:
    freeze = json.loads(
        (ROOT / "configs/v5/RECONSTRUCTION_EXECUTABLE_FREEZE.json").read_text(encoding="utf-8")
    )
    assert freeze["execution_authorized"] is True
    assert freeze["all_sources_maximum_attempts"] == 1
    for relative, expected in freeze["file_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_reconstruction_rejects_unregistered_seed_before_training() -> None:
    with pytest.raises(ValueError, match="outside"):
        reconstruct_checkpoint(ROOT, "burgers", 48)


def test_batch_reconstruction_api_is_available() -> None:
    assert callable(reconstruct_all_checkpoints)
