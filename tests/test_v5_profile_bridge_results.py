from pathlib import Path

from saeps.v5.profile_aggregation import build_profile_bridge_aggregate


ROOT = Path(__file__).resolve().parents[1]


def test_actual_v5_profile_bridge_adjudicates_all_planned_seeds() -> None:
    aggregate = build_profile_bridge_aggregate(ROOT)
    assert aggregate["engineering_status"] == "PASSED"
    assert aggregate["planned_denominator"] == 5
    assert aggregate["terminal_count"] == 5
    assert aggregate["evaluable_count"] == 5
    assert aggregate["profile_valid_count"] == 1
    assert aggregate["scientific_status"] == "NOT_SUPPORTED"
    assert aggregate["rescue_cohort_authorized"] is False


def test_actual_v5_profile_bridge_keeps_comparative_quantities_nonbinding() -> None:
    aggregate = build_profile_bridge_aggregate(ROOT)
    assert aggregate["descriptive_comparative"]["role"] == (
        "descriptive_nonbinding_for_profile_bridge_adjudication"
    )
    assert len(aggregate["source_records"]) == 5
