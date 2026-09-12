# SAEPS-Active 论文方法与实验任务树（AED-v0.2-DRAFT）

## 状态与来源

- **总状态:** `NOT_STARTED`
- **性质:** 论文导向的新方法与实验方案；proposal-only，不是执行授权。
- **最新来源:** `任务说明/SAEPS_Active_论文方法与实验方案包.zip`。
- **ZIP SHA256:** `09745BC5B254B49184774260E905CA7B88DE8F1B6BF32BB36993CD0152A285DD`
- **历史保护:** `docs/EXECUTION_CONTRACT.md`、`docs/LOCKED_PROTOCOL.md`、`configs/locked/`、历史 outputs、既有 `PROTOCOL_STOP` 和历史科学结论不变。
- **论文主线:** 目标导向的序贯测量设计；输入是已有逆 PINN，输出是下一次测量动作，评价标准是目标误差—测量/计算成本，而不是新增一个诊断图。

## 任务树

```text
AED-0 论文定位与治理（NOT_STARTED）
├── AED-0.1 固定论文问题、贡献边界与禁止外推
├── AED-0.2 记录新 ZIP/manifest/hash、基线 commit 和工作树状态
├── AED-0.3 建立 active_design_v2 namespace 与 seed/split 方案
└── AED-0.4 取得单独协议授权；此前禁止新 PINN/主动闭环
├── AED-1 完整目标与信息权限（NOT_STARTED）
│   ├── AED-1.1 固定 xi=log(p/p_ref)、z=(theta,nu)、目标 g(xi)
│   ├── AED-1.2 统一观测/物理残差白化与固定求积权重
│   ├── AED-1.3 禁止候选标签、测试真值和真值 FIM 进入策略
│   └── AED-1.4 明确时间可行性、测量成本和重启成本
├── AED-2 条件约化增量与目标评分（NOT_STARTED）
│   ├── AED-2.1 实现 M=AᵀA+Gamma_z、Z=M⁻¹AᵀB、F
│   ├── AED-2.2 实现候选 E_a、S_a、Delta_a=E_aᵀS_a⁻¹E_a
│   ├── AED-2.3 固定目标导向 A-opt 代理 U(a)/cost
│   └── AED-2.4 保留 full-parameter/null-direction 目标，不静默删维
├── AED-3 收益上界筛除（NOT_STARTED）
│   ├── AED-3.1 实现 U(a) ≤ U_upper(a)
│   ├── AED-3.2 上界排序、精算、并列规则和停止条件
│   ├── AED-3.3 全候选精算对照，验证同一局部代理的选择一致性
│   └── AED-3.4 记录最坏情况回退、求解次数、wall time 和内存
├── AED-4 E0 代数与输入隔离（NOT_STARTED）
│   ├── AED-4.1 explicit/matrix-free/直接重消元一致性
│   ├── AED-4.2 噪声白化、重复 PDE 点权重和完整目标不变性
│   ├── AED-4.3 候选标签隔离和 world/action/replicate 索引检查
│   └── AED-4.4 仅作为工程 gate，不冒充主动反演效果
├── AED-5 E1 候选排序与真实重反演（NOT_STARTED；首要开发门）
│   ├── AED-5.1 固定 checkpoint、候选池和目标，盲选并锁定动作
│   ├── AED-5.2 追加观测、统一预算重反演和独立噪声副本
│   ├── AED-5.3 比较预测 U、实际目标收益和 top-action regret
│   └── AED-5.4 若“矩阵正确但排序无效”，停止扩大主动实验
├── AED-6 E2/E3 机制实验（NOT_STARTED；依赖 AED-5）
│   ├── AED-6.1 B4→B5：同快照空间加密 vs 新时间信息
│   ├── AED-6.2 B3→B6：扩散率目标 vs (k,C) 全参数目标
│   ├── AED-6.3 温度/热流成本与同成本对照
│   └── AED-6.4 保留只有温度时共同尺度不可解除的负对照
├── AED-7 E4 二维工程化导热（NOT_STARTED；依赖 AED-6）
│   ├── AED-7.1 两个以上独立空间模态，避免单模态假辨识
│   ├── AED-7.2 独立有限差分/有限体积生成器与高精度物理逆求解器
│   └── AED-7.3 同一观测集合交给独立求解器重估计
├── AED-8 E5 筛除效率与必要消融（NOT_STARTED；依赖 AED-5）
│   ├── AED-8.1 候选池 64/256/1024 的全评价 vs 筛除
│   ├── AED-8.2 nuisance、条件因子、目标导向、关闭筛除四项消融
│   └── AED-8.3 只做有限阻尼/设计正则敏感性
└── AED-9 统计、审计与科学裁决（NOT_STARTED）
    ├── AED-9.1 目标误差—累计成本、AUBC、终点误差和达标成本
    ├── AED-9.2 独立数据世界配对聚合，保留完整 denominator
    ├── AED-9.3 measurement/computation/selection/refit 成本审计
    └── AED-9.4 只输出 SUPPORTED/PARTIALLY_SUPPORTED/NOT_SUPPORTED
```

## 推进顺序

`AED-0 → AED-1 → AED-2 → AED-3 → AED-4 → AED-5 → AED-6 → AED-7/AED-8 → AED-9`。
AED-5 是首要真实证据门；在它显示排序有可解释的实际收益前，不启动大规模主动轨迹。每个阶段必须先通过 engineering gate，科学失败如实记录，不得换题、删 seed 或降低门槛修复。

