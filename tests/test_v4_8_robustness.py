from pathlib import Path

import pytest

from saeps.config import load_config
from saeps.v49.pipeline import run_robustness_seed


ROOT = Path(__file__).resolve().parents[1]


def test_locked_v4_8_design_is_paired_and_complete() -> None:
    config = load_config(ROOT / "configs/v4_8/robustness.yaml")
    assert config["noise_sparsity"]["seeds"] == [130, 131, 132, 133, 134]
    assert config["architecture"]["seeds"] == [135, 136, 137, 138, 139]
    assert len(config["noise_sparsity"]["noise_levels"]) * len(config["noise_sparsity"]["observation_fractions"]) == 9
    assert len(config["noise_sparsity"]["exact_anchor_cells"]) == 3
    assert config["architecture"]["widths"] == [8, 16, 32]
    assert config["reporting"]["scientific_gate"] == "DESCRIPTIVE_ONLY"


def test_v4_8_rejects_unregistered_seed_before_training(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside the locked"):
        run_robustness_seed(ROOT, "noise_sparsity", 129)
