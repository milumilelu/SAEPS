"""Tests for the non-affine E3 benchmark and the E2 curvature-drift recomputation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import e3_saturation as E  # noqa: E402
import repo_adapter as A  # noqa: E402

REPO = A.repo_root()


@pytest.fixture(scope="module")
def config() -> dict:
    try:
        commit = A.resolve_commit(REPO, A.DEFAULT_REF)
    except Exception:  # pragma: no cover - environment dependent
        pytest.skip("frozen evidence tag unavailable")
    return E.load_config(REPO, commit)


@pytest.fixture(scope="module")
def prepared(config: dict) -> dict:
    return E.prepare(config, int(config["development_data_seeds"][0]), 0.0)


def test_source_satisfies_pde_at_truth(prepared: dict, config: dict) -> None:
    points = prepared["_points"]
    u = E.truth(points.pde_x, points.pde_t)
    u_t, u_xx = E.truth_derivatives(points.pde_x, points.pde_t)
    forcing = E.source(
        points.pde_x, points.pde_t, config["diffusion"], config["rho_known"],
        config["kappa_truth"],
    )
    residual = (
        u_t
        - config["diffusion"] * u_xx
        - config["rho_known"] * u / (1.0 + config["kappa_truth"] * u)
        - forcing
    )
    assert float(residual.abs().max().item()) < 1.0e-12


def test_manufactured_solution_is_periodic(prepared: dict) -> None:
    t = prepared["_points"].boundary_t
    left = torch.zeros_like(t)
    right = torch.ones_like(t)
    assert float((E.truth(left, t) - E.truth(right, t)).abs().max().item()) < 1.0e-14
    lx = left.clone().requires_grad_(True)
    rx = right.clone().requires_grad_(True)
    left_slope = torch.autograd.grad(E.truth(lx, t).sum(), lx)[0]
    right_slope = torch.autograd.grad(E.truth(rx, t).sum(), rx)[0]
    assert float((left_slope - right_slope).abs().max().item()) < 1.0e-14


def test_truth_stays_away_from_zero(prepared: dict) -> None:
    points = prepared["_points"]
    assert float(E.truth(points.pde_x, points.pde_t).min().item()) > 0.7


def test_analytic_branches_match_autograd(config: dict) -> None:
    width = int(config["architecture"][1])
    generator = torch.Generator(device="cpu").manual_seed(7)
    theta = 0.3 * torch.randn(4 * width + 1, dtype=torch.float64, generator=generator)
    x = torch.rand(48, dtype=torch.float64, generator=generator)
    t = 0.4 * torch.rand(48, dtype=torch.float64, generator=generator)
    analytic = E.evaluate(theta, x, t, width)
    autograd = E.evaluate_autograd(theta, x, t, width)
    for left, right in zip(analytic, autograd):
        assert float((left - right).abs().max().item()) < 1.0e-13


def test_nonaffine_identity_holds(config: dict, prepared: dict) -> None:
    """H_ll - G_ll - g_l equals kappa^2 sum r d2r/dkappa2 exactly."""
    width = int(config["architecture"][1])
    generator = torch.Generator(device="cpu").manual_seed(11)
    theta = 0.3 * torch.randn(4 * width + 1, dtype=torch.float64, generator=generator)
    lam = torch.log(torch.tensor([1.2], dtype=torch.float64))
    result = E.nonaffine_identity(theta, lam, prepared["_points"], prepared)
    assert abs(result["left_H_minus_G_minus_g"] - result["right_kappa2_sum_r_d2r"]) < 1.0e-10
    assert result["relative_difference"] < 1.0e-12


def test_nonaffine_term_is_not_small_for_this_benchmark(config: dict, prepared: dict) -> None:
    """The affine prediction must fail here, unlike the affine benchmarks used by E1."""
    width = int(config["architecture"][1])
    generator = torch.Generator(device="cpu").manual_seed(11)
    theta = 0.3 * torch.randn(4 * width + 1, dtype=torch.float64, generator=generator)
    lam = torch.log(torch.tensor([1.2], dtype=torch.float64))
    result = E.nonaffine_identity(theta, lam, prepared["_points"], prepared)
    affine_gap = abs(result["log_identity_left_H_minus_G"] - result["affine_prediction_g_l"])
    assert affine_gap > 1.0
    assert abs(result["right_kappa2_sum_r_d2r"]) > 1.0


def test_residual_count_and_state_size(config: dict) -> None:
    assert E.residual_count(config) == 368
    assert 4 * int(config["architecture"][1]) + 1 == 65


def test_noise_is_paired_across_levels(config: dict) -> None:
    """The same standard-normal draw must drive both noise levels."""
    low = E.prepare(config, 916001, 0.0)
    high = E.prepare(config, 916001, 0.02)
    assert torch.equal(low["_points"].data_x, high["_points"].data_x)
    clean = E.truth(high["_points"].data_x, high["_points"].data_t)
    assert torch.equal(low["_observed_data"], clean)
    assert not torch.equal(high["_observed_data"], clean)


def test_curvature_drift_reproduces_historical_matrices() -> None:
    """The drift route must rebuild the historical F_raw and H_red, not just the points."""
    import e2_curvature_drift as D

    commit = A.resolve_commit(REPO)
    ctx = D.context(REPO, commit, 215)
    historical = A.read_json(
        REPO, commit, "outputs/runs/v5/two_parameter/confirmation/seed_215/result.json"
    )
    gamma = float(historical["gamma"])
    level = D.curvature_at(ctx, ctx["theta0"], gamma)
    raw_reference = torch.tensor(historical["F_raw"], dtype=torch.float64)
    gold_reference = torch.tensor(historical["H_red_exact_gamma"], dtype=torch.float64)
    assert torch.allclose(level["raw"], raw_reference, rtol=0.0, atol=1e-10)
    assert torch.allclose(level["gold"], gold_reference, rtol=0.0, atol=1e-10)


def test_gamma_rule_matches_historical_value() -> None:
    import e2_curvature_drift as D

    commit = A.resolve_commit(REPO)
    ctx = D.context(REPO, commit, 215)
    historical = A.read_json(
        REPO, commit, "outputs/runs/v5/two_parameter/confirmation/seed_215/result.json"
    )
    linearization = ctx["linearization_cls"](
        ctx["residual_function"], ctx["theta0"], ctx["lam0"]
    )
    jt, _ = linearization.explicit_jacobians()
    gamma = 1.0e-8 * float(torch.linalg.svdvals(jt)[0].square())
    assert abs(gamma - float(historical["gamma"])) / float(historical["gamma"]) < 1.0e-12


def test_invalid_centres_have_no_historical_gamma() -> None:
    """The frozen pipeline computes the diagnostic gamma only in its valid branch."""
    commit = A.resolve_commit(REPO)
    for seed in (219, 221):
        record = A.read_json(
            REPO, commit, f"outputs/runs/v5/two_parameter/confirmation/seed_{seed}/result.json"
        )
        assert record.get("gamma") is None
        assert record.get("binding_valid") is False


def test_frozen_protocol_matches_live_files() -> None:
    """The freeze must be checkable: live hashes have to match the recorded ones."""
    import hashlib
    import json

    snapshot = Path(__file__).resolve().parents[1] / "reports/E3_FROZEN_PROTOCOL.json"
    if not snapshot.is_file():
        pytest.skip("protocol not frozen yet")
    document = json.loads(snapshot.read_text(encoding="utf-8"))
    namespace = snapshot.parents[1]
    for name, expected in document["frozen_files"].items():
        actual = hashlib.sha256((namespace / name).read_bytes()).hexdigest()
        assert actual == expected, f"{name} changed after freezing"
    assert document["heldout"]["authorized"] is True


def test_heldout_guard_rejects_before_freeze(monkeypatch) -> None:
    """A missing snapshot must stop the held-out cohort rather than run unguarded."""
    import e3_saturation as E

    monkeypatch.setattr(E, "FROZEN_SNAPSHOT", Path("does_not_exist.json"))
    with pytest.raises(RuntimeError, match="no frozen protocol snapshot"):
        E.verify_frozen_snapshot()


def test_budget_convergence_monotone_in_median() -> None:
    """Median E_SAEPS should fall as the polish budget grows."""
    import json

    path = (
        Path(__file__).resolve().parents[1]
        / "outputs/development/e3_budget_convergence.json"
    )
    if not path.is_file():
        pytest.skip("convergence summary not available")
    document = json.loads(path.read_text(encoding="utf-8"))
    medians = [document["per_budget"][str(b)]["median_E_SAEPS"] for b in (10000, 30000, 100000)]
    assert medians[0] > medians[1] > medians[2]
    assert document["per_budget"]["100000"]["valid"] == 8


def test_heldout_aggregate_is_complete_and_paired() -> None:
    """Regression guard: the aggregate must read typed rows, not raw CSV strings.

    Filtering the raw string rows against float noise levels silently produced empty
    groups and zero wins, so the noise breakdown and the win count are asserted here.
    """
    import json

    path = Path(__file__).resolve().parents[1] / "outputs/heldout/e3/e3_aggregate.json"
    if not path.is_file():
        pytest.skip("held-out aggregate not available")
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["statistical_unit"] == "data_seed"
    assert document["fits_valid"] == document["fits_planned"] == 24
    assert document["data_seeds_complete"] == document["data_seeds_planned"] == 6
    assert document["invalid_fits"] == []
    across = document["across_data_seeds"]
    assert across["wins"] == across["non_ties"] == 24
    assert across["median_E_SAEPS"] < across["median_E_raw"]
    assert across["ratio_of_medians_R1"] > 1000
    assert across["median_paired_ratio_R2"] > 1000
    for level, block in document["by_noise_level"].items():
        assert block["fits_valid"] == 12, level
        assert block["wins"] == 12, level
    for entry in document["within_data_seed"]:
        assert entry["fits_valid"] == entry["fits_planned"] == 4
        assert entry["wins"] == 4
