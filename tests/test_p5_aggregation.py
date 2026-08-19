from __future__ import annotations

from saeps.p5_confirmation import _bootstrap_interval, _classification


def test_locked_paired_classification_uses_planned_denominator() -> None:
    assert _classification(10, 10, 9, 0.2, (0.01, 0.4)) == "STRONGLY_SUPPORTED"
    assert _classification(10, 10, 9, 0.2, (-0.01, 0.4)) == "SUPPORTED_WITH_UNCERTAINTY"
    assert _classification(10, 8, 8, 0.2, (0.01, 0.4)) == "PARTIALLY_SUPPORTED"
    assert _classification(10, 10, 4, -0.1, (-0.3, 0.1)) == "NOT_SUPPORTED"


def test_paired_bootstrap_is_deterministic() -> None:
    specification = {
        "rng_seed": 20260819,
        "resamples": 1000,
        "confidence_level": 0.95,
    }
    first = _bootstrap_interval([0.1, 0.2, 0.3], specification)
    second = _bootstrap_interval([0.1, 0.2, 0.3], specification)
    assert first == second

