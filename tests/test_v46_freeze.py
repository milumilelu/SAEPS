import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v46_freeze_hashes_and_scope() -> None:
    freeze = json.loads((ROOT / "configs/v4_6/TWO_PARAMETER_EXECUTABLE_FREEZE.json").read_text(encoding="utf-8"))
    assert freeze["heldout_seeds"] == [115, 116]
    assert freeze["confirmation_authorized"] is False
    for relative, expected in freeze["file_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
