"""Integration tests for the repository adapter against the frozen evidence tag.

These run against the real repository and the real ``jcp-submission-v1`` checkpoints.
They are read-only and are skipped when git or the tag is unavailable, so the pack's
synthetic suite stays runnable on its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import repo_adapter as A  # noqa: E402

# Note: the default dtype is deliberately left untouched.  Changing it here would alter
# the dtype assertions inside the pack's own tests, which expect torch's float32 default.

REPO = A.repo_root()


def frozen_commit() -> str:
    try:
        return A.resolve_commit(REPO, A.DEFAULT_REF)
    except Exception:  # pragma: no cover - environment dependent
        pytest.skip("frozen evidence tag is not available in this checkout")


@pytest.fixture(scope="module")
def commit() -> str:
    return frozen_commit()


@pytest.fixture(scope="module")
def config(commit: str) -> dict:
    return A.two_parameter_config(REPO, commit)


def test_effective_width_override_is_six(config: dict) -> None:
    assert config["_declared_width"] == 12
    assert config["_effective_width"] == 6


def test_checkpoint_state_matches_declared_architecture(commit: str, config: dict) -> None:
    state = A.load_checkpoint(REPO, commit, 215)
    width = config["_effective_width"]
    channel = 4 * width + 1
    assert state["benchmark"] == "coupled_manufactured_reaction_diffusion"
    assert state["theta"].shape == (2 * channel,)
    assert state["coordinate"].shape == (2,)
    assert state["model_metadata"]["hidden_width"] == width


def test_archived_collocation_points_regenerate_bit_exactly(commit: str, config: dict) -> None:
    """The adapter must reproduce the stored tensors, not merely a matching distribution."""
    for seed in (215, 220, 224):
        state = A.load_checkpoint(REPO, commit, seed)
        stored = A.rebuild_points(state["points"])
        regenerated = A.regenerate_points(config, int(state["source_seed"]))
        for field in ("pde_x", "pde_t", "data_x", "data_t", "initial_x", "boundary_t"):
            assert torch.equal(getattr(stored, field), getattr(regenerated, field))


def test_residual_count_is_736(commit: str, config: dict) -> None:
    state = A.load_checkpoint(REPO, commit, 215)
    points = A.rebuild_points(state["points"])
    count = A.residual_count(state["theta"], state["coordinate"], points, config)
    assert count == 736


def test_log_coordinate_identity_holds(commit: str, config: dict) -> None:
    from e1_identity import identity_error, coordinate_blocks

    state = A.load_checkpoint(REPO, commit, 215)
    points = A.rebuild_points(state["points"])
    blocks = coordinate_blocks(state["theta"], state["coordinate"], points, config, "log")
    _, _, satisfied = identity_error(blocks["H"], blocks["G"], torch.diag(blocks["g"]))
    assert satisfied


def test_physical_coordinate_identity_holds(commit: str, config: dict) -> None:
    from e1_identity import identity_error, coordinate_blocks

    state = A.load_checkpoint(REPO, commit, 215)
    points = A.rebuild_points(state["points"])
    blocks = coordinate_blocks(state["theta"], state["coordinate"], points, config, "physical")
    _, _, satisfied = identity_error(blocks["H"], blocks["G"], torch.zeros_like(blocks["G"]))
    assert satisfied


def test_identity_target_is_gradient_in_log_and_zero_in_physical(commit: str, config: dict) -> None:
    """A non-zero gradient must not be mistaken for an implementation error."""
    from e1_identity import coordinate_blocks

    state = A.load_checkpoint(REPO, commit, 215)
    points = A.rebuild_points(state["points"])
    log_blocks = coordinate_blocks(state["theta"], state["coordinate"], points, config, "log")
    difference = log_blocks["H"] - log_blocks["G"]
    assert not torch.allclose(log_blocks["g"], torch.zeros_like(log_blocks["g"]))
    assert torch.allclose(difference - torch.diag(log_blocks["g"]), torch.zeros_like(difference))


def test_scalar_archive_reports_no_state_tensor(commit: str) -> None:
    record = A.scalar_posthoc_record(REPO, commit, "Burgers", 55)
    for field in ("theta", "residual", "observation", "points"):
        assert field not in record
    assert record["exact_blocks"]["H_ll"] is not None
