from pathlib import Path

from saeps.config import load_config
from saeps.v5.profile_heldout import SEEDS


ROOT = Path(__file__).resolve().parents[1]


def test_v5_profile_heldout_registry_and_adjudication_are_frozen() -> None:
    config = load_config(ROOT / "configs/v5/profile_bridge.yaml")
    assert SEEDS == [200, 201, 202, 203, 204]
    assert config["planned_denominator"] == 5
    assert config["replacement_forbidden"] is True
    assert config["rescue_cohort_authorized"] is False
    assert config["profile_valid_requires"]["finest_profile_exact_relative_error_max"] == 0.10
    assert config["profile_valid_requires"]["last_two_curvature_relative_change_max"] == 0.05
