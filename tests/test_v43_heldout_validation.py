from pathlib import Path

from saeps.v43.heldout_validation import validate_allen_heldout


ROOT = Path(__file__).resolve().parents[1]


def test_real_frozen_allen_heldout_records_pass() -> None:
    result = validate_allen_heldout(ROOT)
    assert result["status"] == "PASSED"
    assert result["binding_valid_count"] == 2
    assert result["directional_indicator_pass_count"] == 2
    assert result["comparative_quantities_used_for_acceptance"] is False

