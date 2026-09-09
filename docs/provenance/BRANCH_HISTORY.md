# Branch history — Stage B completed

Date: 2026-09-09. Authorization: user explicitly approved ordered steps A–G after reviewing Stage A. This supersedes the Stage A no-mutation restriction only for the named tags and branches. The known validator failure was explicitly retained. Stage A files remain immutable historical snapshots; this file records executed results.

## Execution and gates

1. A: all audited heads/remotes/tags matched Stage A; both worktrees and required SHAs verified. Codex internal turn-diff capture refs changed between turns; recorded in `branch_cleanup_raw/internal_ref_delta.json`, left untouched and excluded from branch/tag inventory.
2. B: created and pushed three new annotated tags individually; all local tag objects and peeled commits matched live `ls-remote`. No branch was deleted before `B_tags_verified.json` was written.
3. C: deleted the seven specified posthoc/release remote branches, then fetched/pruned and rechecked required SHAs, all tags, protected refs and worktrees. Four remote heads remained; `C_verified.json` passed.
4. D: only after C passed, deleted the two archived Codex remote branches. Two protected remote heads remained; `D_verified.json` passed.
5. E: attempted each of nine corresponding local branches with `git branch -d` only. Seven deleted; two refused and retained. No force deletion or rewrite.
6. G: fetched/pruned again; checked exactly two remote heads, four tags, all seven required SHAs, expected local refs and the two unchanged worktrees. All pre-existing tracked working-file bytes/missing states except cleanup TASKS were checked against preflight hashes.
7. Unified validator rerun: all check statuses identical to Stage A; no new failures. Cleanup provenance is committed locally on main; no branch push is performed. The local main advance is a documentation/cleanup-artifact commit only, while the SO ref/worktree and remote main remain at the protected research commit.

## Actual branch results

| Historical branch | Remote | Local | Exact historical tip(s) preserved by |
|---|---|---|---|
| `posthoc/exact-fixed-state-decomposition-v1` | DELETED | DELETED | main ancestry: `56c3f8745a5adee9b4a420791b8c85b5bb50c360` |
| `posthoc/exact-fixed-state-decomposition-v2` | DELETED | DELETED | main ancestry: `ead14d9bc09f927029a8f31fd4c095634d855de0` |
| `posthoc/exact-fixed-state-decomposition-v3` | DELETED | DELETED | main ancestry: `39343bc32ae38ea2ad118011105cf4cb2c2f3241` |
| `posthoc/variable-projection-baseline-v1` | DELETED | DELETED | main ancestry: `c868127b1bcc52598dcf41a8822a7d58fed38635` |
| `posthoc/whitening-sensitivity-v1` | DELETED | DELETED | main ancestry: `0428a1f8891fd478fb53c18508aff3c0506fd57b` |
| `release/jcp-submission-v1` | DELETED | DELETED | main ancestry: `deedbbefe80ee63940046b10ce4b6e0ed8df1448` |
| `release/public-release-report-v1` | DELETED | DELETED | main ancestry: `49c692c16bb646a819a7002456fbc18085e171bd` |
| `codex/public-jcp-release` | DELETED | RETAINED_-d_REFUSED | `archive/public-jcp-local-3b02212` (local DAG); `archive/public-jcp-origin-0b610fb` (remote DAG) |
| `codex/v6-phase15-protocol` | DELETED | RETAINED_-d_REFUSED | `archive/v6-phase15-71b84e3` (same local/remote DAG) |

Retained local historical branches are unmerged into main. Archiving them does not make `git branch -d` succeed; its refusal was honored. Both exact DAGs remain protected by uploaded annotated tags.

## Verified tag objects and peeled commits

| Tag | Tag object SHA | Peeled commit SHA |
|---|---|---|
| `archive/public-jcp-local-3b02212` | `5cd076c4d5e1623cf3931bf1f14166dd3a0e9e0d` | `3b02212a4fbf7abbe41d7cacae7ac924e829f232` |
| `archive/public-jcp-origin-0b610fb` | `dc59ac5a27c61ff1d15630465693284569636521` | `0b610fb1f8a898d2954099eff2345de1095c9e37` |
| `archive/v6-phase15-71b84e3` | `eb22e2c20920fbcac3d614fdccb199195fc61e54` | `71b84e3ca28b00bac5a0d9924213415ad66954cd` |
| `jcp-submission-v1` | `fb66427e94e98df7252b76f24c86de6f3ee48fed` | `d5a231d857e410b96ae66174fb98fec9c8b9b34a` |

Every row was checked locally and against live remote refs. The existing submission tag object is unchanged. Release branch deedbbe was not identical to this tag; both histories remain reachable from main.

## Required provenance

| SHA | Retained paths |
|---|---|
| `da5e67bc43ce47c0a79b666fa46dc982d14d3f1f` | main + local/remote SO |
| `acf848f70a5ecc6cea98d9e74d65351deeebbdb3` | main + local/remote SO |
| `cf76ffe85a78c994351e50b97d013d33a0f01f85` | main + local/remote SO + jcp-submission-v1 |
| `39343bc32ae38ea2ad118011105cf4cb2c2f3241` | main + local/remote SO + jcp-submission-v1 |
| `c868127b1bcc52598dcf41a8822a7d58fed38635` | main + local/remote SO + jcp-submission-v1 |
| `0428a1f8891fd478fb53c18508aff3c0506fd57b` | main + local/remote SO + jcp-submission-v1 |
| `d5a231d857e410b96ae66174fb98fec9c8b9b34a` | main + local/remote SO + jcp-submission-v1 |

## Final structure

Remote heads: **11 → 2**. Both point to `0b400e318267504ebae6dc9467652ad8645f0059`:

- `main`
- `codex/saeps-so-week1`

Local heads: **11 → 4**:

- `main`: advances only by this cleanup provenance commit, not pushed.
- `codex/saeps-so-week1`: `0b400e318267504ebae6dc9467652ad8645f0059`, unchanged.
- `codex/public-jcp-release`: `3b02212a4fbf7abbe41d7cacae7ac924e829f232`, -d refused.
- `codex/v6-phase15-protocol`: `71b84e3ca28b00bac5a0d9924213415ad66954cd`, -d refused.

Worktrees remain attached to main and codex/saeps-so-week1 at their original paths. SO HEAD/index/clean status is unchanged. Main retains the seven pre-existing file deletions and unrelated untracked files; only cleanup artifacts/TASKS enter this commit.

DAG summary: the local cleanup commit descends from 0b400e3; SO and both remote heads stay at 0b400e3. V6 remains a separate historical line ending at 71b84e3, now tagged. The distinct public-jcp histories end at 3b02212 and 0b610fb, each tagged despite equal trees. jcp-submission-v1 remains at d5a231d. Full pre-commit DAG: `branch_cleanup_raw/final_graph.txt`; this report commit itself can be found with `git log -- docs/provenance/BRANCH_HISTORY.md`.

## Validator before / after

- Exit code: 1 → 1; repository status FAILED → FAILED.
- Tests: 147 passed / 1 failed / 1 skipped → unchanged.
- Failed checks unchanged: scientific_gate_and_final_mapping; unit_and_integration_tests.
- Existing causes: missing FINAL_VALIDATION_REPORT.md and V5_JCP_MINIMAL_PROTOCOL.md (I-UPGRADE-002).
- Failing test unchanged: tests/test_v5_final_audit.py::test_v5_post_execution_validator_passes_core_checks.
- No new failure, scientific rerun, repair, threshold change, or evidence modification. Comparison: `branch_cleanup_raw/validator_comparison.json`.

Machine logs: `branch_cleanup_raw/commands.jsonl` (ordered commands, return codes and exact output), B/C/D/E/G checkpoint JSON files, raw validator output. Historical unique lists/diffs remain in `branch_audit_raw/`. The old dry-run script remains a Stage A snapshot; its stale-ref guard intentionally rejects current refs. Do not use it to repeat Stage B.
