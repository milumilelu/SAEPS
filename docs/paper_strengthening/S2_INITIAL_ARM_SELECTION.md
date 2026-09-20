# S2 development decision

状态：`PASSED`（development engineering gate）；未授权新的 confirmation。

本阶段只读复用 V5 Allen–Cahn checkpoints 70–72，所有输出写入 `paper_strengthening_v1`。三组 arm 在执行前已写入 development 配置；选择规则只读取 profile point 通过数、曲率分辨率变化和 exact finite-γ reference 误差，禁止读取 D、E_raw、E_SAEPS、eta 或图形外观。

| arm | all-points-pass seeds | profile points | median last-two change | median exact-reference error |
|---|---:|---:|---:|---:|
| `standard_grid_tol_1e-6` | 3/3 | 24/24 | 0.014891153 | 0.0088767029 |
| `standard_grid_tol_1e-7` | 3/3 | 24/24 | 0.0039570353 | 0.0044019889 |
| `coarse_grid_tol_1e-7` | 3/3 | 24/24 | 0.0031946405 | 0.0063498681 |

按预声明规则冻结 `coarse_grid_tol_1e-7`。冻结后的步长为 `[0.08, 0.04, 0.02, 0.01]`，normalized-gradient threshold 为 `1e-07`。所有 9 个 raw records 均为 `PASS`，没有缺失点或静默排除。

该结论只说明 development 阶段可以稳定测量这组有限 γ profile；它不等价于 nonlinear profile scientific support，也不授权新的 confirmation。下一阶段若执行，必须另行授权并使用此 hash 可追溯的规则。

- locked config: `configs/paper_strengthening/locked_profile.yaml`
- lock record: `configs/paper_strengthening/LOCKED_PROFILE_SHA256.json`
- fit audit: `outputs/runs/paper_strengthening_v1/s2_profile_development/S2_FIT_QUALITY_AUDIT.json`
- source config SHA256: `3fb293b944336cb6ba50aeb93ab5ecac5b3d9f0bb4bb387e0f6f4aa23938dc6a`
- development summary SHA256: `d7e6f572754f6a02ca28eff9a2b06d43fa6928572228c4428c7dfbde51db6ace`
