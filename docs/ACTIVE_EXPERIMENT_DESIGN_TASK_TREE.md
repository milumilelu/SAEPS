# SAEPS 主动实验设计任务树（AED-v1.0-DRAFT）

## 状态与边界

- **总状态:** `NOT_STARTED`
- **性质:** 新研究方向的执行规划；不是对既有 v2/v4/v5 协议的修订，也不是 confirmation 授权。
- **输入来源:** `任务说明/SAEPS_主动实验设计转向方案包.zip`，SHA256：`FA5C43A0FB2E1BB1A5DDF75D32C1303B5E9E36B4AEB89EF43D4E97CF6096F71E`。
- **历史保护:** `docs/LOCKED_PROTOCOL.md`、`configs/locked/`、既有 `outputs/runs/`、历史 `PROTOCOL_STOP` 和既有科学结论保持不变。
- **启动条件:** 完成治理节点后，仍需单独的用户/协议授权，才能创建 active-design 配置并运行数值实验。

## 树

```text
AED-0 主动实验设计分支（NOT_STARTED）
├── AED-1 治理与隔离（NOT_STARTED）
│   ├── AED-1.1 记录 ZIP、来源文件、基线 commit 和工作树状态
│   ├── AED-1.2 建立独立 namespace：configs/active_design_v1/
│   │   ├── outputs/runs/active_design_v1/
│   │   └── docs/evidence/active_design_v1/
│   ├── AED-1.3 明确 development / held-out / confirmation 的分离
│   └── AED-1.4 登记停止条件、偏差记录和 provenance schema
├── AED-2 低秩候选评分核心（NOT_STARTED）
│   ├── AED-2.1 固定 gamma、旧残差权重和局部线性化的 API
│   ├── AED-2.2 候选噪声白化与相关噪声联合白化
│   ├── AED-2.3 explicit / matrix-free / 直接重消元一致性
│   ├── AED-2.4 ΔF 半正定、solve-only 实现和成本计数
│   └── AED-2.5 将 ZIP 中 36 组代数检查标为先验工程证据，不当作方法验证
├── AED-3 动作、候选池与预算（NOT_STARTED）
│   ├── AED-3.1 冻结 action=(sensor_type,x,t,cost,noise_model) schema
│   ├── AED-3.2 在线时间因果规则与离线历史时刻规则
│   ├── AED-3.3 B1/B3/B4 候选池和三档预算的 development 设计
│   └── AED-3.4 禁止选择器读取未选候选真实读数
├── AED-4 开发基准与强基线（NOT_STARTED）
│   ├── AED-4.1 仅使用合格 checkpoint 和新分配的 development seeds
│   ├── AED-4.2 random / fixed-uniform / predictive-variance
│   ├── AED-4.3 nuisance-aware physical plug-in FIM（oracle 单列）
│   ├── AED-4.4 PIED-TIP 或可复现的明确实现
│   ├── AED-4.5 SAEPS acquisition、去状态补偿消融、gamma 敏感性
│   └── AED-4.6 保留全部失败、不可辨识和 profile 无效记录
├── AED-5 最小闭环试验（NOT_STARTED）
│   ├── AED-5.1 每个选定场景固定候选池并完成一次排序
│   ├── AED-5.2 执行一次真实加点与重新估计
│   ├── AED-5.3 B4 的时刻混淆、B3 的温度/热流混淆、B1 正面对照
│   └── AED-5.4 报告参数、可辨识组合、场误差和端到端成本
├── AED-6 开发门（NOT_STARTED）
│   ├── AED-6.1 工程正确性、stationarity、profile 和数据兼容性
│   ├── AED-6.2 预设的排序稳定性和预算收益判据
│   ├── AED-6.3 若不胜过物理 FIM，比较边际计算成本并收窄 claim
│   └── AED-6.4 形成独立 development gate 和是否申请新协议的决定
├── AED-7 新协议后的独立执行（NOT_STARTED；需授权）
│   ├── AED-7.1 锁定 active-design config、seed、候选池、阈值和聚合器
│   ├── AED-7.2 held-out / confirmation 闭环执行，不使用既有 [10..19]
│   ├── AED-7.3 生成每 run manifest、raw result、失败原因和 lineage
│   └── AED-7.4 自动聚合并保留完整 denominator
└── AED-8 审计与科学裁决（NOT_STARTED）
    ├── AED-8.1 figures / tables / summary 共享同一机器可读聚合源
    ├── AED-8.2 计算成本审计：measurement、selection、SAEPS、重训
    ├── AED-8.3 只允许 SUPPORTED / PARTIALLY_SUPPORTED / NOT_SUPPORTED
    └── AED-8.4 生成独立报告，不回写历史报告和锁定文件
```

## 依赖关系

`AED-1 → AED-2 → AED-3 → AED-4 → AED-5 → AED-6`。只有 AED-6 通过且获得新协议授权，才可进入 AED-7；AED-8 依赖 AED-7 的完整 raw outputs。任何 engineering gate 失败先修复实现，任何 scientific gate 失败如实记录并停止相应扩展。

