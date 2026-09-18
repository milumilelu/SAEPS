"""Tests for the content integration into the manuscript.

The integration adds four experiment sections and the tables that back them.  Two things
must hold, and both are checkable without reading the paper: no experimental number may be
typed into the prose, and the new material must match the register of the rest of the
document.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
NAMESPACE = Path(__file__).resolve().parents[1]
INTEGRATION = NAMESPACE / "outputs/posthoc/manuscript_integration"
STYLE = NAMESPACE / "outputs/posthoc/narrative_pass/style_integrated.json"
MANUSCRIPT = REPO / "paper/revise/SAEPS_manuscript_integrated.tex"
NARRATIVE = REPO / "paper/revise/SAEPS_manuscript_narrative.tex"

SECTION_LABELS = (
    "sec:nonaffine_setup",
    "sec:nonaffine_results",
    "sec:architecture",
    "sec:profile_resolution",
    "sec:matched_cost",
)
TABLE_LABELS = (
    "tab:e3_heldout",
    "tab:e3_seeds",
    "tab:e6_architecture",
    "tab:e7_scope",
    "tab:e8_cost",
)


def manuscript() -> str:
    if not MANUSCRIPT.is_file():
        pytest.skip("integrated manuscript not present")
    return MANUSCRIPT.read_text(encoding="utf-8")


def test_all_new_sections_and_tables_are_present() -> None:
    """Sections live in the manuscript; the generated tables live in the input file."""
    body = manuscript()
    for label in SECTION_LABELS:
        assert f"\\label{{{label}}}" in body, label
    tables = (INTEGRATION / "paper_tables.tex").read_text(encoding="utf-8")
    for label in TABLE_LABELS:
        assert f"\\label{{{label}}}" in tables, label


def test_every_new_table_is_referenced_from_the_text() -> None:
    body = manuscript()
    for label in TABLE_LABELS:
        assert f"\\ref{{{label}}}" in body, label


def test_numbers_come_from_macros_not_from_typed_digits() -> None:
    """The repository forbids hard-coding experimental results in the manuscript."""
    body = manuscript()
    assert "\\input{paper_numbers}" in body
    for prefix in ("Ethree", "Esix", "Eseven", "Eeight", "Nonaffine"):
        assert re.search(rf"\\{prefix}[A-Za-z]+", body), prefix
    generated = json.loads((INTEGRATION / "paper_numbers.json").read_text(encoding="utf-8"))
    values = generated["values"]
    assert len(values) >= 55
    # spot-check that a published value is present in the macro file and not in the prose
    for key in ("EthreeRone", "EthreePSeed", "EsixSAEPSDeep", "EsevenStationarity"):
        assert key in values
        rendered = f"{values[key]}"
        assert re.search(rf"\\newcommand\{{\\{key}\}}", (INTEGRATION / "paper_numbers.tex").read_text(encoding="utf-8"))
        # only a distinctive value can be tested this way; a bare "0" appears everywhere
        if len(rendered) >= 5:
            assert rendered not in body, f"{key} appears as a typed literal in the manuscript"


def test_the_two_improvement_ratios_are_both_reported() -> None:
    body = manuscript()
    assert "\\EthreeRone" in body
    assert "\\EthreeRtwo" in body


def test_the_statistical_unit_is_stated_in_the_paper() -> None:
    body = manuscript()
    assert "Statistical unit" in body
    assert "\\EthreePSeed" in body


def test_new_material_matches_the_register_of_the_rest() -> None:
    if not STYLE.is_file():
        pytest.skip("style profile not available")
    document = json.loads(STYLE.read_text(encoding="utf-8"))
    narrative = document["SAEPS_manuscript_narrative.tex"]
    integrated = document["SAEPS_manuscript_integrated.tex"]

    added = integrated["sentences"] - narrative["sentences"]
    assert added > 50, added
    # the new sentences must not raise the negation rate of the document
    assert integrated["negation_per_sentence"] <= narrative["negation_per_sentence"] * 1.5
    assert integrated["disclaimer_per_sentence"] < 0.01
    # register targets carry over
    assert integrated["passive_per_sentence"] >= 0.30
    assert integrated["share_at_most_20_words"] >= 0.97
    assert integrated["first_person_per_sentence"] <= 0.02


def test_the_e7_stationarity_limitation_survives_into_the_paper() -> None:
    """The weakest result must not be softened on the way into the manuscript."""
    body = manuscript()
    assert "falls outside that range" in body or "remains open" in body
    generated = json.loads((INTEGRATION / "paper_numbers.json").read_text(encoding="utf-8"))
    assert generated["values"]["EsevenStationarity"] == 0
    assert generated["values"]["EsevenAgreement"] == 20
