from pathlib import Path

from saeps.v5.profile_engineering import select_profile_candidate


ROOT = Path(__file__).resolve().parents[1]


def test_actual_v5_profile_candidate_selection_uses_frozen_rule() -> None:
    selection = select_profile_candidate(ROOT)
    assert selection["selected_candidate"] == "independent_exact_trust_lbfgs"
    assert selection["forbidden_metrics_read"] is False
    assert len(selection["candidate_summaries"]) == 2
    assert sum(row["complete_seed_count"] for row in selection["candidate_summaries"]) == 4
