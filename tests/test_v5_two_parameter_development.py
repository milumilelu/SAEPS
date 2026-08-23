from pathlib import Path

from saeps.config import load_config
from saeps.v5.two_parameter_development import SEEDS


ROOT = Path(__file__).resolve().parents[1]


def test_v5_two_parameter_development_is_center_only_selection() -> None:
    config = load_config(ROOT / "configs/v5/two_parameter_development_execution.yaml")
    assert SEEDS == [210, 211, 212]
    assert config["development_gate"]["required_binding_valid"] == 3
    assert config["scientific_comparison_computed"] is False
    assert set(config["selection_forbidden_metrics"]) >= {
        "D2", "E_raw2", "E_SAEPS2", "favorable_eigenvalues", "eigenvectors"
    }
    assert config["architecture_width"] == 6
