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


E6 = Path(__file__).resolve().parents[1] / "outputs/development/e6"


def e6_rows(name: str) -> list[dict]:
    path = E6 / name
    if not path.is_file():
        pytest.skip(f"{name} not available")
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_e6_is_a_paired_architecture_design() -> None:
    """Same data seeds and initializations for every architecture, or the pairing is broken."""
    data = e6_rows("e6_architecture_accuracy.csv")
    assert len(data) == 18
    keys = {}
    for row in data:
        keys.setdefault(row["label"], set()).add(
            (row["data_seed"], row["initialization_seed"], row["noise_level"])
        )
    assert len(keys) == 3
    first = next(iter(keys.values()))
    for label, group in keys.items():
        assert group == first, label


def test_e6_reports_failures_rather_than_replacing_them() -> None:
    """No centre may be silently replaced by function-preserving widening."""
    data = e6_rows("e6_center_availability.csv")
    assert len(data) == 18
    for row in data:
        assert row["reference_reduction_status"] in ("PASS", "REFERENCE_REDUCTION_FAILED")
        assert row["centre_available"] in ("True", "False")
    document = json.loads((E6 / "e6_summary.json").read_text(encoding="utf-8"))
    assert "widening" in document["claim_boundary"].lower()
    assert document["independent_confirmation"] is False


def test_e6_state_counts_match_the_specified_architectures() -> None:
    data = e6_rows("e6_architecture_accuracy.csv")
    counts = {row["label"]: int(row["state_parameters"]) for row in data}
    assert counts["base_2_16_1"] == 65
    assert counts["wide_2_32_1"] == 129
    assert counts["deep_2_16_16_1"] == 337


def test_e6_hvp_check_is_tight() -> None:
    """The assembled Hessian must match an independent HVP, at every architecture."""
    data = e6_rows("e6_architecture_accuracy.csv")
    worst = max(float(r["hvp_max_relative_difference"]) for r in data)
    assert worst < 1.0e-12, worst


def test_e6_accuracy_does_not_degrade_with_size() -> None:
    """The claim under test: the SAEPS advantage survives leaving the compact network."""
    document = json.loads((E6 / "e6_summary.json").read_text(encoding="utf-8"))
    by_arch = document["by_architecture"]
    base = by_arch["base_2_16_1"]["median_E_SAEPS"]
    for label in ("wide_2_32_1", "deep_2_16_16_1"):
        assert by_arch[label]["median_E_raw"] < 1.0e6
        assert by_arch[label]["median_E_SAEPS"] < base * 1.5, label
    for label, block in by_arch.items():
        assert block["SAEPS_wins"] == block["centres_available"], label
