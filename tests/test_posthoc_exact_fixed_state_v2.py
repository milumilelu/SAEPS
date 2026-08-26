from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "posthoc_exact_fixed_state_v2", ROOT / "scripts/posthoc_exact_fixed_state_v2.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_v2_preflight_regression_separates_lsqr_and_explicit_roles() -> None:
    result = MODULE.preflight_payload()
    assert result["status"] == "PASSED"
    assert result["v2_regression_checks"]["study_seeds_used"] == []
    assert result["v2_regression_checks"]["distinct_LSQR_value_retained_for_reproduction"]
    assert result["v2_regression_checks"]["identity_uses_explicit_Schur_value"]
    assert result["v2_regression_checks"]["corrected_numerical_status"]


def test_corrected_identity_is_not_contaminated_by_lsqr_crosscheck_value() -> None:
    torch.set_default_dtype(torch.float64)
    theta = torch.tensor([0.2, -0.1], dtype=torch.float64)
    parameter = torch.tensor([math.log(0.9)], dtype=torch.float64)

    def residual(t: torch.Tensor, p: torch.Tensor) -> torch.Tensor:
        physical = torch.exp(p[0])
        return torch.stack([t[0] * physical + t[1] ** 2, torch.sin(t[0]) + physical * t[1]])

    blocks = MODULE.v1.curvature_blocks(residual, theta, parameter, 0.04)
    explicit = MODULE.v1._scalar(blocks["F_SAEPS_tensor"])
    selected_lsqr = explicit * (1.0 + 8.0e-11)
    result = MODULE.corrected_numeric_analysis(
        blocks,
        0.04,
        {},
        selected_lsqr,
        MODULE.v1.load_config(MODULE.CONFIG_PATH),
    )
    assert result["rerun"]["F_SAEPS_reproduction_LSQR"] == selected_lsqr
    assert result["rerun"]["F_SAEPS_mechanistic_explicit"] == explicit
    assert result["numerical_checks"]["exact_error_identity"]
    assert result["numerical_status"] == "PASS"


def test_canary_order_is_fixed_before_execution() -> None:
    assert MODULE.canary_sequence() == [
        ("burgers", 55),
        ("burgers", 56),
        ("burgers", 57),
        ("burgers", 58),
        ("burgers", 59),
    ]
