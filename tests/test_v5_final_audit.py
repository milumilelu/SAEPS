from pathlib import Path

from saeps.v5.final_audit import build_final_audit
from saeps.v5.final_validation import validate_v5_repository


ROOT = Path(__file__).resolve().parents[1]


def test_v5_final_audit_preserves_all_scientific_boundaries() -> None:
    audit = build_final_audit(ROOT)
    assert audit["scientific_conclusion"] == "PARTIALLY_SUPPORTED"
    assert audit["full_general_JCP_claim_ready"] is False
    statuses = {row["evidence"]: row["status"] for row in audit["evidence_table"]}
    assert statuses["Burgers scalar comparative"] == "SUPPORTED"
    assert statuses["Allen-Cahn scalar replication"] == "SUPPORTED"
    assert statuses["Nonlinear profile bridge"] == "NOT_SUPPORTED"
    assert statuses["Two-parameter comparative geometry"] == "INCONCLUSIVE"


def test_v5_post_execution_validator_passes_core_checks() -> None:
    result = validate_v5_repository(ROOT, require_final=False)
    assert result["status"] == "PASSED"
    assert all(row["status"] == "PASS" for row in result["checks"].values())
