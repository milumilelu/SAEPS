from pathlib import Path

from saeps.v5.two_parameter_development_audit import build_two_parameter_development_audit


ROOT = Path(__file__).resolve().parents[1]


def test_actual_v5_two_parameter_development_passes_without_comparative_selection() -> None:
    audit = build_two_parameter_development_audit(ROOT)
    assert audit["engineering_status"] == "PASSED"
    assert audit["binding_valid_count"] == 3
    assert audit["heldout_authorized"] is True
    assert audit["forbidden_metrics_computed"] is False
    assert len(audit["source_records"]) == 3
