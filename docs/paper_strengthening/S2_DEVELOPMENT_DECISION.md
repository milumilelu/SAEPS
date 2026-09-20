# S2 development decision

状态：`FAILED`（profile fit-quality engineering gate）；没有授权新的 confirmation。

第一轮 development 队列的 9 个 profile records 均完成了独立优化、stationarity 和 exact local-minimum gate，但这不足以形成可审计的局部二次 profile。随后对预先列明的四类 fit window 运行了只读审计，保持 P3 的 R²、normalized RMSE、design-condition 和正曲率门槛不变。

| window | 保留尺度数 | fit-quality PASS | 中位 normalized RMSE |
|---|---:|---:|---:|
| `all_common_scales` | 3 | 0/9 | 0.00034623549 |
| `two_finest_scales` | 2 | 0/9 | 0.00011442401 |
| `finest_pair_only` | 1 | 7/9 | 1.0257597e-15 |

预声明选择规则在未改变阈值的情况下选择 `all_common_scales` 作为诊断基准，但 `selected_window_passes_all_records` 为 `false`。因此本阶段不能把 profile 扩展成独立 scientific evidence。

该失败被归类为 profile numerical/scientific limitation：profile point 的可优化性通过，而有限步长下的局部二次拟合没有在完整 development cohort 上通过。不得缩小 fit window、放宽阈值、删除 seed 或用单一 finest pair 的恰合拟合替代多尺度证据。后续应采用 Claim Ledger 的收缩主张，除非用户另行授权一份新协议。

- 首轮 arm 选择记录：`docs/paper_strengthening/S2_INITIAL_ARM_SELECTION.md`
- fit-window 机器结果：`outputs/runs/paper_strengthening_v1/s2_profile_development/S2_FIT_WINDOW_SUMMARY.json`
- 当前配置状态：`configs/paper_strengthening/locked_profile.yaml`（`FAILED`，不可用于 confirmation）
- lock record：`configs/paper_strengthening/LOCKED_PROFILE_SHA256.json`
