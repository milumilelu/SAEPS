"""Tests for the independent analytic R3 profile reference."""

from __future__ import annotations

import numpy as np

from saeps.identifiability.profile_reference import (
    DEFAULT_C,
    DEFAULT_K,
    frozen_profile_grid,
    generate_analytic_observations,
    profile_heat_observation,
)


def test_frozen_profile_grid_is_declared_and_contains_reference():
    grid = frozen_profile_grid()
    assert grid.size == 31
    assert np.all(np.diff(grid) > 0)
    assert np.isclose(grid[15], DEFAULT_K)
    assert np.isclose(grid[0], DEFAULT_K / 3.0)
    assert np.isclose(grid[-1], DEFAULT_K * 3.0)


def test_flat_profiles_reveal_b3_and_b4_compensation_without_truth_fit():
    b3 = profile_heat_observation(generate_analytic_observations("B3", noise_rho=0.0))
    b4 = profile_heat_observation(generate_analytic_observations("B4", noise_rho=0.0))
    assert b3["flat_profile"] is True
    assert b3["profile_status"] == "FLAT"
    assert b3["objective_span_half_chi2"] < 1.0e-6
    assert b4["flat_profile"] is True
    assert b4["profile_status"] == "FLAT"
    assert b4["objective_span_half_chi2"] < 1.0e-6

    # B3's profiled nuisance follows the exact alpha=k/C combination.
    middle = b3["points"][15]
    assert np.isclose(middle["nuisance"]["C"], DEFAULT_C)
    edge = b3["points"][0]
    assert np.isclose(edge["nuisance"]["C"], 2.0 * edge["scan_value"], rtol=1.0e-6)


def test_two_time_and_flux_interventions_create_informative_profiles():
    b5 = profile_heat_observation(generate_analytic_observations("B5", noise_rho=0.0))
    b6 = profile_heat_observation(generate_analytic_observations("B6", noise_rho=0.0))
    assert b5["flat_profile"] is False
    assert b6["flat_profile"] is False
    assert b5["minimum_index"] == 15
    assert b6["minimum_index"] == 15
    assert b5["objective_span_half_chi2"] > 1.0
    assert b6["objective_span_half_chi2"] > 1.0


def test_early_time_b2_profile_is_weak_but_not_structurally_flat():
    profile = profile_heat_observation(generate_analytic_observations("B2", data_seed=10))
    values = np.asarray([row["objective_half_chi2"] for row in profile["points"]])
    assert profile["flat_profile"] is False
    assert profile["profile_status"] == "PASS"
    assert profile["grid_rule"].startswith("31 log-spaced")
    assert profile["scan_domain"]["closed"] is True
    assert profile["nuisance_domain"]["closed"] is True
    assert profile["branch_status"] == "SINGLE_PRINCIPAL"
    assert np.isfinite(values).all()
    # The early-time design carries much less curvature than B1 at 1% noise.
    b1 = profile_heat_observation(generate_analytic_observations("B1", data_seed=10))
    assert profile["objective_span_half_chi2"] < b1["objective_span_half_chi2"]


def test_early_time_b2_profile_is_present_but_practically_shallow():
    b1 = profile_heat_observation(generate_analytic_observations("B1", noise_rho=0.0))
    b2 = profile_heat_observation(generate_analytic_observations("B2", noise_rho=0.0))
    assert b2["profile_status"] == "PASS"
    assert b2["flat_profile"] is False
    assert b2["objective_span_half_chi2"] < b1["objective_span_half_chi2"]


def test_profile_is_reproducible_for_noisy_data():
    first = profile_heat_observation(generate_analytic_observations("B6", data_seed=42))
    second = profile_heat_observation(generate_analytic_observations("B6", data_seed=42))
    assert first == second
