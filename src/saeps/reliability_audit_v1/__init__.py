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
    classify_saeps_only,
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

from .corrections import (
    DecisionMode,
    FIM_ASSISTED_SAEPS,
    FIMAssistedSaepsInput,
    ORACLE_FIM_REFERENCE,
    OracleFIMReferenceInput,
    PHYSICAL_FIM_PLUGIN,
    PhysicalFIMPluginInput,
    SAEPS_ONLY,
    SAEPSOnlyInput,
    SaepsOnlyInput,
    check_log_parameter_bounds,
    evaluate_refinement,
    make_side_effect_free_closure,
    normalized_heat_residual,
    normalized_heat_residual_from_parameters,
    normalized_quadrature_weights,
    weighted_residual_mean_square,
    refinement_threshold,
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
    "classify_saeps_only",
    "effective_rank",
    "gamma_path_from_jacobians",
    "selective_metrics",
    "target_log_error",
    "DecisionMode",
    "SAEPS_ONLY",
    "PHYSICAL_FIM_PLUGIN",
    "ORACLE_FIM_REFERENCE",
    "FIM_ASSISTED_SAEPS",
    "SaepsOnlyInput",
    "SAEPSOnlyInput",
    "PhysicalFIMPluginInput",
    "OracleFIMReferenceInput",
    "FIMAssistedSaepsInput",
    "normalized_heat_residual",
    "normalized_heat_residual_from_parameters",
    "normalized_quadrature_weights",
    "weighted_residual_mean_square",
    "check_log_parameter_bounds",
    "make_side_effect_free_closure",
    "refinement_threshold",
    "evaluate_refinement",
]
