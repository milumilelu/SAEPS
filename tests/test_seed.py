import random

import numpy as np
import torch

from saeps.seed import set_deterministic_seed


def _draw() -> tuple[float, np.ndarray, torch.Tensor]:
    return random.random(), np.random.standard_normal(4), torch.randn(4, dtype=torch.float64)


def test_seed_reproduces_python_numpy_and_torch() -> None:
    set_deterministic_seed(123)
    first = _draw()
    set_deterministic_seed(123)
    second = _draw()
    assert first[0] == second[0]
    np.testing.assert_array_equal(first[1], second[1])
    torch.testing.assert_close(first[2], second[2], rtol=0.0, atol=0.0)

