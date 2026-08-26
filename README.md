# SAEPS: State-Adapted Effective Parameter Signals

> **Paper-facing evidence state: V5 final audit.** The repository-level scientific conclusion is `PARTIALLY_SUPPORTED`; historical v2–v4 protocol documents are preserved for provenance and are not the current paper-facing adjudication.

[Current V5 scientific audit](V5_FINAL_JCP_AUDIT_REPORT.md) · [Machine-readable final repository validation](docs/evidence/v5_final_validation.json) · [Reproduction and validation](REPRODUCIBILITY.md) · [Historical protocols](docs/HISTORICAL_PROTOCOLS.md)

SAEPS studies **local finite-damping reduced parameter curvature** in inverse physics-informed neural networks (PINNs). At a fixed trained checkpoint, it asks whether eliminating local neural-state directions produces a parameter-curvature estimate closer than raw frozen-state curvature to the exact local finite-damping reduced Hessian.

The supported paper claim is deliberately narrow: in scalar exact-reference comparisons for Burgers and Allen--Cahn, **SAEPS-GN is closer than raw frozen-state curvature to the exact local finite-damping reduced Hessian**. This is a local, checkpoint-dependent residual-space result. It is not a claim of exact Hessian recovery, global identifiability, posterior uncertainty, or general nonlinear-profile equivalence.

## Evidence map

| Evidence | V5 status | Permitted interpretation |
|---|---|---|
| Burgers scalar comparative | `SUPPORTED` | Primary scalar exact-reference evidence: 12/15 planned wins and 12/12 valid paired wins. |
| Allen--Cahn scalar replication | `SUPPORTED` | Independent scalar replication: 9/10 planned wins and 9/9 valid paired wins. |
| Noise/sparsity exact anchors | Secondary support | Descriptive robustness evidence; 14/14 exact-anchor pairs favor SAEPS. |
| Finite-gamma sweep | Descriptive | Sensitivity evidence only; 42/42 terminal records and 38/42 numerical passes, with no nominal-gamma recalibration. |
| Two-parameter geometry | `INCONCLUSIVE` | Availability-limited directional evidence: 8/10 valid and all 8/8 valid pairs favor SAEPS, but the preregistered 9/10 gate was not met. |
| Nonlinear finite-displacement profile | `NOT_SUPPORTED` | Only 1/5 profiles passed the frozen validity rule. The nonlinear-profile-equivalence claim is not supported and must not be restored. |
| Controlled tangent-overlap mechanism | `NOT_SUPPORTED` | The stronger cohort-level monotonic claim failed its planned-denominator gate; conditional valid-center behavior is not confirmation. |
| Scalability | Engineering/cost only | Feasibility evidence, not scientific validation of curvature accuracy or generality. |
| Width-32 architecture | Untested | Curvature comparison was not successfully tested because 0/5 frozen runs had valid stationary centers. |

The complete adjudication, denominators, retained failures, and claim restrictions are in the [V5 final audit](V5_FINAL_JCP_AUDIT_REPORT.md). Machine-readable source data are under `outputs/runs/`, aggregate evidence under `docs/evidence/`, and paper artifacts under `paper_artifacts/`.

## Validate the published evidence

The audit path uses already frozen artifacts; ordinary reviewer verification does **not** require retraining or rerunning locked confirmation experiments.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
pytest -q
python scripts/00_smoke_test.py --output-root "$env:TEMP/saeps-smoke"
python scripts/01_validate_core.py --output-root "$env:TEMP/saeps-core"
python scripts/validate_v5_repository.py
```

The V5 validator checks frozen hashes, historical raw-output immutability, raw-to-aggregate lineage, checkpoint lineage, final artifact consistency, and preservation of the scientific adjudications. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for platform details, audit-only workflows, and the distinction between lightweight validation and prohibited confirmation reruns.

## Repository guide

- `docs/evidence/v5_final_audit.json`: machine-readable V5 scientific adjudication.
- `docs/evidence/v5_final_validation.json`: machine-readable final repository validation record.
- `V5_FINAL_JCP_AUDIT_REPORT.md`: human-readable current scientific audit.
- `outputs/runs/`: retained raw records and manifests, including failed/invalid runs.
- `paper_artifacts/v5/`: deterministic V5 figures/tables and their hash manifest.
- `configs/v5/`: V5 governance, seed registry, freezes, and schemas.
- `docs/HISTORICAL_PROTOCOLS.md`: navigation for historical v2–v4 protocols and evidence.

## Evidence and release provenance

The frozen scientific evidence baseline is commit `cf76ffe85a78c994351e50b97d013d33a0f01f85`. Publication-facing documentation and CI commits do not alter that evidence. A suitable release tag is `v1.0-jcp-evidence`; release notes should state both the tagged publication commit and the frozen evidence commit above.

## License and citation

Citation metadata are provided in [CITATION.cff](CITATION.cff). No DOI has been assigned in this repository; authors should add the Zenodo DOI only after publishing a release.

The current [LICENSE](LICENSE) is **all rights reserved**. It permits public inspection but does not grant permission to copy, modify, redistribute, or reuse the software or artifacts. Authors who want third parties to reproduce and reuse the code freely must explicitly choose an open-source license such as MIT or BSD-3-Clause; this release-preparation work does not change the license.
