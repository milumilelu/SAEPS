from __future__ import annotations

import numpy as np

from saeps.reliability_audit_v1.physical_solver import (
    finite_difference_sensitivity,
    heat_fd_temperature,
    refinement_difference,
)
from saeps.identifiability.profile_reference import heat_temperature_np


def test_independent_fd_solver_refines_toward_closed_form_solution() -> None:
    x = np.repeat(np.asarray([0.2, 0.4, 0.7]), 4)
    t = np.tile(np.asarray([0.02, 0.08, 0.2, 0.4]), 3)
    truth = heat_temperature_np(x, t, 0.6, 1.2, 1.0)
    coarse = heat_fd_temperature(x, t, k=0.6, C=1.2, interior_count=32).values
    fine = heat_fd_temperature(x, t, k=0.6, C=1.2, interior_count=128).values
    assert np.max(np.abs(fine - truth)) < np.max(np.abs(coarse - truth))
    assert np.max(np.abs(fine - truth)) < 2.0e-3
    assert refinement_difference(x, t, k=0.6, C=1.2, coarse_count=32, fine_count=64) > 0.0


def test_fd_sensitivity_has_expected_shape_and_finite_values() -> None:
    x = np.asarray([0.2, 0.4, 0.7])
    t = np.asarray([0.02, 0.2, 0.4])
    jac = finite_difference_sensitivity(x, t, k=0.6, C=1.2, amplitude=1.0, interior_count=64)
    assert jac.shape == (3, 3)
    assert np.isfinite(jac).all()
