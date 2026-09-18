"""Tests for the E4 coordinate/metric audit and the E5 weak-direction diagnostic.

These read the committed result files rather than recomputing, so they are fast; the
numerical recomputation lives in the runner scripts.  What they guard is the claim
structure: that the naive parameter transform really does fail, that control 1 is
invariant while control 2 is not, and that E5 does not quietly overstate its result.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

NAMESPACE = Path(__file__).resolve().parents[1]
E4 = NAMESPACE / "outputs/posthoc/e4"
E5 = NAMESPACE / "outputs/posthoc/e5"


def rows(path: Path) -> list[dict]:
    if not path.is_file():
        pytest.skip(f"{path.name} not available")
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_e4_required_checks_all_pass() -> None:
    data = rows(E4 / "e4_coordinate_metric_audit.csv")
    required = [r for r in data if r["required"] == "True"]
    assert required
    failing = [
        (r["test"], r["seed"], r["relative_error"])
        for r in required
        if float(r["relative_error"]) > float(r["tolerance"])
    ]
    assert not failing, failing


def test_e4_naive_parameter_transform_fails() -> None:
    """Dropping the gradient term must fail; otherwise the test proves nothing."""
    data = rows(E4 / "e4_coordinate_metric_audit.csv")
    naive = [r for r in data if r["test"].endswith("naive_without_gradient_term")]
    assert naive
    for row in naive:
        assert float(row["relative_error"]) > 1.0e-3


def test_e4_control1_invariant_and_control2_not() -> None:
    data = rows(E4 / "e4_coordinate_metric_audit.csv")
    control1 = [
        float(r["relative_error"])
        for r in data
        if r["test"] == "state_metric_control1_metric_TtT_reduced_curvature"
    ]
    control2 = [
        float(r["relative_error"])
        for r in data
        if r["test"] == "state_metric_control2_identity_metric_reduced_curvature"
    ]
    assert control1 and control2
    assert max(control1) < 1.0e-8
    # control 2 must be allowed to move; at least the scaled transforms do
    assert max(control2) > 1.0e-3


def test_e4_does_not_claim_general_reparameterisation_invariance() -> None:
    document = json.loads((E4 / "e4_coordinate_metric_summary.json").read_text(encoding="utf-8"))
    assert "invariance" in document["claim_boundary"]
    assert "arbitrary" in document["claim_boundary"]


def test_e5_directions_are_resolved() -> None:
    document = json.loads((E5 / "e5_weak_direction_summary.json").read_text(encoding="utf-8"))
    assert document["centres_valid"] == document["centres_valid_with_resolved_directions"]
    assert document["eigengap_resolution_threshold"] == 0.1
    for seed, entry in document["per_seed"].items():
        if entry.get("status") != "PASS":
            continue
        for name, spectrum in entry["entries"].items():
            assert spectrum["eigengap"] >= 0.1, (seed, name)
            assert len(spectrum["weakest_direction"]) == 2


def test_e5_uses_the_declared_metric_not_the_whitened_one() -> None:
    document = json.loads((E5 / "e5_weak_direction_summary.json").read_text(encoding="utf-8"))
    assert "Euclidean" in document["parameter_metric"]
    assert "whitened" in document["metric_rationale"]


def test_e5_saeps_weak_direction_is_closer_to_exact_than_raw() -> None:
    document = json.loads((E5 / "e5_weak_direction_summary.json").read_text(encoding="utf-8"))
    assert (
        document["median_angle_SAEPS_vs_exact_degrees"]
        < document["median_angle_raw_vs_exact_degrees"]
    )


def test_e5_does_not_claim_recovery_accuracy() -> None:
    document = json.loads((E5 / "e5_weak_direction_summary.json").read_text(encoding="utf-8"))
    boundary = document["claim_boundary"].lower()
    assert "recovery" in boundary
    assert "variance" in boundary


def test_e5_exact_eigen_directions_are_reference_only() -> None:
    data = rows(E5 / "e5_directional_curvature.csv")
    exact_directions = [r for r in data if r["record_type"] == "directional_curvature" and r["direction"].startswith("exact_dir")]
    assert exact_directions
    assert all(r["direction_is_exact_reference"] == "True" for r in exact_directions)
