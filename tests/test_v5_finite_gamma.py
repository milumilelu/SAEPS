from pathlib import Path

from saeps.config import load_config
from saeps.v5.finite_gamma import ALPHAS, CHECKPOINTS


ROOT = Path(__file__).resolve().parents[1]


def test_v5_finite_gamma_registry_matches_frozen_protocol() -> None:
    config = load_config(ROOT / "configs/v5/finite_gamma_audit.yaml")
    assert [float(value) for value in config["alpha_values"]] == ALPHAS
    assert CHECKPOINTS == {"burgers": [45, 46, 47], "allen_cahn": [70, 71, 72]}
    assert config["scientific_win_gate"] == "none_descriptive_only"
    assert config["nominal_gamma_recalibration_forbidden"] is True


def test_v5_execution_authorization_does_not_change_thresholds_or_seeds() -> None:
    import json

    authorization = json.loads(
        (ROOT / "configs/v5/V5_EXECUTION_AUTHORIZATION.json").read_text(encoding="utf-8")
    )
    assert authorization["authorized"] is True
    assert authorization["threshold_changes_authorized"] is False
    assert authorization["seed_changes_authorized"] is False
