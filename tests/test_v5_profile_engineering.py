from pathlib import Path

from saeps.config import load_config
from saeps.v5.profile_engineering import CANDIDATE_SEEDS, VALIDATION_SEEDS


ROOT = Path(__file__).resolve().parents[1]


def test_v5_profile_engineering_registry_and_forbidden_metrics() -> None:
    config = load_config(ROOT / "configs/v5/profile_engineering_execution.yaml")
    assert CANDIDATE_SEEDS == [70, 71, 72]
    assert VALIDATION_SEEDS == [73, 74]
    assert config["h_values"] == [0.04, 0.02, 0.01, 0.005]
    assert config["independent_start_from_common_theta0"] is True
    assert config["continuation_forbidden"] is True
    assert set(config["selection_rule"]["forbidden_metrics"]) >= {
        "D", "E_raw", "E_SAEPS", "eta", "F_raw", "F_se_GN"
    }


def test_v5_profile_candidate_split_never_reads_confirmation() -> None:
    assert set(CANDIDATE_SEEDS + VALIDATION_SEEDS) == set(range(70, 75))
    assert not set(range(75, 85)) & set(CANDIDATE_SEEDS + VALIDATION_SEEDS)
