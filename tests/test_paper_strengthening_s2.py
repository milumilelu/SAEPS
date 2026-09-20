import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
S2_ROOT = ROOT / "outputs/runs/paper_strengthening_v1/s2_profile_development"


def _read(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_s2_raw_profile_records_are_complete_and_confirmation_closed() -> None:
    summary = _read(
        "outputs/runs/paper_strengthening_v1/s2_profile_development/S2_DEVELOPMENT_SUMMARY.json"
    )
    assert summary["planned_denominator"] == 3
    assert summary["terminal_count"] == 9
    assert summary["confirmation_authorized"] is False
    assert summary["forbidden_metrics_read"] is False
    records = sorted(S2_ROOT.rglob("result.json"))
    assert len(records) == 9
    for path in records:
        row = json.loads(path.read_text(encoding="utf-8"))
        assert row["status"] == "PASS"
        assert row["profile_point_count"] == 8
        assert row["profile_pass_count"] == 8
        assert row["continuation_used"] is False
        assert row["selection_forbidden_metrics_computed"] is False


def test_s2_fit_quality_failure_is_retained_without_threshold_relaxation() -> None:
    result = _read(
        "outputs/runs/paper_strengthening_v1/s2_profile_development/S2_FIT_WINDOW_SUMMARY.json"
    )
    assert result["engineering_gate"] == "FAILED"
    assert result["selected_window_passes_all_records"] is False
    assert result["scientific_profile_claim_authorized"] is False
    assert result["selection_rule"]["no_threshold_relaxation"] is True
    assert any(row["fit_quality_pass_count"] == 7 for row in result["window_summaries"])


def test_s2_failed_lock_hashes_and_authorization_are_auditable() -> None:
    lock_path = ROOT / "configs/paper_strengthening/locked_profile.yaml"
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    record = _read("configs/paper_strengthening/LOCKED_PROFILE_SHA256.json")
    observed = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    assert lock["status"] == "FAILED"
    assert lock["engineering_gate"] == "FAILED"
    assert lock["confirmation_authorized"] is False
    assert lock["scientific_profile_claim_authorized"] is False
    assert record["locked_config_sha256"] == observed
    assert record["status"] == "FAILED"
