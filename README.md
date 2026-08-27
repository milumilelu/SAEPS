# SAEPS: State-Adapted Effective Parameter Signals

> **Paper-facing evidence state: V5 final audit.** Historical v2--v4 protocols and reports remain available for provenance but are not the current paper-facing conclusion.

[Current V5 scientific audit](V5_FINAL_JCP_AUDIT_REPORT.md) · [Machine-readable repository validation](docs/evidence/v5_final_validation.json) · [Reproduction and validation](REPRODUCIBILITY.md) · [Historical protocols](docs/HISTORICAL_PROTOCOLS.md)

SAEPS is a finite-damping reduced Gauss--Newton curvature diagnostic for trained inverse physics-informed neural networks (PINNs). At a fixed checkpoint, it removes residual directions locally explainable by neural-state adaptation and estimates the remaining parameter curvature. Exact-reference accuracy is validated on compact one-dimensional inverse-PINN benchmarks.

## What SAEPS computes

For residual Jacobians with respect to neural state and physical parameters, SAEPS applies a damped state-space elimination. The matrix-free implementation in `src/saeps/core.py` uses JVP/VJP operations and iterative solves rather than constructing the full neural-state Jacobian or state curvature matrix. The diagnostic is local, finite-damping, checkpoint-dependent, and residual-space based.

## Main validated result

In scalar exact-reference comparisons for Burgers and Allen--Cahn, SAEPS-GN is closer than raw frozen-state curvature to the exact local finite-damping reduced Hessian:

- Burgers: 15 planned, 12 binding-valid; all 12/12 valid comparisons favor SAEPS.
- Allen--Cahn: 10 planned, 9 binding-valid; all 9/9 valid comparisons favor SAEPS.

This does not establish exact Hessian recovery, global identifiability, posterior uncertainty, or nonlinear finite-displacement profile equivalence.

## Evidence levels

| Evidence | Status | Permitted interpretation |
|---|---|---|
| Burgers scalar comparative | `SUPPORTED` | Primary exact-reference evidence; 12/15 planned wins and 12/12 valid paired wins. |
| Allen--Cahn scalar replication | `SUPPORTED` | Independent replication; 9/10 planned wins and 9/9 valid paired wins. |
| Noise/sparsity exact anchors | Secondary support | 14/15 planned anchors were valid; all 14 valid anchors favor SAEPS. |
| Finite-gamma sweep | Descriptive | Sensitivity evidence only; the smallest tested damping has retained failures. |
| Exact fixed-state decomposition | `POSTHOC_NONBINDING` | Mechanism analysis of 21 reconstructed valid centers; not confirmatory. |
| Undamped variable projection | `POSTHOC_NONBINDING` | Baseline/mechanism analysis without a generally admissible exact gamma-zero reference. It does not establish superiority over VP0. |
| Two-parameter geometry | `INCONCLUSIVE` | 8/10 binding-valid and 8/8 valid pairs favor SAEPS, but the preregistered 9/10 availability gate was not met. |
| Whitening stabilizer sensitivity | `POSTHOC_NONBINDING` | The observed paired direction is preserved at all 8 valid checkpoints for relative stabilizers `1e-8`, `1e-10`, and `1e-12`; this is not mathematical invariance. |
| Nonlinear finite-displacement profile | `NOT_SUPPORTED` | The nonlinear-profile-equivalence claim is not supported. |
| Controlled tangent-overlap cohort claim | `NOT_SUPPORTED` | The stronger cohort-level monotonic claim failed its planned-denominator gate. |
| Scalability | Engineering/cost only | The `n_theta=100001` study establishes matrix-free computational feasibility, not large-network curvature accuracy. |
| Width-32 architecture | Not successfully tested | No frozen run supplied a valid stationary center for curvature comparison. |

## Repository structure

- `src/saeps/`: package implementation, including explicit and matrix-free operators.
- `configs/`: locked protocols, execution freezes, and post-hoc analysis configurations.
- `outputs/runs/`: frozen raw records and manifests, including invalid and failed runs.
- `outputs/posthoc/`: derived post-hoc records that retain their nonbinding classifications.
- `docs/evidence/`: machine-readable aggregates and human-readable evidence reports.
- `paper_artifacts/`: generated paper-facing tables, figures, supplementary data, and manifests.
- `docs/archive/`: historical planning and manuscript snapshots retained for provenance.

## Installation

The locked environment uses CPython 3.12.13 on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
```

## Reproducing repository validation

Ordinary reviewer audit does not require retraining or rerunning locked confirmation experiments:

```powershell
pytest -q
python scripts/00_smoke_test.py --output-root "$env:TEMP/saeps-smoke"
python scripts/01_validate_core.py --output-root "$env:TEMP/saeps-core"
python scripts/04_validate_profile.py --output-root "$env:TEMP/saeps-profile"
python scripts/validate_repository.py
python scripts/validate_v5_repository.py
```

See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for the raw-to-aggregate audit path and platform details. Validation-only output must use a temporary directory and must never overwrite checked-in scientific records.

## Reproducing paper-facing aggregates

Start with `docs/evidence/v5_final_audit.json`, follow each aggregate's `source_records` entries to `outputs/runs/`, and verify publication artifacts against the manifests in `paper_artifacts/`. All planned denominators and failed/invalid records remain visible. Post-hoc analyses are separately identified under `docs/evidence/` and `outputs/posthoc/`.

## Provenance and frozen evidence

The frozen primary evidence baseline is commit `cf76ffe85a78c994351e50b97d013d33a0f01f85`. The exact-decomposition, variable-projection, and whitening-sensitivity heads are respectively `39343bc32ae38ea2ad118011105cf4cb2c2f3241`, `c868127b1bcc52598dcf41a8822a7d58fed38635`, and `0428a1f8891fd478fb53c18508aff3c0506fd57b`. Their histories are integrated with merge commits so the original SHAs remain reachable.

## Current scope and limitations

The validated comparisons are local and use compact one-dimensional inverse-PINN benchmarks. Scalability results concern engineering feasibility. Failed stationarity gates, unavailable exact references, and negative scientific gates are retained rather than filtered. Historical protocols are indexed in [docs/HISTORICAL_PROTOCOLS.md](docs/HISTORICAL_PROTOCOLS.md).

## Citation

Citation metadata are in [CITATION.cff](CITATION.cff). No DOI is currently claimed; release/archival metadata should be updated only after a DOI is issued.

## License

This repository is released under the BSD 3-Clause License. See [LICENSE](LICENSE) for details. Third-party Python dependencies retain their own licenses and are not redistributed as source in this repository.
