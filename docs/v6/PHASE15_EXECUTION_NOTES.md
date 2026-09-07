# Phase 1.5 execution 001

User authorization: “开始运行”, 2026-09-07. This supersedes the preparation-only
status for Phase 1.5, but does not authorize later layers. The original draft
config/protocol and source inventory remain unchanged. A separate execution
record freezes implementation, tests, config, input hashes and environment.

Implementation details fixed before scientific execution:

- B measures one warmup and five independent repeats for every candidate/start.
  C uses prefixes of these identical PCG trajectories; adaptive prefix selection
  reads only the indicator, never the oracle error. This avoids rerunning the
  same deterministic prefix while retaining the cost of each verification.
- Exact response, generalized spectra, target first hits and error identities are
  evaluated only after all timed repeats finish. Candidate execution has no
  oracle argument. Rows preserve recursive and explicit residuals separately.
- NumPy solves the Cholesky triangular systems. Dense allocated/preconditioner
  bytes are reported; actual native peak memory remains unavailable.
- Hybrid setup computes and charges its own defect; it does not receive an
  uncharged exact-Hessian action. Counts include actual vector columns.
- If the strict full-response residual is not reached by n_theta, B records
  SOLVER_FAILURE. Finite valid prefixes in C remain usable at their stated
  budgets; a numerical breakdown prefix itself is not accepted. Residual
  convergence before a requested budget is explicitly labeled.
- No preconditioner/setup is shared for free across starts or timing repeats.
  Shared outputs represent only the already-computed prefix of one trajectory.
- Existing unrelated user files/deletions remain untouched. All commits are
  local on the development branch; legacy failures and sync restriction remain.

Commands after implementation acceptance:

```powershell
.venv/Scripts/python.exe scripts/v6/run_phase15.py authorize
.venv/Scripts/python.exe scripts/v6/run_phase15.py A
.venv/Scripts/python.exe scripts/v6/run_phase15.py B
.venv/Scripts/python.exe scripts/v6/run_phase15.py C
.venv/Scripts/python.exe scripts/v6/build_phase15_report.py
```

Each scientific stage refuses to overwrite its output directory. Stage manifests
and independent Git commits track acceptance; scientific failures stay terminal.
