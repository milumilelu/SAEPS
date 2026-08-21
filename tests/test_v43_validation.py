import json
from pathlib import Path

from saeps.v43.validation import validate_allen_engineering, validate_record_schema


ROOT = Path(__file__).resolve().parents[1]


def test_real_allen_engineering_records_pass_schema_and_binding_validation() -> None:
    result = validate_allen_engineering(ROOT)
    assert result["status"] == "PASSED"
    assert result["binding_valid_count"] == 3
    assert result["profile_bridge_pass_count"] == 1
    assert result["directional_indicator_pass_count"] == 3


def test_real_seed70_record_has_independent_status_schema() -> None:
    record = json.loads(
        (
            ROOT
            / "outputs/runs/v4_3_allen_cahn_development/architecture_w8/seed_70/result.json"
        ).read_text(encoding="utf-8")
    )
    validate_record_schema(record)
    assert record["statuses"]["score_solver_status"] == "SOLVER_FAILURE"
    assert record["binding_valid"] is True

