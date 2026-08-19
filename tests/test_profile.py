from __future__ import annotations

from pathlib import Path

import pytest

from saeps.p3_validation import run_profile_validation
from saeps.profile import ProfileFitError, fit_local_quadratic


ROOT = Path(__file__).resolve().parents[1]


def test_p3_known_curvature_end_to_end(tmp_path: Path) -> None:
    result = run_profile_validation(
        ROOT / "configs/p3_profile.yaml", tmp_path, ROOT, write_output=False
    )
    assert result["status"] == "PASS"
    assert all(result["checks"].values())


def test_fit_rejects_empty_profile() -> None:
    with pytest.raises(ProfileFitError):
        fit_local_quadratic([], {
            "minimum_r_squared": 0.9,
            "maximum_normalized_rmse": 0.1,
            "maximum_design_condition": 1.0e6,
            "positive_curvature_required": True,
        })

