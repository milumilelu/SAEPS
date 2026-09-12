import json

import torch

from saeps.reliability_audit_v1 import HeatPINNConfig, generate_heat_observations, run_heat_pinn
from saeps.reliability_audit_v1.heat_pinn import weighted_residual


def test_heat_observation_and_residual_shapes():
    config = HeatPINNConfig(benchmark="B3", epochs=1, n_collocation=5, n_ic=4, n_bc=4)
    observation = generate_heat_observations(config)
    assert observation.x.shape == observation.t.shape == observation.values.shape
    assert observation.values.ndim == 1
    # A run exercises PDE autodiff and confirms the weighted residual is finite.
    run = run_heat_pinn(config)
    assert run.residual.ndim == 1
    assert torch.isfinite(run.residual).all()
    assert run.jacobian_state.shape[0] == run.residual.numel()
    assert run.jacobian_parameter.shape == (run.residual.numel(), 2)


def test_manifest_has_explicit_statuses_and_curvature_shapes(tmp_path):
    config = HeatPINNConfig(benchmark="B1", epochs=1, n_collocation=4, n_ic=4, n_bc=4, output_dir=str(tmp_path))
    run = run_heat_pinn(config)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert set(("COMPUTABLE", "FIT_QUALIFIED", "PROFILE_ELIGIBLE")) <= set(manifest["statuses"])
    assert manifest["F_raw_shape"] == [1, 1]
    assert manifest["F_gamma_shape"] == [1, 1]
    assert manifest["I_obs_shape"] == [1, 1]
    assert manifest["profile_implemented"] is False
    assert (tmp_path / "checkpoint.pt").exists()
