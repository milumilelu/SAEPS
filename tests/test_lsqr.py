import torch

from saeps.solvers import least_squares_qr


def test_augmented_lsqr_matches_direct_lstsq() -> None:
    generator = torch.Generator().manual_seed(331)
    matrix = torch.randn(12, 5, dtype=torch.float64, generator=generator)
    gamma = 0.07
    augmented = torch.cat(
        [matrix, torch.sqrt(torch.tensor(gamma, dtype=torch.float64)) * torch.eye(5)],
        dim=0,
    )
    right_hand_side = torch.randn(12, dtype=torch.float64, generator=generator)
    augmented_rhs = torch.cat([right_hand_side, torch.zeros(5, dtype=torch.float64)])

    result = least_squares_qr(
        lambda vector: augmented @ vector,
        lambda vector: augmented.T @ vector,
        augmented_rhs,
        solution_size=5,
        tolerance=1.0e-12,
        max_iterations=50,
    )
    direct = torch.linalg.lstsq(augmented, augmented_rhs).solution

    assert result.converged
    assert result.relative_normal_residual <= 1.0e-12
    assert torch.allclose(result.solution, direct, rtol=1.0e-10, atol=1.0e-11)
