from pathlib import Path

from saeps.config import load_config
from saeps.v5.residual_scalability import REPEATS, RESIDUAL_COUNTS, STATE_COUNTS


ROOT = Path(__file__).resolve().parents[1]


def test_v5_residual_scalability_grid_is_real_and_fixed() -> None:
    config = load_config(ROOT / "configs/v5/residual_scalability_execution.yaml")
    assert STATE_COUNTS == [1001, 10001, 100001]
    assert RESIDUAL_COUNTS == [213, 853, 3413]
    assert REPEATS == [1, 2, 3]
    assert config["synthetic_residual_padding"] is False
    assert config["complexity_exponent_fit"] is False
    for residual_count, construction in config["residual_constructions"].items():
        pde = construction["pde_grid"][0] * construction["pde_grid"][1]
        data = construction["data_grid"][0] * construction["data_grid"][1]
        actual = pde + data + construction["initial_points"] + 2 * construction[
            "boundary_points_per_side"
        ]
        assert actual == residual_count
