from pathlib import Path

from saeps.config import load_config


ROOT = Path(__file__).resolve().parents[1]


def test_cost_benchmark_uses_development_not_confirmation_seeds() -> None:
    config = load_config(ROOT / "configs/cost.yaml")
    assert config["split"] == "cost_only_development"
    assert config["seeds"] == [0, 1, 2]
    assert not set(config["seeds"]).intersection(range(10, 20))
