from pathlib import Path

from saeps.smoke import SmokeSettings, run_smoke


def test_real_tiny_pinn_checkpoint_roundtrip(tmp_path: Path) -> None:
    settings = SmokeSettings(
        seed=9,
        hidden_width=10,
        adam_steps=400,
        learning_rate=0.01,
        collocation_points=32,
        initial_condition_weight=10.0,
        max_state_rmse=0.06,
        max_roundtrip_abs_error=1.0e-12,
    )
    config = {"schema_version": 1, "runtime": {"dtype": "float64"}, "smoke": settings.__dict__}
    metadata = run_smoke(settings, tmp_path / "outputs", ".", config)
    assert metadata["status"] == "PASS"
    assert metadata["trained_metrics"]["state_rmse"] <= settings.max_state_rmse
    assert metadata["roundtrip"]["max_abs_error"] <= settings.max_roundtrip_abs_error
    run_dir = tmp_path / "outputs" / metadata["run_id"]
    assert (run_dir / "checkpoint.pt").is_file()
    assert (run_dir / "metadata.json").is_file()
    assert (run_dir / "validation.json").is_file()

