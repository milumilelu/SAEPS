"""Tests for the adapter-fidelity table.

Bit-exact point regeneration is not enough on its own: a wrong weight or config override
would keep the points identical and could still satisfy the E1 coordinate identity.  This
table rebuilds the reduced matrices and compares them to the archive, so these tests check
that the agreement is real, that the provenance needed to reproduce it is present, and
that the result agrees with the earlier matrix-consistency artifact.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

FIDELITY = Path(__file__).resolve().parents[1] / "outputs/posthoc/adapter_fidelity"
OLDER = Path(__file__).resolve().parents[1] / "outputs/posthoc/e2_curvature/e2_matrix_consistency.csv"


def rows(name: str, base: Path = FIDELITY) -> list[dict]:
    path = base / name
    if not path.is_file():
        pytest.skip(f"{name} not available")
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_every_valid_point_is_compared_for_three_quantities() -> None:
    data = [r for r in rows("adapter_fidelity.csv") if r.get("status") in ("PASS", "FAIL")]
    assert len(data) == 24
    valid = {r["seed"] for r in data}
    assert len(valid) == 8
    for seed in valid:
        quantities = {r["quantity"] for r in data if r["seed"] == seed}
        assert quantities == {"F_raw", "F_se_GN_explicit", "H_red_exact_gamma"}


def test_all_comparisons_pass_the_declared_acceptance() -> None:
    data = [r for r in rows("adapter_fidelity.csv") if r.get("status") in ("PASS", "FAIL")]
    for row in data:
        assert row["status"] == "PASS", row
        assert float(row["relative_difference_frobenius"]) <= float(row["declared_relative_acceptance"])


def test_observed_agreement_is_much_tighter_than_the_declared_bound() -> None:
    document = json.loads((FIDELITY / "adapter_fidelity_summary.json").read_text(encoding="utf-8"))
    assert document["max_relative_difference"] < 1.0e-9
    assert document["max_relative_difference"] < document["declared_relative_acceptance"] / 1.0e3
    assert document["comparisons_passing"] == document["comparisons"]


def test_provenance_needed_to_reproduce_is_recorded() -> None:
    row = next(r for r in rows("adapter_fidelity.csv") if r.get("status") == "PASS")
    assert int(row["declared_width"]) == 12
    assert int(row["effective_width"]) == 6
    assert int(row["state_parameters"]) == 50
    assert int(row["residual_count"]) == 736
    assert float(row["alpha"]) == 1.0e-08
    for key in ("checkpoint_sha256", "locked_config_sha256", "execution_config_sha256",
                "source_record_sha256", "checkpoint_path", "locked_config", "gamma"):
        assert row[key] not in ("", None), key
    assert "mean" in row["objective"]


def test_f_raw_and_reduced_reference_are_bit_exact() -> None:
    data = [r for r in rows("adapter_fidelity.csv") if r.get("status") in ("PASS", "FAIL")]
    for row in data:
        if row["quantity"] in ("F_raw", "H_red_exact_gamma"):
            assert float(row["relative_difference_frobenius"]) == 0.0, row


def test_agrees_with_the_earlier_matrix_consistency_artifact() -> None:
    """Same recomputation, older column layout: the two must not disagree."""
    newer = {r["seed"]: r for r in rows("adapter_fidelity.csv") if r.get("status") == "PASS"}
    older = rows("e2_matrix_consistency.csv", base=OLDER.parent)
    assert newer and older
    for row in older:
        seed = row["seed"]
        quantity = row["quantity"]
        match = [r for r in rows("adapter_fidelity.csv")
                 if r.get("status") == "PASS" and r["seed"] == seed and r["quantity"] == quantity]
        assert len(match) == 1, (seed, quantity)
        assert abs(float(match[0]["relative_difference_frobenius"])
                   - float(row["recomputed_sha_relative_error"])) < 1.0e-15
