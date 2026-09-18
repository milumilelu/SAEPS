"""Tests for the narrative pass over the manuscript.

The brief was: reduce defensiveness, keep the passive register, keep every sentence at or
under twenty words, and change as little as possible.  Each is checkable, so none of them
rests on impression.

Two failure modes are pinned in particular.  First, a rewrite must never delete a
scientific boundary -- an earlier draft of this pass silently dropped the sentence saying
that ordering preservation carries no general guarantee, and the content test below is
what caught it.  Second, a rewrite must never invent a cross-reference; four were
introduced that way and then removed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

NAMESPACE = Path(__file__).resolve().parents[1]
STYLE = NAMESPACE / "outputs/posthoc/narrative_pass/style_profile_before_after.json"
CHANGELOG = NAMESPACE / "outputs/posthoc/narrative_pass/narrative_pass_changelog.json"
REPO = Path(__file__).resolve().parents[3]
BEFORE = REPO / "paper/revise/SAEPS_manuscript_revised.tex"
AFTER = REPO / "paper/revise/SAEPS_manuscript_narrative.tex"

LABEL = re.compile(r"\\label\{([^}]*)\}")
REF = re.compile(r"\\(?:ref|eqref)\{([^}]*)\}")

# statements that carry a boundary and must survive the pass in some form
BOUNDARIES = (
    r"0\) of \(5\) planned centers",
    r"\(8\) of \(10\) planned centers",
    "recorded as unavailable",
    "falls outside that range",
    "at or below",
    "reported separately",
    "as a separate diagnostic",
)


@pytest.fixture(scope="module")
def style() -> dict:
    if not STYLE.is_file():
        pytest.skip("style profile not available")
    return json.loads(STYLE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def changelog() -> dict:
    if not CHANGELOG.is_file():
        pytest.skip("changelog not available")
    return json.loads(CHANGELOG.read_text(encoding="utf-8"))


def test_defensiveness_fell_sharply(style: dict) -> None:
    before = style["SAEPS_manuscript_revised.tex"]
    after = style["SAEPS_manuscript_narrative.tex"]
    assert after["disclaimer_per_sentence"] == 0.0
    assert after["negation_per_sentence"] < 0.25 * before["negation_per_sentence"]
    assert after["concessive_per_sentence"] < before["concessive_per_sentence"]


def test_the_other_register_targets_are_preserved(style: dict) -> None:
    before = style["SAEPS_manuscript_revised.tex"]
    after = style["SAEPS_manuscript_narrative.tex"]
    assert after["passive_per_sentence"] >= 0.30
    assert after["first_person_per_sentence"] <= 0.02
    assert after["share_at_most_20_words"] >= 0.97
    assert after["mean_words_per_sentence"] <= before["mean_words_per_sentence"] + 0.5


def test_the_edit_stays_minimal(style: dict) -> None:
    before = style["SAEPS_manuscript_revised.tex"]
    after = style["SAEPS_manuscript_narrative.tex"]
    assert abs(after["sentences"] - before["sentences"]) <= 3


def test_every_replacement_landed_exactly_once(changelog: dict) -> None:
    assert changelog["applied"] == changelog["planned"]
    assert changelog["not_found"] == []
    assert changelog["ambiguous"] == []
    assert changelog["replacements_over_twenty_words"] == []
    assert len(changelog["changes"]) == changelog["planned"]


def test_no_replacement_is_merely_a_deletion(changelog: dict) -> None:
    """A boundary may be rephrased, but not dropped."""
    for change in changelog["changes"]:
        before_words = len(change["before"].split())
        after_words = len(change["after"].split())
        assert after_words >= 0.7 * before_words, change


def test_scientific_boundaries_survive_in_the_manuscript() -> None:
    if not AFTER.is_file():
        pytest.skip("narrative manuscript not present")
    body = AFTER.read_text(encoding="utf-8")
    for marker in BOUNDARIES:
        assert marker in body, marker


def test_no_dangling_cross_reference_was_introduced() -> None:
    if not (BEFORE.is_file() and AFTER.is_file()):
        pytest.skip("manuscripts not present")

    def dangling(path: Path) -> set[str]:
        text = path.read_text(encoding="utf-8")
        return set(REF.findall(text)) - set(LABEL.findall(text))

    assert dangling(AFTER) <= dangling(BEFORE), sorted(dangling(AFTER) - dangling(BEFORE))


def test_false_positives_were_left_alone(changelog: dict) -> None:
    assert len(changelog["excluded_false_positives"]) == 2
