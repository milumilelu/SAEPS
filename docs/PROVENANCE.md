# PROVENANCE.md

## Protocol Sources

| Source | SHA256 | Role |
|---|---|---|
| `SAEPS-Codex Goal 实验项目任务书与验收规范.md` | `DE58B07F0E6836EC4468F21F7F4607EBD16577A8B3494E978FF5318BAFE58CE2` | Initial governance and hard acceptance |
| `SAEPS 最小可发表版本实验说明与新仓库开发任务书.md` | `347900D18A59E8AF8E98B1CE074AB36CF9C4766EB548592ED6D515E46E0C7A0C` | MVP experimental redesign |
| Confirmation seed update attachment | `402FD0B411CE115975AE50A62554FBB85B26A56405A64901721A523E974F9FF9` | 10-seed paired-statistics amendment |
| `SAEPS 新仓库实验任务书 v2.0.md` | `FD7F2675719F98997236D735CED8181D631A939835DF6A08A9192FBE6266B07C` | Current JCP-level protocol |

## Active Governance

- Active contract: `docs/EXECUTION_CONTRACT.md` (`SAEPS-JCP-EXEC-v2.0`)
- Current protocol state: `P0 PASSED / UNLOCKED`
- P0 implementation commit: `6c88a860dbaf95988ae75b30b9f0efcdd951623c`
- P0 evidence: `docs/evidence/P0_ACCEPTANCE.md` and `docs/evidence/p0_acceptance.json`

Run-level provenance schema is defined by the execution contract. Experimental provenance entries will be generated automatically; they must not be entered manually as paper values.

## V3 Foundation Development

- Development-only contract: `docs/v3/EXECUTION_CONTRACT.md`
- Formal foundation run: `v3-foundation-s20-20260819T114530.041894+0000-b10a91601fd9`
- Clean implementation commit: `6309a62ca206fb73e28258b742f7bfafa68a6fa0`
- Configuration hash: `f42431dc76f9cc09012a33a4f430c1cefbbd0d36744687b7039d9833cf6e3d59`
- v2 scalar lock hash verified unchanged: `cb5c2e9e3eee2d5462dd92ac0b9cd3b2b607ea487367d9c83b18a3a8af9c5cf8`
- Acceptance: `docs/evidence/V3_FOUNDATION_ACCEPTANCE.md`
- Scope remains `DEVELOPMENT_ONLY`; no v3 confirmation is authorized.

## V3.1 State-Minimum Development

- Contract: `docs/v3_1/EXECUTION_CONTRACT.md`
- Accepted seed-20 run: `v3-1-state-min-s20-20260819T122328.472834+0000-629b7eb8ec88`
- Clean run commit: `0cbde5853a33ac8dc02f3f64e598210854b3e1a7`
- Engineering validation: `PASSED`
- Strict full-chain gate: `FAIL` at unregularized multiscale convergence
- Seed status: 21–24 inactive; 30–44 unseen/inactive; confirmation unauthorized
- Evidence: `docs/evidence/V3_1_SEED20_ACCEPTANCE.md`

## V3.2 Gamma-Primary Development

- Contract: `docs/v3_2/EXECUTION_CONTRACT.md`
- Accepted seed-20 run: `v3-2-gamma-primary-s20-20260819T133259.913719+0000-defb083d1a75`
- Clean run commit: `681e6354c3cf199533f275f9cc933c6565849158`
- Configuration hash: `f65072d22a444786f19c7c92cc617f5a1b3fb55ebbee3d3433404a64568ac9bb`
- Engineering validation: `PASSED`; gamma-primary chain: `FAIL`
- Seeds 21–24 and 30–44 remain inactive; confirmation unauthorized
- Evidence: `docs/evidence/V3_2_SEED20_ACCEPTANCE.md`

## V3.3 Numerical-Decomposition Development

- Contract: `docs/v3_3/EXECUTION_CONTRACT.md`
- Accepted seed-20 run: `v3-3-num-decomp-s20-20260819T142127.327595+0000-3b23a23db90f`
- Clean implementation commit: `b0c317c8d13d49db5942dee5203c964cb74bb482`
- Configuration hash: `83c190d1d76600671ae5558e93b50720ef96169e7bd43fab073f874237029bae`
- Engineering validation: `PASSED`; registered all-gates chain: `FAIL`
- Diagnostic scope: `NONBINDING_DIAGNOSTIC_ONLY`
- Seeds 21–24 and 30–44 remain inactive; confirmation unauthorized
- Evidence: `docs/evidence/V3_3_SEED20_ACCEPTANCE.md`
