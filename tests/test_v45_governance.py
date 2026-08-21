import hashlib
from pathlib import Path

from saeps.config import load_config


ROOT = Path(__file__).resolve().parents[1]


def test_v45_seed_isolation_and_inactive_confirmation() -> None:
    config = load_config(ROOT / "configs/v4_5/controlled_mechanism_development.yaml")
    assert config["engineering_seeds"] == [85, 86, 87]
    assert config["heldout_development_seeds"] == [88, 89]
    assert config["inactive_confirmation_seeds"] == list(range(90, 100))
    assert config["confirmation_authorized"] is False
    assert not set(config["engineering_seeds"] + config["heldout_development_seeds"]) & set(
        config["inactive_confirmation_seeds"]
    )


def test_v45_protected_source_hashes_and_forbidden_selection_metrics() -> None:
    config = load_config(ROOT / "configs/v4_5/controlled_mechanism_development.yaml")
    for item in config["protected_sources"].values():
        actual = hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
        assert actual == item["sha256"]
    assert config["center_engineering"]["selection_forbidden_metrics"] == [
        "eta",
        "monotonicity",
        "spearman",
        "figure_appearance",
    ]
    assert config["future_confirmation_rule"]["all_centers_must_be_valid"] is True
