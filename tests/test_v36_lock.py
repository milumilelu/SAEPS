from __future__ import annotations

import math
from pathlib import Path

from saeps.config import load_config


ROOT = Path(__file__).resolve().parents[1]


def test_v36_primary_threshold_has_registered_exact_tail() -> None:
    specification = load_config(ROOT / "configs/v3_6/locked_scalar_confirmation.yaml")
    primary = specification["primary"]
    n = primary["planned_denominator"]
    required = primary["planned_seed_wins_required"]

    tail = sum(math.comb(n, value) for value in range(required, n + 1)) / 2**n
    preceding = sum(math.comb(n, value) for value in range(required - 1, n + 1)) / 2**n

    assert n == 15
    assert required == 12
    assert tail <= primary["alpha"]
    assert preceding > primary["alpha"]


def test_v36_is_locked_but_not_authorized() -> None:
    specification = load_config(ROOT / "configs/v3_6/locked_scalar_confirmation.yaml")
    assert specification["protocol_locked"] is True
    assert specification["execution_authorized"] is False
    assert specification["planned_seeds"] == list(range(30, 45))
