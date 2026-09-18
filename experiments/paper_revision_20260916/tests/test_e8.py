"""Tests for the E8 matched-damping cost comparison.

The load-bearing check here is the LSQR assembly.  An earlier version treated the
helper's ``Fse`` as a correction to subtract from ``F_raw``, which produced a 17.2
relative error against the dense solve and would have been reported as "LSQR fails at
weak damping".  The value is already the reduced quantity.  These tests pin that down
against the dense reference so the mistake cannot come back silently.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

E8 = Path(__file__).resolve().parents[1] / "outputs/posthoc/e8"

STAGES = (
    "setup_seconds",
    "spectral_seconds",
    "preconditioner_seconds",
    "solve_seconds",
    "verification_seconds",
)


def rows() -> list[dict]:
    path = E8 / "e8_matched_gamma_cost.csv"
    if not path.is_file():
        pytest.skip("E8 results not available")
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_every_condition_is_recorded_and_passes() -> None:
    data = rows()
    assert data
    assert all(r["status"] == "PASS" for r in data)
    assert all(r["initial_guess"] == "zero" for r in data)
    assert all(r["warmup_discarded"] == "True" for r in data)


def test_all_methods_share_one_gamma_per_alpha() -> None:
    """Matched damping is the whole point: no method may get its own gamma."""
    data = rows()
    for seed in {r["seed"] for r in data}:
        for alpha in {r["alpha"] for r in data}:
            gammas = {
                round(float(r["gamma"]), 12)
                for r in data
                if r["seed"] == seed and r["alpha"] == alpha
            }
            assert len(gammas) == 1, (seed, alpha, gammas)


def test_lsqr_agrees_with_the_dense_reference() -> None:
    """Regression guard for the Fse assembly bug."""
    data = rows()
    lsqr = [r for r in data if r["method"] == "scaled_LSQR"]
    assert lsqr
    worst = max(float(r["accuracy_vs_dense_reference"]) for r in lsqr)
    assert worst < 1.0e-8, worst


def test_cg_accuracy_degrades_as_damping_weakens() -> None:
    data = rows()
    by_alpha = {}
    for r in data:
        if r["method"] == "CG":
            by_alpha.setdefault(float(r["alpha"]), []).append(
                float(r["accuracy_vs_dense_reference"])
            )
    weakest = by_alpha[min(by_alpha)]
    strongest = by_alpha[max(by_alpha)]
    assert max(weakest) > max(strongest)


def test_every_stage_is_timed_separately() -> None:
    data = rows()
    for row in data:
        for stage in STAGES:
            assert stage in row
            assert float(row[stage]) >= 0.0
        total = sum(float(row[s]) for s in STAGES)
        assert float(row["reported_total_seconds"]) >= total - 1.0e-6


def test_resource_manifest_states_its_limits() -> None:
    document = json.loads((E8 / "e8_resource_manifest.json").read_text(encoding="utf-8"))
    resources = document["resources"]
    for key in ("device", "dtype", "torch_threads", "torch", "numpy"):
        assert resources[key] not in (None, "")
    # no peak tensor memory may be claimed, and the large-scale timing must not be implied
    assert "NOT" in resources["peak_memory_convention"] or "not" in resources["peak_memory_convention"]
    assert document["large_scale_operator_timing_run"] is False
    assert "training_and_polish_excluded" in document
    assert document["training_and_polish_excluded"] is True


def test_cost_is_reported_not_hidden() -> None:
    """The expensive stage must be visible, whichever stage it turns out to be."""
    data = rows()
    lsqr_at_weakest = [
        r
        for r in data
        if r["method"] == "scaled_LSQR" and float(r["alpha"]) == min(float(x["alpha"]) for x in data)
    ]
    assert lsqr_at_weakest
    for row in lsqr_at_weakest:
        assert float(row["solve_seconds"]) > 0.0
