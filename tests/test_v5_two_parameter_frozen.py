from pathlib import Path

import torch

from saeps.config import load_config
from saeps.v5.two_parameter_frozen import (
    CONFIRMATION_SEEDS,
    HELDOUT_SEEDS,
    _generalized_geometry,
    _primary_metrics,
)


ROOT = Path(__file__).resolve().parents[1]


def test_v5_two_parameter_frozen_seed_registry_and_primary_rule() -> None:
    config = load_config(ROOT / "configs/v5/two_parameter_frozen_execution.yaml")
    assert HELDOUT_SEEDS == [213, 214]
    assert CONFIRMATION_SEEDS == list(range(215, 225))
    assert config["confirmation_gate"]["minimum_valid"] == 9
    assert config["confirmation_gate"]["minimum_planned_wins"] == 9
    assert config["primary_metric"]["tau_relative"] == 1.0e-10


def test_whitened_primary_and_nonbinding_generalized_geometry_on_actual_matrices() -> None:
    raw = torch.tensor([[4.0, 1.0], [1.0, 3.0]], dtype=torch.float64)
    fse = torch.tensor([[1.5, 0.2], [0.2, 1.0]], dtype=torch.float64)
    exact = torch.tensor([[1.4, 0.25], [0.25, 0.9]], dtype=torch.float64)
    specification = load_config(ROOT / "configs/v5/two_parameter_frozen_execution.yaml")
    primary = _primary_metrics(raw, fse, exact, specification["primary_metric"])
    geometry = _generalized_geometry(fse, exact, torch.tensor(primary["B"], dtype=torch.float64))
    assert primary["D2"] > 0.0
    assert geometry["eigengap_threshold"] is None
    assert geometry["orientation_enters_adjudication"] is False
    assert len(geometry["directional_curvatures"]) == 2
