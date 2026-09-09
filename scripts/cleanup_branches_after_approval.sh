#!/usr/bin/env bash
set -euo pipefail
DRY_RUN=${DRY_RUN:-1}
[[ "$DRY_RUN" == 1 ]] || { echo "Stage A preview only: execution disabled; obtain approval and re-audit for Stage B." >&2; exit 2; }
cd "$(git rev-parse --show-toplevel)"
[[ "$(git remote get-url origin)" == https://github.com/milumilelu/SAEPS.git ]] || exit 3
[[ "$(git remote get-url --push origin)" == https://github.com/milumilelu/SAEPS.git ]] || exit 3
protect() { case "$1" in main|codex/saeps-so-week1) echo "Protected branch" >&2; exit 4;; esac; }
preview() { printf "DRY_RUN:"; printf " %q" "$@"; printf "\n"; }
# Fail closed if audited refs changed; this is a read-only network query.
expected_remote=$(cat <<'AUDITED_REMOTE'
0b610fb1f8a898d2954099eff2345de1095c9e37	refs/heads/codex/public-jcp-release
0b400e318267504ebae6dc9467652ad8645f0059	refs/heads/codex/saeps-so-week1
71b84e3ca28b00bac5a0d9924213415ad66954cd	refs/heads/codex/v6-phase15-protocol
0b400e318267504ebae6dc9467652ad8645f0059	refs/heads/main
56c3f8745a5adee9b4a420791b8c85b5bb50c360	refs/heads/posthoc/exact-fixed-state-decomposition-v1
ead14d9bc09f927029a8f31fd4c095634d855de0	refs/heads/posthoc/exact-fixed-state-decomposition-v2
39343bc32ae38ea2ad118011105cf4cb2c2f3241	refs/heads/posthoc/exact-fixed-state-decomposition-v3
c868127b1bcc52598dcf41a8822a7d58fed38635	refs/heads/posthoc/variable-projection-baseline-v1
0428a1f8891fd478fb53c18508aff3c0506fd57b	refs/heads/posthoc/whitening-sensitivity-v1
deedbbefe80ee63940046b10ce4b6e0ed8df1448	refs/heads/release/jcp-submission-v1
49c692c16bb646a819a7002456fbc18085e171bd	refs/heads/release/public-release-report-v1
fb66427e94e98df7252b76f24c86de6f3ee48fed	refs/tags/jcp-submission-v1
d5a231d857e410b96ae66174fb98fec9c8b9b34a	refs/tags/jcp-submission-v1^{}
AUDITED_REMOTE
)
[[ "$(git ls-remote --heads --tags origin)" == "$expected_remote" ]] || { echo "Remote changed; re-audit" >&2; exit 5; }
[[ "$(git rev-parse refs/heads/codex/public-jcp-release)" == 3b02212a4fbf7abbe41d7cacae7ac924e829f232 ]] || exit 5
[[ "$(git rev-parse refs/heads/codex/saeps-so-week1)" == 0b400e318267504ebae6dc9467652ad8645f0059 ]] || exit 5
[[ "$(git rev-parse refs/heads/codex/v6-phase15-protocol)" == 71b84e3ca28b00bac5a0d9924213415ad66954cd ]] || exit 5
[[ "$(git rev-parse refs/heads/main)" == 0b400e318267504ebae6dc9467652ad8645f0059 ]] || exit 5
[[ "$(git rev-parse refs/heads/posthoc/exact-fixed-state-decomposition-v1)" == 56c3f8745a5adee9b4a420791b8c85b5bb50c360 ]] || exit 5
[[ "$(git rev-parse refs/heads/posthoc/exact-fixed-state-decomposition-v2)" == ead14d9bc09f927029a8f31fd4c095634d855de0 ]] || exit 5
[[ "$(git rev-parse refs/heads/posthoc/exact-fixed-state-decomposition-v3)" == 39343bc32ae38ea2ad118011105cf4cb2c2f3241 ]] || exit 5
[[ "$(git rev-parse refs/heads/posthoc/variable-projection-baseline-v1)" == c868127b1bcc52598dcf41a8822a7d58fed38635 ]] || exit 5
[[ "$(git rev-parse refs/heads/posthoc/whitening-sensitivity-v1)" == 0428a1f8891fd478fb53c18508aff3c0506fd57b ]] || exit 5
[[ "$(git rev-parse refs/heads/release/jcp-submission-v1)" == deedbbefe80ee63940046b10ce4b6e0ed8df1448 ]] || exit 5
[[ "$(git rev-parse refs/heads/release/public-release-report-v1)" == 49c692c16bb646a819a7002456fbc18085e171bd ]] || exit 5
[[ "$(git rev-parse refs/remotes/origin/codex/public-jcp-release)" == 0b610fb1f8a898d2954099eff2345de1095c9e37 ]] || exit 5
[[ "$(git rev-parse refs/remotes/origin/codex/saeps-so-week1)" == 0b400e318267504ebae6dc9467652ad8645f0059 ]] || exit 5
[[ "$(git rev-parse refs/remotes/origin/codex/v6-phase15-protocol)" == 71b84e3ca28b00bac5a0d9924213415ad66954cd ]] || exit 5
[[ "$(git rev-parse refs/remotes/origin/main)" == 0b400e318267504ebae6dc9467652ad8645f0059 ]] || exit 5
[[ "$(git rev-parse refs/remotes/origin/posthoc/exact-fixed-state-decomposition-v1)" == 56c3f8745a5adee9b4a420791b8c85b5bb50c360 ]] || exit 5
[[ "$(git rev-parse refs/remotes/origin/posthoc/exact-fixed-state-decomposition-v2)" == ead14d9bc09f927029a8f31fd4c095634d855de0 ]] || exit 5
[[ "$(git rev-parse refs/remotes/origin/posthoc/exact-fixed-state-decomposition-v3)" == 39343bc32ae38ea2ad118011105cf4cb2c2f3241 ]] || exit 5
[[ "$(git rev-parse refs/remotes/origin/posthoc/variable-projection-baseline-v1)" == c868127b1bcc52598dcf41a8822a7d58fed38635 ]] || exit 5
[[ "$(git rev-parse refs/remotes/origin/posthoc/whitening-sensitivity-v1)" == 0428a1f8891fd478fb53c18508aff3c0506fd57b ]] || exit 5
[[ "$(git rev-parse refs/remotes/origin/release/jcp-submission-v1)" == deedbbefe80ee63940046b10ce4b6e0ed8df1448 ]] || exit 5
[[ "$(git rev-parse refs/remotes/origin/release/public-release-report-v1)" == 49c692c16bb646a819a7002456fbc18085e171bd ]] || exit 5
[[ "$(git rev-parse refs/tags/jcp-submission-v1)" == fb66427e94e98df7252b76f24c86de6f3ee48fed ]] || exit 5
git cat-file -e da5e67bc43ce47c0a79b666fa46dc982d14d3f1f^{commit}
git merge-base --is-ancestor da5e67bc43ce47c0a79b666fa46dc982d14d3f1f refs/heads/main
git merge-base --is-ancestor da5e67bc43ce47c0a79b666fa46dc982d14d3f1f refs/heads/codex/saeps-so-week1
git cat-file -e acf848f70a5ecc6cea98d9e74d65351deeebbdb3^{commit}
git merge-base --is-ancestor acf848f70a5ecc6cea98d9e74d65351deeebbdb3 refs/heads/main
git merge-base --is-ancestor acf848f70a5ecc6cea98d9e74d65351deeebbdb3 refs/heads/codex/saeps-so-week1
git cat-file -e cf76ffe85a78c994351e50b97d013d33a0f01f85^{commit}
git merge-base --is-ancestor cf76ffe85a78c994351e50b97d013d33a0f01f85 refs/heads/main
git merge-base --is-ancestor cf76ffe85a78c994351e50b97d013d33a0f01f85 refs/heads/codex/saeps-so-week1
git cat-file -e 39343bc32ae38ea2ad118011105cf4cb2c2f3241^{commit}
git merge-base --is-ancestor 39343bc32ae38ea2ad118011105cf4cb2c2f3241 refs/heads/main
git merge-base --is-ancestor 39343bc32ae38ea2ad118011105cf4cb2c2f3241 refs/heads/codex/saeps-so-week1
git cat-file -e c868127b1bcc52598dcf41a8822a7d58fed38635^{commit}
git merge-base --is-ancestor c868127b1bcc52598dcf41a8822a7d58fed38635 refs/heads/main
git merge-base --is-ancestor c868127b1bcc52598dcf41a8822a7d58fed38635 refs/heads/codex/saeps-so-week1
git cat-file -e 0428a1f8891fd478fb53c18508aff3c0506fd57b^{commit}
git merge-base --is-ancestor 0428a1f8891fd478fb53c18508aff3c0506fd57b refs/heads/main
git merge-base --is-ancestor 0428a1f8891fd478fb53c18508aff3c0506fd57b refs/heads/codex/saeps-so-week1
git cat-file -e d5a231d857e410b96ae66174fb98fec9c8b9b34a^{commit}
git merge-base --is-ancestor d5a231d857e410b96ae66174fb98fec9c8b9b34a refs/heads/main
git merge-base --is-ancestor d5a231d857e410b96ae66174fb98fec9c8b9b34a refs/heads/codex/saeps-so-week1
echo "Pending human approval; require clean worktrees and passing validator before Stage B."
git status --short
git worktree list --porcelain
# Proposed NEW archive tags (do not overwrite existing names):
if git show-ref --verify --quiet refs/tags/archive/public-jcp-local-3b02212; then echo "Archive name already exists; re-audit" >&2; exit 6; fi
preview git tag -a archive/public-jcp-local-3b02212 3b02212a4fbf7abbe41d7cacae7ac924e829f232 -m "Preserve historical DAG and evidence before approved branch cleanup"
preview git push origin refs/tags/archive/public-jcp-local-3b02212
echo "VERIFY remote annotated tag archive/public-jcp-local-3b02212 and peeled SHA 3b02212a4fbf7abbe41d7cacae7ac924e829f232 before deleting its source branch."
if git show-ref --verify --quiet refs/tags/archive/public-jcp-origin-0b610fb; then echo "Archive name already exists; re-audit" >&2; exit 6; fi
preview git tag -a archive/public-jcp-origin-0b610fb 0b610fb1f8a898d2954099eff2345de1095c9e37 -m "Preserve historical DAG and evidence before approved branch cleanup"
preview git push origin refs/tags/archive/public-jcp-origin-0b610fb
echo "VERIFY remote annotated tag archive/public-jcp-origin-0b610fb and peeled SHA 0b610fb1f8a898d2954099eff2345de1095c9e37 before deleting its source branch."
if git show-ref --verify --quiet refs/tags/archive/v6-phase15-71b84e3; then echo "Archive name already exists; re-audit" >&2; exit 6; fi
preview git tag -a archive/v6-phase15-71b84e3 71b84e3ca28b00bac5a0d9924213415ad66954cd -m "Preserve historical DAG and evidence before approved branch cleanup"
preview git push origin refs/tags/archive/v6-phase15-71b84e3
echo "VERIFY remote annotated tag archive/v6-phase15-71b84e3 and peeled SHA 71b84e3ca28b00bac5a0d9924213415ad66954cd before deleting its source branch."
# Proposed remote deletions. Only after the printed tag verification and approval:
protect codex/public-jcp-release
if git worktree list --porcelain | grep -Fxq "branch refs/heads/codex/public-jcp-release"; then echo "Attached worktree; stop" >&2; exit 7; fi
preview git push origin --delete codex/public-jcp-release
protect codex/v6-phase15-protocol
if git worktree list --porcelain | grep -Fxq "branch refs/heads/codex/v6-phase15-protocol"; then echo "Attached worktree; stop" >&2; exit 7; fi
preview git push origin --delete codex/v6-phase15-protocol
protect posthoc/exact-fixed-state-decomposition-v1
if git worktree list --porcelain | grep -Fxq "branch refs/heads/posthoc/exact-fixed-state-decomposition-v1"; then echo "Attached worktree; stop" >&2; exit 7; fi
preview git push origin --delete posthoc/exact-fixed-state-decomposition-v1
protect posthoc/exact-fixed-state-decomposition-v2
if git worktree list --porcelain | grep -Fxq "branch refs/heads/posthoc/exact-fixed-state-decomposition-v2"; then echo "Attached worktree; stop" >&2; exit 7; fi
preview git push origin --delete posthoc/exact-fixed-state-decomposition-v2
protect posthoc/exact-fixed-state-decomposition-v3
if git worktree list --porcelain | grep -Fxq "branch refs/heads/posthoc/exact-fixed-state-decomposition-v3"; then echo "Attached worktree; stop" >&2; exit 7; fi
preview git push origin --delete posthoc/exact-fixed-state-decomposition-v3
protect posthoc/variable-projection-baseline-v1
if git worktree list --porcelain | grep -Fxq "branch refs/heads/posthoc/variable-projection-baseline-v1"; then echo "Attached worktree; stop" >&2; exit 7; fi
preview git push origin --delete posthoc/variable-projection-baseline-v1
protect posthoc/whitening-sensitivity-v1
if git worktree list --porcelain | grep -Fxq "branch refs/heads/posthoc/whitening-sensitivity-v1"; then echo "Attached worktree; stop" >&2; exit 7; fi
preview git push origin --delete posthoc/whitening-sensitivity-v1
protect release/jcp-submission-v1
if git worktree list --porcelain | grep -Fxq "branch refs/heads/release/jcp-submission-v1"; then echo "Attached worktree; stop" >&2; exit 7; fi
preview git push origin --delete release/jcp-submission-v1
protect release/public-release-report-v1
if git worktree list --porcelain | grep -Fxq "branch refs/heads/release/public-release-report-v1"; then echo "Attached worktree; stop" >&2; exit 7; fi
preview git push origin --delete release/public-release-report-v1
# Proposed local deletions. If -d refuses, STOP; retain the local branch.
protect codex/public-jcp-release
preview git branch -d codex/public-jcp-release
protect codex/v6-phase15-protocol
preview git branch -d codex/v6-phase15-protocol
protect posthoc/exact-fixed-state-decomposition-v1
preview git branch -d posthoc/exact-fixed-state-decomposition-v1
protect posthoc/exact-fixed-state-decomposition-v2
preview git branch -d posthoc/exact-fixed-state-decomposition-v2
protect posthoc/exact-fixed-state-decomposition-v3
preview git branch -d posthoc/exact-fixed-state-decomposition-v3
protect posthoc/variable-projection-baseline-v1
preview git branch -d posthoc/variable-projection-baseline-v1
protect posthoc/whitening-sensitivity-v1
preview git branch -d posthoc/whitening-sensitivity-v1
protect release/jcp-submission-v1
preview git branch -d release/jcp-submission-v1
protect release/public-release-report-v1
preview git branch -d release/public-release-report-v1
