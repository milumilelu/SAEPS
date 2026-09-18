"""Tests for the L-BFGS stop-reason audit.

The audit exists because a budget flag derived only from ``n_iter >= max_iter`` reported
"not exhausted" while the function-evaluation budget was in fact binding.  These tests pin
the rule, the classification, and the honesty of the UNKNOWN bucket.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

AUDIT_DIR = Path(__file__).resolve().parents[1] / "outputs/posthoc/report_correction_20260918"


def rows(name: str) -> list[dict]:
    path = AUDIT_DIR / name
    if not path.is_file():
        pytest.skip(f"{name} not available")
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_max_eval_rule_matches_the_installed_default() -> None:
    """torch LBFGS sets max_eval = max_iter * 5 // 4 when it is not passed."""
    document = json.loads((AUDIT_DIR / "lbfgs_stop_reason_summary.json").read_text(encoding="utf-8"))
    assert "max_iter * 5 // 4" in document["max_eval_rule"]
    for row in rows("lbfgs_stop_reason_audit.csv"):
        assert int(row["max_eval"]) == int(row["max_iter"]) * 5 // 4


def test_e2_runs_are_classified_from_recorded_counters() -> None:
    data = [r for r in rows("lbfgs_stop_reason_audit.csv") if r["task"] == "E2"]
    assert len(data) == 30
    eval_bound = [r for r in data if r["binding_budget"] == "function_evaluation_budget"]
    assert eval_bound
    for row in eval_bound:
        assert int(row["recorded_closure_calls"]) >= int(row["max_eval"])
        assert int(row["recorded_n_iter"]) < int(row["max_iter"])


def test_the_old_flag_is_marked_misleading() -> None:
    """The field said False while the evaluation budget had in fact bound the run."""
    data = [r for r in rows("lbfgs_stop_reason_audit.csv") if r["task"] == "E2"]
    misleading = [r for r in data if r["flag_was_misleading"] == "True"]
    assert misleading
    for row in misleading:
        assert row["recorded_budget_exhausted_flag"] == "False"


def test_unclassifiable_cohorts_are_marked_unknown() -> None:
    """E3/E6/E7 recorded only accepted iterations, so no stop reason may be invented."""
    data = [r for r in rows("lbfgs_stop_reason_audit.csv") if r["task"] != "E2"]
    assert data
    for row in data:
        assert row["binding_budget"] == "UNKNOWN"
        assert row["stop_reason"].startswith("UNKNOWN")
        assert row["recorded_closure_calls"] in ("", None)


def test_instrumented_reproduction_is_labelled_as_a_new_measurement() -> None:
    document = json.loads((AUDIT_DIR / "lbfgs_stop_reason_summary.json").read_text(encoding="utf-8"))
    reproduction = document["instrumented_reproduction"]
    assert reproduction is not None
    assert "new measurement" in reproduction["label"]
    assert "not a reconstruction" in reproduction["label"]
    # the reproduction bound on the iteration budget while the recorded E2 runs bound on max_eval,
    # so the binding constraint must not be generalised from one case to the other
    assert reproduction["binding_budget"] == "iteration_budget"
