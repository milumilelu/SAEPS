"""Tests for the 2026-09-18 report corrections.

Two errors are pinned here so they cannot return silently:

1. ``E_GN_fix`` must follow the manuscript definition
   ``|F_raw - H_fix| / (|H_red| + eps)``.  The runner used
   ``|F_se - F_raw| / (|H_fix| + eps)``, which is a different ratio and reported
   about 0.944 instead of about 0.0012.
2. The primary sign test must use the declared statistical unit, the data seed (n=6),
   not the 24 correlated fits.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

CORRECTION = Path(__file__).resolve().parents[1] / "outputs/posthoc/report_correction_20260918"
EPSILON = 1.0e-8

# the manuscript-exact regression case quoted in the review
REGRESSION = {
    "F_raw": 31.691529364882115,
    "F_se_GN": 1.6381987355663945,
    "H_fix_exact": 31.694172677784533,
    "H_red_exact": 1.6410548213691847,
    "reported": 0.9482289039492354,
    "expected": 0.0016107401482815197,
}


def rows(name: str) -> list[dict]:
    path = CORRECTION / name
    if not path.is_file():
        pytest.skip(f"{name} not available")
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_manuscript_definition_regression() -> None:
    """The exact case from the review must reproduce to machine precision."""
    expected = abs(REGRESSION["F_raw"] - REGRESSION["H_fix_exact"]) / (
        abs(REGRESSION["H_red_exact"]) + EPSILON
    )
    assert abs(expected - REGRESSION["expected"]) < 1.0e-15
    # the old formula gives a different number, which is the point
    old = abs(REGRESSION["F_se_GN"] - REGRESSION["F_raw"]) / (
        abs(REGRESSION["H_fix_exact"]) + EPSILON
    )
    assert abs(old - REGRESSION["reported"]) < 1.0e-12
    assert abs(old - expected) > 0.9


def test_corrected_table_matches_the_regression_row() -> None:
    data = rows("e3_metrics_corrected.csv")
    match = [
        r
        for r in data
        if r["cohort"] == "e3_heldout_1e5"
        and r["data_seed"] == "916101"
        and r["initialization_seed"] == "926001"
        and r["noise_level"] == "0.0"
    ]
    assert len(match) == 1
    assert abs(float(match[0]["E_GN_fix"]) - REGRESSION["expected"]) < 1.0e-15


def test_algebraic_identity_holds_for_every_row() -> None:
    """F_se - H_red = (F_raw - H_fix) - (C_GN - C_exact) must be exact."""
    data = rows("metric_definition_audit.csv")
    assert data
    for row in data:
        if row["identity_residual"] in ("", None):
            continue
        assert float(row["identity_residual"]) <= 1.0e-9, row


def test_reported_and_recomputed_columns_both_survive() -> None:
    """The old value must not be silently overwritten."""
    data = rows("metric_definition_audit.csv")
    paired = [r for r in data if r["E_GN_fix_reported"] and r["E_GN_fix_recomputed"]]
    assert paired
    for row in paired:
        assert float(row["E_GN_fix_reported"]) != float(row["E_GN_fix_recomputed"])
    document = json.loads((CORRECTION / "metric_correction_summary.json").read_text(encoding="utf-8"))
    assert document["unaffected_metrics"] == ["E_raw", "E_SAEPS", "E_fix", "E_relax"]
    assert document["checks"]["e_raw_and_e_saeps_unchanged"] is True
    assert document["frozen_files_modified"] is False


def test_degenerate_case_is_zero() -> None:
    """If F_raw equals H_fix then E_GN_fix is zero regardless of relaxation."""
    f_raw = h_fix = 2.5
    value = abs(f_raw - h_fix) / (abs(0.4) + EPSILON)
    assert value == 0.0
    document = json.loads((CORRECTION / "metric_correction_summary.json").read_text(encoding="utf-8"))
    assert document["checks"]["degenerate_case_gives_zero"] is True


def test_sign_test_uses_the_declared_unit() -> None:
    document = json.loads((CORRECTION / "e3_cluster_statistics.json").read_text(encoding="utf-8"))
    assert document["declared_statistical_unit"] == "data_seed"
    seed = document["data_seed_level_summary"]
    assert seed["aggregation_unit"] == "data_seed"
    assert seed["independent_units"] == 6
    assert abs(seed["one_sided_sign_test_p"] - 2 ** -6) < 1.0e-15
    # the old value treated 24 correlated fits as independent
    assert abs(2 ** -24 - 5.960464477539063e-08) < 1.0e-20
    assert seed["one_sided_sign_test_p"] > 1.0e-3


def test_noise_layers_are_not_pooled_into_independent_units() -> None:
    document = json.loads((CORRECTION / "e3_cluster_statistics.json").read_text(encoding="utf-8"))
    layers = document["per_noise_layer"]
    assert len(layers) == 2
    for block in layers.values():
        assert block["independent_units"] == 6
        assert "not independent" in block["note"]
    assert "twelve" in document["multiple_comparison_note"]


def test_planned_grid_is_read_from_the_protocol_not_from_successes() -> None:
    document = json.loads((CORRECTION / "e3_cluster_statistics.json").read_text(encoding="utf-8"))
    assert document["planned_grid_size"] == 24
    assert document["membership_missing"] == []
    assert document["membership_duplicates"] == []
    assert document["membership_unexpected"] == []
    membership = rows("e3_cluster_membership.csv")
    assert len(membership) == 24


def test_both_improvement_ratios_are_reported_separately() -> None:
    document = json.loads((CORRECTION / "e3_cluster_statistics.json").read_text(encoding="utf-8"))
    seed = document["data_seed_level_summary"]
    assert seed["ratio_of_medians"] is not None
    assert seed["median_paired_ratio"] is not None
    assert abs(seed["ratio_of_medians"] - seed["median_paired_ratio"]) > 1.0
    fit = json.loads((CORRECTION / "fit_level_summary.json").read_text(encoding="utf-8"))
    assert fit["aggregation_unit"] == "fit"
    assert fit["independence_claimed"] is False
