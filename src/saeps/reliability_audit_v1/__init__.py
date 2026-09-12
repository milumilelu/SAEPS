"""RI-2 reliability-audit adapters.

This namespace is deliberately independent of historical SAEPS experiments.  The
heat-equation PINN pilot is a small, deterministic implementation intended for
analytically controlled B1--B4 checks and provenance-complete development runs.
"""

from .reliability import (
    GAMMA_ALPHA_GRID,
    DEFAULT_ERROR_TOLERANCE,
    DEFAULT_INFORMATION_FLOOR,
    DEFAULT_RANK_TOLERANCE,
    classify_record,
    effective_rank,
    gamma_path_from_jacobians,
    selective_metrics,
    target_log_error,
)

from .heat_pinn import (
    HeatPINNConfig,
    HeatPINNRun,
    HeatPINN,
    HeatObservation,
    generate_heat_observations,
    heat_pinn_residual,
    run_one,
    train_heat_pinn,
    run_heat_pinn,
)

__all__ = [
    "HeatPINNConfig",
    "HeatPINNRun",
    "HeatPINN",
    "HeatObservation",
    "generate_heat_observations",
    "heat_pinn_residual",
    "run_one",
    "train_heat_pinn",
    "run_heat_pinn",
    "GAMMA_ALPHA_GRID",
    "DEFAULT_ERROR_TOLERANCE",
    "DEFAULT_INFORMATION_FLOOR",
    "DEFAULT_RANK_TOLERANCE",
    "classify_record",
    "effective_rank",
    "gamma_path_from_jacobians",
    "selective_metrics",
    "target_log_error",
]
