import torch

from saeps.v35.second_order import second_order_reduced_decomposition
from saeps.v43.indicator import directional_first_order_correction


def test_directional_first_order_correction_matches_explicit_nonlinear_residual() -> None:
    theta = torch.tensor([0.4, -0.2], dtype=torch.float64)
    parameter = torch.tensor([0.3], dtype=torch.float64)

    def residual(current_theta: torch.Tensor, current_parameter: torch.Tensor) -> torch.Tensor:
        return torch.stack(
            [
                current_theta[0] ** 2 + current_theta[1] * current_parameter[0] - 0.1,
                torch.sin(current_theta[1]) + current_parameter[0] ** 2,
                current_theta[0] * current_parameter[0] + torch.exp(current_theta[1]) - 1.0,
            ]
        )

    gamma = 1.0e-3
    explicit = second_order_reduced_decomposition(residual, theta, parameter, gamma, 1.0e-12)
    directional = directional_first_order_correction(residual, theta, parameter, gamma)
    expected = explicit["first_order_reduced_correction"]
    observed = directional["first_order_reduced_correction"]
    relative = abs(observed - expected) / max(abs(expected), 1.0e-12)
    assert relative < 1.0e-10
    assert directional["forms_full_hessian"] is False

