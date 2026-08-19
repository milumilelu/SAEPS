# V3 Foundation Acceptance

## 结论

五项 foundation correction 已按 `SAEPS-FOUNDATION-v3.0-development` 完成工程实现与真实 Burgers seed 20 端到端运行。工程 gate 为 `PASSED`，但结果不支持进入 v3 confirmation：exact state Hessian 非正定，两个 nonlinear profile 均未通过预注册的多尺度收敛流程。

## 可追溯运行

- run: `v3-foundation-s20-20260819T114530.041894+0000-b10a91601fd9`
- clean implementation commit: `6309a62ca206fb73e28258b742f7bfafa68a6fa0`
- config hash: `f42431dc76f9cc09012a33a4f430c1cefbbd0d36744687b7039d9833cf6e3d59`
- v2 scalar lock hash: `cb5c2e9e3eee2d5462dd92ac0b9cd3b2b607ea487367d9c83b18a3a8af9c5cf8`
- environment: CPU, float64, Python 3.12.13, torch 2.13.0

## 实际结果

- common state-profiled base: `PASS`; mean loss `0.0366474069 -> 0.0301511367`; relative state drift `0.364383`; theta stationarity residual `0.00362462`.
- Gauss–Newton: `Fraw=645.4436613`; `Fse=22.40331108`; explicit/matrix-free relative error `1.7871e-9`.
- exact full Hessian: symmetry error `1.1572e-16`, but unregularized/gamma-matched state blocks分别有 `18/16` 个非正方向，最小特征值分别为 `-1.637958/-1.634889`；按协议禁止计算 Schur reduction。
- unregularized profile: `0/8` points passed the combined optimizer rule; no multiscale curvature estimate.
- gamma-matched profile: `2/8` points passed; no multiscale curvature estimate.

## 判定

这不是工程失败：所有计划点均有最终状态，失败数据完整保存，full-Hessian 无效性也被机器可读地报告。它是明确的数值/科学警报：当前 checkpoint 不能被表述为具有可靠局部凸 state-profile geometry，七点二次拟合也不能再充当主要证据。v3 confirmation 未授权。

## Fresh-clone audit

在 clean commit `0b82d08` 的全新 clone 中，依次执行 v2 canonical snapshot verification、paper artifact rebuild、v2 repository validator 与 v3 foundation validator，全部 `PASSED`；artifact 重建后 `git status --porcelain` 为空。该检查同时发现并修复了历史 CRLF/LF 物理字节哈希不可移植问题，数值内容未改变。
