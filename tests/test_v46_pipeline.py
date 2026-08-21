from pathlib import Path

import pytest

from saeps.v47.pipeline import run_v46_engineering_seed


def test_v46_rejects_confirmation_seed() -> None:
    with pytest.raises(ValueError, match="engineering seeds"):
        run_v46_engineering_seed(Path(__file__).resolve().parents[1], 105)
