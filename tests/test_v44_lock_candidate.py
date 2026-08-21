import json
from pathlib import Path

from saeps.config import load_config


ROOT = Path(__file__).resolve().parents[1]


def test_v44_lock_candidate_has_exact_planned_cohort_and_joint_rule() -> None:
    config = load_config(ROOT / "configs/v4_4/locked_allen_cahn_confirmation.yaml")
    assert config["planned_seeds"] == list(range(75, 85))
    assert config["confirmation_authorized"] is False
    assert config["primary"]["minimum_valid_pairs"] == 8
    assert config["primary"]["planned_strict_wins_required"] == 8
    assert config["primary"]["success_requires_all_primary_conditions"] is True


def test_v44_semantic_graph_keeps_profile_and_indicator_nonbinding() -> None:
    graph = json.loads(
        (ROOT / "docs/v4_4/ALLEN_SEMANTIC_GATE_GRAPH.json").read_text(encoding="utf-8")
    )
    assert graph["profile_cannot_change_primary_validity"] is True
    assert graph["indicator_cannot_change_primary_validity"] is True
    assert "profile_status" not in graph["binding_nodes"]

