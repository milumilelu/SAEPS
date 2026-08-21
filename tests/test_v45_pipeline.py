from pathlib import Path

import pytest

from saeps.v45.pipeline import run_v45_engineering_seed, run_v45_heldout_seed


ROOT = Path(__file__).resolve().parents[1]


def test_v45_runner_rejects_confirmation_seed() -> None:
    with pytest.raises(ValueError, match="not authorized"):
        run_v45_engineering_seed(ROOT, 90)


def test_v45_heldout_requires_freeze_or_rejects_confirmation_seed() -> None:
    with pytest.raises((RuntimeError, ValueError)):
        run_v45_heldout_seed(ROOT, 90)
