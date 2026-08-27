# SAEPS public release report

## 1. Initial repository state

- Repository: `https://github.com/milumilelu/SAEPS`
- Initial visibility: private
- Initial `main`: `cf76ffe85a78c994351e50b97d013d33a0f01f85`
- Initial license: all rights reserved
- Initial public README: historical v2 `PARTIALLY_SUPPORTED / INVESTIGATE_NUMERICS` landing page
- Integration PR: `https://github.com/milumilelu/SAEPS/pull/5`
- Integration merge commit: `080168bda5b2f43180f14027c44ea0f7ed534694`

## 2. Security and privacy scan

`gitleaks` was not installed, and its official release download endpoint was unavailable during the pre-public audit. A full-history fallback scanner inspected every reachable commit for GitHub/AWS token formats, private-key headers, credential assignments, sensitive filenames, oversized blobs, and local absolute paths without printing candidate secret values. It found zero credential-pattern hits and no sensitive credential filenames. GitHub secret scanning and push protection were enabled after publication.

One historical Windows temporary path remains in `docs/ISSUES.md`. It is non-secret execution provenance and does not identify a credential. No history rewrite was required.

## 3. License audit

The author-authorized license is the standard OSI BSD 3-Clause text with copyright `Copyright (c) 2026, SAEPS authors`. No vendored third-party source, submodule, external dataset license conflict, or third-party figure requiring relicensing was identified. Python dependencies are installed separately and retain their own licenses. The archived PDF and TeX are author manuscript snapshots.

## 4. PR #2/#3/#4 integration method

The branches were merged separately with `git merge --no-ff`; no squash, rebase, or cherry-pick was used:

- PR #2 head: `39343bc32ae38ea2ad118011105cf4cb2c2f3241`
- PR #3 head: `c868127b1bcc52598dcf41a8822a7d58fed38635`
- PR #4 head: `0428a1f8891fd478fb53c18508aff3c0506fd57b`

All source heads and their protocol/evidence commits remain ancestors of the integrated history.

## 5. Merge conflicts and resolutions

The three evidence merges completed without content conflicts. During publication cleanup, moving `V5_JCP_MINIMAL_PROTOCOL.md` was rejected by the V5 validator because that path is frozen; the file was restored byte-for-byte to its original root path before commit. No scientific file was regenerated to resolve a conflict.

## 6. Protected evidence verification

`protected historical evidence diff = empty` for `outputs/runs/`, `configs/locked/`, `configs/v5/`, `src/`, `paper_artifacts/`, the V5 evidence files, and frozen V5 reports relative to `cf76ffe85a78c994351e50b97d013d33a0f01f85`.

No seed was replaced; invalid and failed records remain present; planned denominators and all scientific adjudications are unchanged. Exact decomposition, variable projection, and whitening sensitivity remain post-hoc/nonbinding. Two-parameter evidence remains `INCONCLUSIVE`.

## 7. Test result

- Local: `148 passed, 1 skipped`, 0 failed
- GitHub Actions run `33043562287`: `repository-validation` passed
- Lightweight smoke/core/profile validations: passed with disposable output roots

The single skipped test is the documented immutable V5 pre-execution assertion; post-execution validation is binding.

## 8. Repository validator result

- `python scripts/validate_repository.py`: `PASSED`
- `python scripts/validate_v5_repository.py`: `PASSED`
- 85 frozen protocol/executable hashes match
- 441 protected pre-V5 files retain their frozen tree digest
- 29/29 checkpoint records remain unique, one-attempt, reloadable, and unreplaced
- V5 artifacts and deterministic report rebuild pass

## 9. Final main SHA

The submission snapshot commit is the peeled commit of annotated tag `jcp-submission-v1` and is reported explicitly in the GitHub Release notes. It can be resolved with:

```text
git rev-parse jcp-submission-v1^{commit}
```

A Git commit cannot embed its own final SHA without changing that SHA; the immutable tag and release provide the non-self-referential record.

## 10. Manuscript-facing provenance reachability

The following commits are present and reachable in the public repository history:

- `cf76ffe85a78c994351e50b97d013d33a0f01f85`
- `538b866`
- `e30f65df3b9321422439b5f28d99b157f14ae100`
- `39343bc32ae38ea2ad118011105cf4cb2c2f3241`
- `2b700c253af55d5d5095f7380c85a1f1c62d78c5`
- `c868127b1bcc52598dcf41a8822a7d58fed38635`
- `17d48bf7c3233c89cb17b0444a90b1885ab7bb5f`
- `0428a1f8891fd478fb53c18508aff3c0506fd57b`
- `db55ef9d1db5d2080f7ceee68ba1d094f4cce49c`

## 11. Tag and GitHub Release

- Annotated tag: `jcp-submission-v1`
- Release title: `JCP submission snapshot v1`
- Stable URL: `https://github.com/milumilelu/SAEPS/releases/tag/jcp-submission-v1`
- Scope: submission snapshot, not an accepted-version claim

No DOI or ORCID was invented. A Zenodo DOI may be added only after an archival deposit is issued.

## 12. Repository visibility

Visibility is public. The default branch remains `main`; Issues are enabled and Wiki is disabled.

## 13. Main branch protection

`main` requires pull requests and strict `repository-validation` status checks. Required approvals are 0. Force pushes and branch deletion are disabled. Administrators may bypass in an emergency. Merge commits, squash merges, and rebase merges remain available globally, but manuscript-provenance branches must use merge commits as documented in `CONTRIBUTING.md`.

## 14. GitHub Actions and security settings

Workflow permissions default to `contents: read`. CI fetches full history, installs CPython 3.12.13 and pinned dependencies, runs tests and lightweight validators, and runs both repository validators. It does not rerun frozen confirmation training.

Private vulnerability reporting, Dependabot alerts/security updates, secret scanning, and push protection are enabled. GitHub plan-dependent non-provider secret patterns and validity checks are not enabled.

## 15. Remaining known limitations

- Scientific conclusions remain local and benchmark-limited.
- Nonlinear finite-displacement profile equivalence is `NOT_SUPPORTED`.
- Two-parameter evidence is `INCONCLUSIVE` under the preregistered 9/10 availability gate.
- Scalability demonstrates engineering feasibility, not large-network curvature accuracy.
- Width-32 curvature accuracy was not successfully tested because no valid stationary center was available.
- No archival DOI is currently assigned.

## 16. Recommended Data Availability wording

> Code, frozen experimental records, and machine-readable evidence are publicly available in the SAEPS repository at https://github.com/milumilelu/SAEPS. The submitted evidence snapshot is archived under tag `jcp-submission-v1`; the corresponding full commit SHA is reported in the repository release.

## Final status

```text
PUBLIC RELEASE: PASS
Tag: jcp-submission-v1
Release: https://github.com/milumilelu/SAEPS/releases/tag/jcp-submission-v1
Visibility: public
License: BSD-3-Clause
Tests: PASS
Validator: PASS
Secret scan: PASS (full-history fallback plus GitHub secret scanning)
Protected evidence: unchanged
```
