from pathlib import Path

from saeps.v49.final_audit import audit_v4, render_report


ROOT = Path(__file__).resolve().parents[1]


def test_v4_final_audit_uses_actual_complete_evidence() -> None:
    audit = audit_v4(ROOT)
    assert all(audit["checks"].values())
    assert audit["scientific_conclusion"] == "PARTIALLY_SUPPORTED"
    assert audit["recommendation"] == "INVESTIGATE_NUMERICS"
    assert audit["results"]["two_parameter"]["comparative_hypothesis_tested"] is False
    assert audit["results"]["robustness"]["wide_architecture_valid"] == 0
    report = render_report(audit)
    assert "Two-parameter confirmation was never" in report
    assert "0/5 valid centers" in report
