from pathlib import Path

import pytest

from saeps.v48.pipeline import run_scalability_checkpoint


def test_scalability_rejects_unregistered_checkpoint() -> None:
    with pytest.raises(ValueError):
        run_scalability_checkpoint(Path(__file__).resolve().parents[1], 119)
