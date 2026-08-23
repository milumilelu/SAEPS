from pathlib import Path

from saeps.v5.profile_development_audit import build_profile_development_audit


ROOT = Path(__file__).resolve().parents[1]


def test_actual_v5_profile_development_authorizes_heldout_without_threshold_change() -> None:
    audit = build_profile_development_audit(ROOT)
    assert audit["engineering_status"] == "PASSED"
    assert audit["heldout_authorized"] is True
    assert len(audit["validation_records"]) == 2
    assert audit["heldout_accuracy_thresholds_changed"] is False
    assert audit["development_accuracy_is_nonbinding"] is True
    assert audit["forbidden_metrics_read"] is False
