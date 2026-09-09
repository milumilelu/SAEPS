# Branch audit — Stage A / 审计完成，未执行清理

审计时间 UTC：2026-09-09T09:24:33.216780+00:00；基准 main：`0b400e318267504ebae6dc9467652ad8645f0059`。

已联网执行 `git fetch --all --tags --prune`，并用 `git ls-remote --heads --tags origin` 核对服务器。仓库非 shallow；origin 为 https://github.com/milumilelu/SAEPS.git。11 local branches、11 remote heads（不把 origin/HEAD 符号引用计为分支）、1 annotated tag、2 worktrees。GitHub Release 服务端对象未另行查询；现有唯一 tag 及其全部祖先不变。

本阶段不删除本地/远程 branch、不创建或修改 tag、不 push。已有用户改动保留；主工作树预先存在7个 tracked deletions及未跟踪文件，SO工作树干净。原始状态见 branch_audit_raw/worktree_*_status.txt。

## 判定口径

`unique_commit_count` 精确定义为 main..branch 的提交数；不是仅由该 ref 引用的全局独有数。本地与远程逐行审计。merge-base 三点差异和 main→tip 两点差异均保存；已合并历史分支三点差异为空不代表与 main tree 相同。每个 tip 的 path/mode/blob 与 main、SO、已有tag的当前tree比较；不一致的文件清单不是“数据丢失”，历史祖先仍可恢复。未合并分支必须保留完整 DAG，patch/tree 相同不等于提交身份相同。

所有 DELETE_AFTER_VERIFY 都是待审批候选，当前均为 DO_NOT_DELETE（尚未完成人工确认、干净工作树与验收条件）。本次无 EXTRACT_THEN_DELETE / MANUAL_REVIEW 分类：完整归档足以保留已停止的历史工作；没有证据要求现在移植代码。若决定继续维护V6算法，应先制定提取清单并改列 EXTRACT_THEN_DELETE。

## 逐分支分类

| Branch | Scope | Unique vs main | Action | Risk | Reason |
|---|---|---:|---|---|---|
| `codex/public-jcp-release` | local | 7 | ARCHIVE_TAG_THEN_DELETE | medium | Unmerged unique DAG and tip content; preserve exact tip with a NEW annotated archive tag before any deletion. |
| `codex/saeps-so-week1` | local | 0 | KEEP | low | Protected stable main / active SO worktree; no rename or rewrite. |
| `codex/v6-phase15-protocol` | local | 8 | ARCHIVE_TAG_THEN_DELETE | medium | Unmerged unique DAG and tip content; preserve exact tip with a NEW annotated archive tag before any deletion. |
| `main` | local | 0 | KEEP | low | Protected stable main / active SO worktree; no rename or rewrite. |
| `posthoc/exact-fixed-state-decomposition-v1` | local | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |
| `posthoc/exact-fixed-state-decomposition-v2` | local | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |
| `posthoc/exact-fixed-state-decomposition-v3` | local | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |
| `posthoc/variable-projection-baseline-v1` | local | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |
| `posthoc/whitening-sensitivity-v1` | local | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |
| `release/jcp-submission-v1` | local | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |
| `release/public-release-report-v1` | local | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |
| `origin/codex/public-jcp-release` | origin | 6 | ARCHIVE_TAG_THEN_DELETE | medium | Unmerged unique DAG and tip content; preserve exact tip with a NEW annotated archive tag before any deletion. |
| `origin/codex/saeps-so-week1` | origin | 0 | KEEP | low | Protected stable main / active SO worktree; no rename or rewrite. |
| `origin/codex/v6-phase15-protocol` | origin | 8 | ARCHIVE_TAG_THEN_DELETE | medium | Unmerged unique DAG and tip content; preserve exact tip with a NEW annotated archive tag before any deletion. |
| `origin/main` | origin | 0 | KEEP | low | Protected stable main / active SO worktree; no rename or rewrite. |
| `origin/posthoc/exact-fixed-state-decomposition-v1` | origin | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |
| `origin/posthoc/exact-fixed-state-decomposition-v2` | origin | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |
| `origin/posthoc/exact-fixed-state-decomposition-v3` | origin | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |
| `origin/posthoc/variable-projection-baseline-v1` | origin | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |
| `origin/posthoc/whitening-sensitivity-v1` | origin | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |
| `origin/release/jcp-submission-v1` | origin | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |
| `origin/release/public-release-report-v1` | origin | 0 | DELETE_AFTER_VERIFY | low | Tip and every ancestor reachable from retained main; historic tree remains retrievable even where current tip differs. |

## 关键发现

- 五条 posthoc 分支均为 main 祖先，unique=0；失败/aborted v1、v2记录也随祖先完整保留，不为减少分支而抹掉失败证据。
- 两条 release 分支均为 main 祖先，unique=0，属于已整合的发布线。特别注意：release/jcp-submission-v1=`deedbbe` 与正式 tag=`d5a231d857e4` **不等价**；tag 比 branch 多132行的 PUBLIC_RELEASE_REPORT.md，不能以同名判为同一快照。允许列入候选的依据是 main 同时保留两者，既有 tag 不动。
- public-jcp 本地7个、远程6个提交不在main；两个tip的tree完全一致，但DAG不同，`git cherry main`也未证明patch等价于main。27个path/mode/blob与保留ref当前tree不同，含 PUBLIC_RELEASE_AUDIT.md、CI、LICENSE、文稿与治理文档等；不能称为纯重复工作流痕迹。分别归档两tip，避免丢失任一提交身份。
- V6本地/远程同tip `71b84e3`，8个unique commits；6014个path/mode/blob不在保留ref当前tree，包含 src/saeps/v6、scripts/v6、tests/v6、configs/v6、docs/v6 以及 outputs/runs/v5/upgrade_pilot/phase15/20260907_001。findings/FINDINGS.md明确 NOT_SUPPORTED 与停止后续层级。归档完整tip保留失败、原始轨迹和协议，不将其合入SO研究以凑整合。

## 受保护提交与稳定可达路径

| Commit | Full SHA | Retained refs |
|---|---|---|
| da5e67b | `da5e67bc43ce47c0a79b666fa46dc982d14d3f1f` | main; refs/heads/codex/saeps-so-week1 |
| acf848f | `acf848f70a5ecc6cea98d9e74d65351deeebbdb3` | main; refs/heads/codex/saeps-so-week1 |
| cf76ffe | `cf76ffe85a78c994351e50b97d013d33a0f01f85` | main; refs/heads/codex/saeps-so-week1; refs/tags/jcp-submission-v1 |
| 39343bc | `39343bc32ae38ea2ad118011105cf4cb2c2f3241` | main; refs/heads/codex/saeps-so-week1; refs/tags/jcp-submission-v1 |
| c868127 | `c868127b1bcc52598dcf41a8822a7d58fed38635` | main; refs/heads/codex/saeps-so-week1; refs/tags/jcp-submission-v1 |
| 0428a1f | `0428a1f8891fd478fb53c18508aff3c0506fd57b` | main; refs/heads/codex/saeps-so-week1; refs/tags/jcp-submission-v1 |
| d5a231d857e4 | `d5a231d857e410b96ae66174fb98fec9c8b9b34a` | main; refs/heads/codex/saeps-so-week1; refs/tags/jcp-submission-v1 |

SO worktree：`C:/Users/RZF/Desktop/博士课题资料/SAEPS-so-week1`，branch=`codex/saeps-so-week1`。两受保护提交已在本地/远程main和SO祖先链中。本轮不改名；Phase 1B之后是否重命名研究线需另行决定。

现有 annotated tag object：`fb66427e94e98df7252b76f24c86de6f3ee48fed`；peeled commit：`d5a231d857e410b96ae66174fb98fec9c8b9b34a`。服务器与本地完全匹配。五个论文SHA全为该tag祖先。

## Stage B 拟议归档（本次未创建）

- `archive/public-jcp-local-3b02212` → `3b02212a4fbf7abbe41d7cacae7ac924e829f232`；必须新建 annotated tag，推送后复核tag object与peeled SHA；不可覆盖已有tag。
- `archive/public-jcp-origin-0b610fb` → `0b610fb1f8a898d2954099eff2345de1095c9e37`；必须新建 annotated tag，推送后复核tag object与peeled SHA；不可覆盖已有tag。
- `archive/v6-phase15-71b84e3` → `71b84e3ca28b00bac5a0d9924213415ad66954cd`；必须新建 annotated tag，推送后复核tag object与peeled SHA；不可覆盖已有tag。

## 预期结构

当前远程11条 → 仅批准7条已合并候选时4条（main、codex/saeps-so-week1、codex/public-jcp-release、codex/v6-phase15-protocol） → 三个归档tag确认上传、再批准2条归档分支候选后2条（main、codex/saeps-so-week1）。本地同为11→4→2，但unmerged local branch的 `git branch -d` 可能拒绝；拒绝时保留本地分支，禁止改用-D，因此本地最终2条并非当前承诺。

远程分类计数：KEEP=2，DELETE_AFTER_VERIFY=7，ARCHIVE_TAG_THEN_DELETE=2，EXTRACT_THEN_DELETE=0，MANUAL_REVIEW=0。需要人工确认的是全部9条拟删远程分支，不是“MANUAL_REVIEW=0所以无需审批”。

将来可在独立授权下把SO统一命名 research/saeps-so；本阶段不建立 paper/q2-revision、saeps-so-phase1 或 q2-submission-v1。

## 验证与复查

CSV包含22条完整记录和完整unique commit列表。branch_audit_raw/dag.txt保存完整DAG；每行raw_prefix对应unique、merge-base stat/name-status、tip name-status、cherry、unpreserved tip blob清单。branch_audit_raw/provenance.json保存全部contains关系。

cleanup脚本仅打印命令，默认DRY_RUN=1；DRY_RUN=0明确拒绝执行，故即使误设变量也不进入Stage B。实际Stage B需基于批准清单另行执行并重新验证，特别是归档tag先上传、local -d拒绝即停。脚本会重复检查origin、全部refs快照、required SHAs、main/SO祖先链和已存在tag，保护main/SO硬编码；对worktree附着分支拒绝生成删除操作。

统一仓库validator实际运行日志：branch_audit_raw/repository_validation.txt。预先已有文件删除的缺陷不得在本任务静默修复；Stage A Git审计通过不等于全仓库科学/工程验收通过。

实际验收结果：Stage A 专项检查 PASSED（refs、worktree附着、SO状态不变；22条unique count复核；Bash语法、真实dry-run通过；DRY_RUN=0拒绝执行）。统一validator退出1：147 tests passed、1 failed、1 skipped；失败来自预先缺失的 FINAL_VALIDATION_REPORT.md、V5_JCP_MINIMAL_PROTOCOL.md，已由 docs/ISSUES.md 的 I-UPGRADE-002 记录。未提交或推送：保留用户改动，遵循验收失败时保留本地结果的规则。
