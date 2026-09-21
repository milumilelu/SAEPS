from __future__ import annotations

from pathlib import Path

from experiments.paper_revision_20260916.src.parameter_block_correction_posthoc import (
    base_row,
    read_architecture,
    read_exact_blocks,
)


ROOT = Path(__file__).resolve().parents[1]


def test_parameter_block_identity_and_signed_fields() -> None:
    row = base_row(
        source="test",
        group="unit",
        seed=0,
        state_parameters=2,
        f_raw=10.0,
        f_se=3.0,
        h_ll=8.0,
        h_red=2.0,
        gamma=0.1,
    )
    assert row["F_block"] == 1.0
    assert row["signed_error_block"] == -1.0
    assert row["identity_pass"] is True


def test_saved_architecture_and_exact_block_denominators() -> None:
    architecture = read_architecture(
        ROOT / "experiments/paper_revision_20260916/outputs/development/e6/e6_architecture_accuracy.csv"
    )
    exact = read_exact_blocks(ROOT / "outputs/posthoc/exact_fixed_state_v3")
    assert len(architecture) == 18
    assert len(exact) == 21
    assert all(row["identity_pass"] for row in architecture + exact)
