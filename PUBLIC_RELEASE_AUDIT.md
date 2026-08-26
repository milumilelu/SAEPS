# SAEPS public-release audit

## Scope and baseline

- Publication-preparation branch: `codex/public-jcp-release`
- Frozen scientific evidence baseline: `cf76ffe85a78c994351e50b97d013d33a0f01f85`
- Repository: `https://github.com/milumilelu/SAEPS`
- Permitted scope: documentation, repository navigation, CI, and release metadata only
- Publication-facing content commit: `TO_BE_RECORDED_AFTER_COMMIT`

## Publication-facing changes

- `README.md`: replaced the historical v2 landing page with the V5 final-audit claim, evidence boundaries, four primary navigation links, reviewer validation commands, provenance, and license notice.
- `REPRODUCIBILITY.md`: added pinned-environment setup, unit/smoke/core/profile validation, V5 repository validation, raw-to-aggregate audit instructions, CI scope, and Data/Code Availability guidance.
- `docs/HISTORICAL_PROTOCOLS.md`: added a single navigation index for v2, v3, and v4 protocols and reports.
- Historical protocol/report entry pages: added status banners linking to the V5 audit; their historical scientific results and protocol bodies were not rewritten.
- `.github/workflows/ci.yml`: made V5 final repository validation a required CI step and redirected lightweight validation outputs to the runner temporary directory.
- `CITATION.cff`: added repository and software metadata, explicit author/paper placeholders, and the frozen scientific evidence commit; no DOI was invented.
- `PUBLIC_RELEASE_AUDIT.md`: recorded the public-release scope, validation, unchanged scientific assets, release recommendation, and author actions.

## Scientific and frozen files not modified

No training, confirmation, aggregation, or scientific-result regeneration was performed. In particular, the publication work did not modify:

- any file under `outputs/runs/`;
- any file under `configs/locked/` or `configs/v5/`;
- frozen executables or package source under `src/` and `scripts/`;
- V5 raw records, checkpoint artifacts, manifests, aggregates, figures, tables, or their hashes;
- `docs/evidence/v5_final_audit.json` or `V5_FINAL_JCP_AUDIT_REPORT.md`;
- registered seeds, gates, thresholds, scientific statuses, or failed/invalid records; or
- `LICENSE`.

Historical documents received navigation-only banners. Their prior results remain intact, and the V5 validator confirms that the protected historical raw-output tree is byte-identical.

## Validation record

Baseline at `cf76ffe85a78c994351e50b97d013d33a0f01f85`:

- `python scripts/validate_v5_repository.py`: `PASSED`
- frozen protocol/executable hashes: 85/85 match
- protected pre-V5 files: 441 retain the frozen tree digest
- checkpoint lineage: 29/29 unique, one-attempt, reloadable
- scientific adjudications: preserved

After publication-facing changes:

- `pytest -q`: 121 passed, 1 historical pre-execution assertion skipped, 0 failed
- `scripts/00_smoke_test.py` with temporary output: `PASS`
- `scripts/01_validate_core.py` with temporary output: `PASS`
- `scripts/04_validate_profile.py` with temporary output: `PASS`
- `scripts/validate_v5_repository.py`: `PASSED`
- final report deterministic rebuild: `PASS`
- paper artifact manifest: 7 artifacts hash-match
- raw-to-aggregate source counts: finite-gamma 42, profile 5, two-parameter 10, residual scalability 27, baseline 5
- scientific adjudications remain: overall `PARTIALLY_SUPPORTED`; nonlinear profile `NOT_SUPPORTED`; two-parameter `INCONCLUSIVE`

## Publication release recommendation

Recommended tag: `v1.0-jcp-evidence`.

Tag the publication-facing branch tip after review. Release notes should state:

> This release packages SAEPS for JCP review and public evidence audit. Publication-facing documentation, CI, citation metadata, and navigation were added without changing scientific evidence. All scientific raw evidence and adjudications originate from frozen commit `cf76ffe85a78c994351e50b97d013d33a0f01f85`. The V5 final repository validator passes, including frozen hashes, historical immutability, checkpoint lineage, raw-to-aggregate lineage, deterministic report reconstruction, and preserved scientific outcomes.

Do not regenerate scientific results to fit the release. If the tag points to the later documentation/CI commit, retain the frozen evidence commit above in the release notes.

## Author actions still required

- Make the GitHub repository publicly visible when submission policy permits.
- Replace the author and paper-title placeholders in `CITATION.cff`.
- Create the release and, if desired, archive it with Zenodo; then add the issued DOI. No DOI currently exists in repository metadata.
- Decide whether to replace the current all-rights-reserved `LICENSE` with an author-approved open license such as MIT or BSD-3-Clause. This task did not change the license.
- Insert the final public repository/release URL in the manuscript Data Availability statement.
- Confirm that no untracked local manuscript material (including the pre-existing `paper/` directory) is accidentally included in the public release.

Because a Git commit cannot contain its own SHA without changing that SHA, the audit records the publication-facing content commit after it is created; the audit-inclusive branch-tip SHA is reported in the PR/release metadata and can always be verified with `git rev-parse HEAD`.
