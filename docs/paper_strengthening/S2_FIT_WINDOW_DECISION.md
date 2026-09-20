# S2 fit-window development audit

工程门：`FAILED`；fit-quality threshold 保持 P3 锁定值，未放宽。

| window | retained h scales | fit-quality PASS | median normalized RMSE |
|---|---:|---:|---:|
| `all_common_scales` | 3 | 0/9 | 0.00034623549 |
| `two_finest_scales` | 2 | 0/9 | 0.00011442401 |
| `finest_pair_only` | 1 | 7/9 | 1.0257597e-15 |

按预声明规则选择 `all_common_scales`，但该 window 的全部记录通过条件为 `false`。

由于没有一个候选 window 在全部保留 records 上同时通过未改变的 R²、normalized RMSE、design-condition 和正曲率门槛，S2 不能形成可用于独立 confirmation 的 profile fit freeze。该结果保留所有 raw records，不能通过缩小窗口、放宽 threshold 或删除 seed 修复。

机器可读结果：`outputs/runs/paper_strengthening_v1/s2_profile_development/S2_FIT_WINDOW_SUMMARY.json`
