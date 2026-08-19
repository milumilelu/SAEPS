# EXPERIMENT_SPEC.md

**状态:** `DRAFT / DEVELOPMENT_ONLY`  
**协议:** `SAEPS-JCP-EXEC-v2.0`

本文件保存 development 阶段的具体实验设计。任何 confirmation run 开始前，以下项目必须全部解析、经 development evidence 支持，并转录到 `docs/LOCKED_PROTOCOL.md`。

## 固定项目

```yaml
development_seeds: [0, 1, 2]
confirmation_seeds: [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
gamma_alpha: [1e-12, 1e-10, 1e-8, 1e-6, 1e-4, 1e-2]
scalar_candidates: [Allen-Cahn, Burgers]
multi_parameter_benchmark: coupled-reaction-diffusion
multi_parameter_coordinates: [log_a, log_b]
profile_points_default: [-0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15]
```

## LOCK 前待确定

- [ ] Python、依赖、dtype 和 hardware policy；
- [ ] controlled PDE、truth、Fourier library 和 source normalization；
- [ ] network architecture；
- [ ] training/diagnostic/sensor layouts；
- [ ] loss weights；
- [ ] optimizer、stopping 和统一追加训练规则；
- [ ] residual/stationarity thresholds；
- [ ] profile interval、fit window、fit quality 和 missing-point rules；
- [ ] nominal gamma algorithm 与 plateau tolerance；
- [ ] bootstrap CI method、resamples、RNG seed、invalid-pair rule；
- [ ] robustness 5-seed list；
- [ ] narrow/wide architecture definitions；
- [ ] timing and memory measurement policy；
- [ ] artifact scripts freeze point。

任何决定必须引用 `docs/DECISIONS.md` 中的 development evidence。

