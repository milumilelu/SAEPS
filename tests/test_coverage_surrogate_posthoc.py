from experiments.paper_revision_20260916.src.coverage_surrogate_posthoc import (
    surrogate_coverage,
)


def test_surrogate_coverage_is_nominal_when_information_matches() -> None:
    value = surrogate_coverage(4.0, 4.0, 1.959963984540054)
    assert abs(value - 0.95) < 1.0e-12


def test_overstated_reported_information_reduces_coverage() -> None:
    value = surrogate_coverage(16.0, 1.0, 1.959963984540054)
    assert value < 0.50
