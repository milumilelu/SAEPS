# Cumulative measured cost

{
  "e0_wall_seconds": 1.4812168000498787,
  "e0_cpu_seconds": 0.40625,
  "historical_reconstruction_seconds": 3801.8915909999632,
  "historical_original_training_total": null,
  "new_training_seconds": 0,
  "new_profile_seconds": 0,
  "gn_solve_seconds": 0.001128900097683072,
  "spectrum_seconds": 0.015298699960112572,
  "reference_seconds": 0.0006612997967749834,
  "adaptive_seconds": 0.0972487999824807,
  "A_matvec_count": 3261,
  "jvp_count": 0,
  "vjp_count": 0,
  "hvp_count": 0,
  "audit_seconds": 8.153892899979837,
  "test_seconds": 10.969645600067452,
  "current_recorded_compute_seconds": 43.54764920009564,
  "failed_audit_seconds": 1.7435761,
  "failed_byte_repair_syntax_command_seconds": 0.5267703,
  "validator_attempts": [
    {
      "seconds": 10.023151900037192,
      "exit_code": 1
    },
    {
      "seconds": 10.180077399942093,
      "exit_code": 0
    }
  ],
  "stage_audit_and_resume_seconds": 0.4693182000191882
}

Historical reconstruction costs are inherited (not newly incurred). Original training total is unknown. Includes failed audit, failed repair command, both repository validator attempts, unit tests, E0, result audit and resume. Interactive inspection latency not exhaustively instrumented. No new training/profile; actual E0 JVP/VJP/HVP=0. Dense eigenspectrum and correction are charged. E0 refinement budget is 100 PCG iterations, up to 201 A products/RHS including explicit defect checks, not the proposed E1 100-product cap. This E0 diagnostic budget must not be represented as the future E1 budget. No efficiency conclusion is based on those differing budgets.
