import json
from pathlib import Path

from saeps.io_utils import read_json, write_json_atomic
from saeps.logging_utils import configure_logger, log_event


def test_atomic_json_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "result.json"
    payload = {"schema_version": 1, "status": "PASS", "values": [1.0, 2.0]}
    write_json_atomic(path, payload)
    assert read_json(path) == payload
    assert not list(path.parent.glob("*.tmp"))


def test_structured_log_is_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    logger = configure_logger("test.structured", path)
    log_event(logger, "unit_test", seed=7, status="PASS")
    payload = json.loads(path.read_text(encoding="utf-8").strip())
    assert payload["event"] == "unit_test"
    assert payload["fields"] == {"seed": 7, "status": "PASS"}

