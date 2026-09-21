from pathlib import Path

from experiments.paper_revision_20260916.src.profile_resolution_posthoc import (
    aggregate,
    load_rows,
)


ROOT = Path(__file__).resolve().parents[1]


def test_saved_profile_resolution_has_complete_step_denominator() -> None:
    rows = load_rows(ROOT / "outputs/posthoc/paper_strengthening/e7_rescue_v2_summary.json")
    summary = aggregate(rows)
    assert len(rows) == 9
    assert [row["planned_points"] for row in summary] == [3, 3, 3]
    assert all(row["reference_agreement_count"] >= 0 for row in summary)
