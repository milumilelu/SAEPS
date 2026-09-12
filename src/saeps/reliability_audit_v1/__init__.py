"""RI-2 reliability-audit adapters.

This namespace is deliberately independent of historical SAEPS experiments.  The
heat-equation PINN pilot is a small, deterministic implementation intended for
analytically controlled B1--B4 checks and provenance-complete development runs.
"""

from .heat_pinn import (
    HeatPINNConfig,
    HeatPINNRun,
    HeatPINN,
    HeatObservation,
    generate_heat_observations,
    heat_pinn_residual,
    run_one,
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
    "run_heat_pinn",
]
