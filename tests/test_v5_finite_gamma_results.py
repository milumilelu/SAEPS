from pathlib import Path

from saeps.v5.finite_gamma_aggregation import build_finite_gamma_aggregate


ROOT = Path(__file__).resolve().parents[1]


def test_actual_v5_finite_gamma_has_all_planned_terminal_records() -> None:
    aggregate = build_finite_gamma_aggregate(ROOT)
    assert aggregate["engineering_status"] == "PASSED"
    assert aggregate["terminal_count"] == 42
    assert all(row["terminal_count"] == 6 for row in aggregate["alpha_summaries"])
    assert len(aggregate["source_records"]) == 42
    assert aggregate["nominal_gamma_recalibrated"] is False
    assert aggregate["scientific_win_gate"] is None


def test_actual_v5_finite_gamma_failures_are_retained() -> None:
    aggregate = build_finite_gamma_aggregate(ROOT)
    assert aggregate["pass_count"] + aggregate["failure_count"] == 42
    assert len(aggregate["failures"]) == aggregate["failure_count"]
    assert all(row["alpha"] == 1.0e-10 for row in aggregate["failures"])
