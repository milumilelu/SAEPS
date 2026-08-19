from pathlib import Path
from saeps.config import load_config

ROOT=Path(__file__).resolve().parents[1]
def test_locked_robustness_workload_is_exact():
    config=load_config(ROOT/"configs/locked/robustness.yaml")
    assert config["seeds"]==[10,11,12,13,14]
    assert len(config["noise_levels"])*len(config["observation_fractions"])*len(config["seeds"])==45
    assert config["maximum_noise_sparsity_runs"]==45
