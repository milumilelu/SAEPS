import torch

from saeps.v35.second_order import second_order_reduced_decomposition


def test_shapley_blocks_reproduce_exact_minus_gn() -> None:
    dtype = torch.float64
    theta = torch.tensor([0.3, -0.2], dtype=dtype)
    parameter = torch.tensor([0.15], dtype=dtype)

    def residual(state: torch.Tensor, physical: torch.Tensor) -> torch.Tensor:
        return torch.stack(
            [
                state[0] ** 2 + physical[0] * state[1] - 0.2,
                torch.sin(state[1]) + physical[0] ** 2 + 0.1 * state[0],
                state[0] * state[1] * physical[0] + 0.3,
            ]
        )

    result = second_order_reduced_decomposition(
        residual, theta, parameter, gamma=0.2, denominator_floor=1.0e-12
    )

    assert result["shapley_reproduction_relative_error"] < 1.0e-12
    assert abs(
        result["shapley_sum"]
        - (result["Hred_exact_gamma"] - result["Fse_GN"])
    ) < 1.0e-12
    assert result["comparative_estimand"]["D_raw_minus_SAEPS"] == (
        result["comparative_estimand"]["E_raw"]
        - result["comparative_estimand"]["E_SAEPS"]
    )
