from pathlib import Path

from saeps.v49.aggregation import aggregate_v4_8


ROOT = Path(__file__).resolve().parents[1]


def test_v4_8_actual_outputs_are_complete_and_hash_valid() -> None:
    result = aggregate_v4_8(ROOT)
    assert result["integrity_gate"] == "PASS"
    assert result["planned"] == result["completed"] == 60
    assert result["noise_sparsity"]["planned"] == 45
    assert result["architecture"]["planned"] == 15
    assert result["exact_anchors"]["planned"] == 15
