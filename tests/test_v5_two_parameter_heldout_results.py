from pathlib import Path

from saeps.v5.two_parameter_heldout_audit import build_two_parameter_heldout_audit


ROOT = Path(__file__).resolve().parents[1]


def test_actual_v5_two_parameter_heldout_authorizes_confirmation_by_binding_only() -> None:
    audit = build_two_parameter_heldout_audit(ROOT)
    assert audit["engineering_status"] == "PASSED"
    assert audit["binding_valid_count"] == 2
    assert audit["confirmation_authorized"] is True
    assert audit["comparative_metrics_entered_authorization"] is False
    assert audit["authorization_inputs"] == [
        "binding_valid_seed_213",
        "binding_valid_seed_214",
    ]
