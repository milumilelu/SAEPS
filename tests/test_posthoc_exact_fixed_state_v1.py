from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "posthoc_exact_fixed_state_v1", ROOT / "scripts/posthoc_exact_fixed_state_v1.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_tiny_exact_block_preflight_passes_without_study_seeds() -> None:
    result = MODULE.preflight_payload()
    assert result["study_seeds_used"] == []
    assert result["status"] == "PASSED"
    assert all(result["checks"].values())


def test_exact_error_identity_on_nonlinear_log_parameter_residual() -> None:
    torch.set_default_dtype(torch.float64)
    theta = torch.tensor([0.1, -0.4], dtype=torch.float64)
    parameter = torch.tensor([math.log(0.8)], dtype=torch.float64)

    def residual(t: torch.Tensor, p: torch.Tensor) -> torch.Tensor:
        physical = torch.exp(p[0])
        return torch.stack([t[0] ** 2 + physical * t[1], torch.cos(t[1]) + physical * t[0]])

    blocks = MODULE.curvature_blocks(residual, theta, parameter, 0.03)
    fraw = MODULE._scalar(blocks["G_ll_tensor"])
    fse = MODULE._scalar(blocks["F_SAEPS_tensor"])
    hfix = MODULE._scalar(blocks["H_ll_tensor"])
    hred = MODULE._scalar(blocks["H_red_exact_tensor"])
    cgn = MODULE._scalar(blocks["C_relax_GN_tensor"])
    cexact = MODULE._scalar(blocks["C_relax_exact_tensor"])
    assert math.isclose(fse - hred, (fraw - hfix) - (cgn - cexact), rel_tol=1e-12, abs_tol=1e-12)


def test_frozen_manifest_seed_sets_match_protocol() -> None:
    config = MODULE.load_config(MODULE.CONFIG_PATH)
    state = MODULE._manifest_state(config)
    assert state["burgers"]["valid"] == [55, 56, 58, 59, 60, 62, 64, 65, 66, 67, 68, 69]
    assert state["burgers"]["invalid"] == [57, 61, 63]
    assert state["allen_cahn"]["valid"] == [75, 76, 77, 78, 79, 80, 82, 83, 84]
    assert state["allen_cahn"]["invalid"] == [81]
