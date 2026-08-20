from __future__ import annotations

from saeps.v41.numerics import binding_curvature_gate


def test_parameter_pass_score_fail_keeps_curvature_gate_pass() -> None:
    result = binding_curvature_gate("PASS", "PASS", "SOLVER_FAILURE")
    assert result["CURVATURE_GATE"] == "PASS"
    assert result["nonbinding_diagnostics"]["score_solver_status"] == "SOLVER_FAILURE"


def test_binding_parameter_failure_fails_curvature_gate() -> None:
    result = binding_curvature_gate("NUMERICAL_FAILURE", "PASS", "PASS")
    assert result["CURVATURE_GATE"] == "SOLVER_FAILURE"

