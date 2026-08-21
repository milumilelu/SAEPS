from pathlib import Path

import pytest

from saeps.v47.pipeline import run_v46_engineering_seed, run_v46_heldout_seed


def test_v46_rejects_confirmation_seed() -> None:
    with pytest.raises(ValueError, match="not authorized"):
        run_v46_engineering_seed(Path(__file__).resolve().parents[1], 105)


def test_v46_heldout_never_executes_confirmation_seed() -> None:
    with pytest.raises((RuntimeError, ValueError)):
        run_v46_heldout_seed(Path(__file__).resolve().parents[1], 105)
