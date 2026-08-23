import json
from pathlib import Path

from saeps.v5.profile_validation import VALIDATION_SEEDS


ROOT = Path(__file__).resolve().parents[1]


def test_v5_profile_validation_lock_is_numerical_not_outcome_driven() -> None:
    lock = json.loads((ROOT / "configs/v5/PROFILE_OPTIMIZER_LOCK.json").read_text(encoding="utf-8"))
    assert VALIDATION_SEEDS == [73, 74]
    assert lock["selected_candidate"] == "independent_exact_trust_lbfgs"
    assert lock["selected_settings"]["independent_start_from_common_theta0"] is True
    assert lock["selected_settings"]["continuation_forbidden"] is True
