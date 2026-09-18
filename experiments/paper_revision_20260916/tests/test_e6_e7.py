"""Tests for E7, the independent profile-resolution check.

E7 is what stops the exact Schur reference from being self-certifying: it re-minimises the
state at displaced parameter values and reads the curvature from a symmetric difference.
These tests pin the shape of that evidence: the ladder must not be monotone (otherwise the
h^-2 amplification is not being seen), the reference check must be reported separately
from the method comparison, and the failing step must stay in the file rather than being
dropped.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

E7 = Path(__file__).resolve().parents[1] / "outputs/heldout/e7"


def rows(name: str) -> list[dict]:
    path = E7 / name
    if not path.is_file():
        pytest.skip(f"{name} not available")
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_every_step_is_recorded_including_failures() -> None:
    data = rows("e7_branch_diagnostics.csv")
    assert data
    seeds = {r["data_seed"] for r in data}
    assert len(seeds) == 3
    for seed in seeds:
        steps = [r for r in data if r["data_seed"] == seed]
        assert len(steps) == 7, seed
    # the one step that misses the acceptance level must still be present
    failing = [r for r in data if r["reference_check_passes"] == "False"]
    assert failing, "a failing step was removed from the record"
    assert all(float(r["relative_difference"]) > 0.1 for r in failing)


def test_reference_check_is_reported_per_step() -> None:
    data = rows("e7_branch_diagnostics.csv")
    for row in data:
        assert float(row["exact_schur_reference"]) > 0.0
        assert float(row["relative_difference"]) >= 0.0
        assert row["branches_comparable"] in ("True", "False")


def test_resolution_error_is_not_monotone_in_step_size() -> None:
    """The smallest step must not be the most accurate; that is the h^-2 signature."""
    data = rows("e7_branch_diagnostics.csv")
    by_seed = {}
    for row in data:
        by_seed.setdefault(row["data_seed"], []).append(row)
    for seed, group in by_seed.items():
        group.sort(key=lambda r: float(r["step"]))
        smallest = float(group[0]["relative_difference"])
        best = min(float(r["relative_difference"]) for r in group)
        assert best < smallest, (seed, best, smallest)


def test_three_gradient_tolerances_are_all_attempted() -> None:
    data = rows("e7_profile_resolution.csv")
    assert {r["tolerance"] for r in data} == {"1e-08", "1e-10", "1e-12"}
    # both sides and every step, for every tolerance
    for seed in {r["data_seed"] for r in data}:
        group = [r for r in data if r["data_seed"] == seed]
        assert len(group) == 7 * 2 * 3, seed
        assert {r["side"] for r in group} == {"plus", "minus"}


def test_optimisation_limits_are_disclosed_not_hidden() -> None:
    """The state optimisation is tolerance-limited; the record must show that."""
    data = rows("e7_profile_resolution.csv")
    reached = sum(1 for r in data if r["tolerance_reached"] == "True")
    assert reached < len(data), "if every tolerance were reached this test should change"
    document = json.loads((E7 / "e7_summary.json").read_text(encoding="utf-8"))
    assert document["reanchor_forbidden"] is True
    assert document["gamma_reestimation_forbidden"] is True
    assert document["max_inner_iterations_per_point"] == 1000


def test_method_comparison_is_separate_from_the_reference_check() -> None:
    document = json.loads((E7 / "e7_summary.json").read_text(encoding="utf-8"))
    boundary = document["claim_boundary"].lower()
    assert "separate" in boundary
    assert "algebraic" in boundary
    data = rows("e7_branch_diagnostics.csv")
    for row in data:
        assert "E_raw_same_reference" in row
        assert "E_SAEPS_same_reference" in row
        assert row["SAEPS_wins_same_reference"] in ("True", "False")
