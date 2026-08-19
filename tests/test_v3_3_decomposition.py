import torch

from saeps.autodiff import ResidualLinearization
from saeps.v33.pipeline import (
    _augmented_lsqr_reference,
    _direct_augmented_reference,
    _matrix_free_normal_solvers,
)


def test_four_node_solver_layer_separates_and_matches_references() -> None:
    generator = torch.Generator().manual_seed(332)
    state_matrix = torch.randn(14, 5, dtype=torch.float64, generator=generator)
    parameter_matrix = torch.randn(14, 1, dtype=torch.float64, generator=generator)
    offset = torch.randn(14, dtype=torch.float64, generator=generator)
    theta = torch.randn(5, dtype=torch.float64, generator=generator)
    parameter = torch.tensor([0.2], dtype=torch.float64)

    def residual_function(state: torch.Tensor, physical: torch.Tensor) -> torch.Tensor:
        return state_matrix @ state + parameter_matrix @ physical + offset

    linearization = ResidualLinearization(residual_function, theta, parameter)
    residual = linearization.residual()
    jacobian_theta, jacobian_parameter = linearization.explicit_jacobians()
    jacobian_parameter_mf = linearization.parameter_columns_matrix_free()
    gamma = 0.08
    specification = {
        "normal_equation_tolerance": 1.0e-12,
        "acceptance_relative_residual": 1.0e-10,
        "max_iterations": 100,
        "explicit_relative_normal_residual": 1.0e-10,
        "explicit_objective_identity_tolerance": 1.0e-10,
        "lsqr_relative_normal_residual": 1.0e-10,
        "lsqr_curvature_relative_tolerance": 1.0e-9,
    }

    explicit = _direct_augmented_reference(
        jacobian_theta,
        jacobian_parameter,
        residual,
        gamma,
        specification,
    )
    matrix_free = _matrix_free_normal_solvers(
        linearization,
        jacobian_parameter_mf,
        residual,
        gamma,
        specification,
    )
    explicit_value = explicit["Fse"][0][0]
    lsqr = _augmented_lsqr_reference(
        linearization,
        jacobian_parameter_mf,
        residual,
        gamma,
        specification,
        explicit_value,
    )

    assert explicit["status"] == "PASS"
    assert matrix_free["standard_cg"]["status"] == "PASS"
    assert matrix_free["jacobi_pcg"]["status"] == "PASS"
    assert lsqr["status"] == "PASS"
    assert abs(matrix_free["standard_cg"]["Fse"][0][0] - explicit_value) < 1.0e-9
    assert abs(lsqr["Fse"][0][0] - explicit_value) < 1.0e-9
