from pathlib import Path

from saeps.config import load_config


ROOT = Path(__file__).resolve().parents[1]


def test_v46_seed_isolation_and_matrix_primary() -> None:
    config = load_config(ROOT / "configs/v4_6/two_parameter_development.yaml")
    assert config["engineering_seeds"] == [100, 101, 102]
    assert config["heldout_development_seeds"] == [115, 116]
    assert config["inactive_confirmation_seeds"] == list(range(105, 115))
    assert config["confirmation_authorized"] is False
    assert "D" in config["selection_forbidden_metrics"]
    assert config["future_confirmation"]["planned_strict_wins_required"] == 8
