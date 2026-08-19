from saeps.v34.pipeline import _solver_hierarchy


def test_curvature_and_score_solver_gates_are_independent() -> None:
    explicit = {
        "Fse": [[10.0]],
        "right_hand_side_relative_normal_residuals": [1.0e-14, 1.0e-5],
        "objective_projection_identity_relative_error": 1.0e-14,
    }
    matrix_free = {
        "standard_cg": {
            "Fse": [[10.0 + 1.0e-8]],
            "converged": [True, False],
            "verified_relative_residuals": [1.0e-10, 1.0e-5],
            "iterations": [20, 100],
        },
        "jacobi_pcg": {
            "Fse": [[10.1]],
            "converged": [False, False],
            "verified_relative_residuals": [1.0e-3, 1.0e-2],
            "iterations": [100, 100],
        },
    }
    lsqr = {
        "Fse": [[10.0 + 2.0e-8]],
        "converged": [True, False],
        "relative_normal_residuals": [1.0e-9, 2.0e-5],
        "iterations": [15, 100],
    }
    specification = {
        "explicit_parameter_relative_normal_residual": 1.0e-10,
        "explicit_objective_identity_tolerance": 1.0e-10,
        "parameter_residual_acceptance": 1.0e-8,
        "curvature_relative_acceptance": 1.0e-6,
    }

    hierarchy = _solver_hierarchy(explicit, matrix_free, lsqr, specification)

    assert hierarchy["CURVATURE_SOLVER_GATE"]["status"] == "PASS"
    assert hierarchy["SCORE_SOLVER_GATE"]["status"] == "SOLVER_FAILURE"
    assert hierarchy["PRECONDITIONER_DIAGNOSTIC"]["status"] == "SOLVER_FAILURE"
    assert hierarchy["SCORE_SOLVER_GATE"]["binding"] is False
