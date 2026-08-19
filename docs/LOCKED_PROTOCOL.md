# LOCKED_PROTOCOL.md

**状态:** `LOCKED`  
**警告:** confirmation 配置已冻结；禁止依据 confirmation 结果修改。

## Lock Metadata

```yaml
status: LOCKED
contract_id: SAEPS-JCP-EXEC-v2.0
lock_date: 2026-08-19
lock_basis_commit: 66c58f416d184546f93c4c0c0341cc8b83ada51a
lock_commit: ad794ca2908c8935d0e21702fab7914ff944cce7
decision_id: D-003
locked_config_hashes:
  scalar: cb5c2e9e3eee2d5462dd92ac0b9cd3b2b607ea487367d9c83b18a3a8af9c5cf8
  multi: b985ccee5cf2daf5c40a4226a3e4bf8aa7c47e7dbbb3e4792e04c47a7082b9bb
  robustness: 058decc716579f7129157d61917eceb1a557273b7bfa57ef1b57e66c904a8859
  p3_profile: 1389ffa4cb0ca45dae9b80c995e71c40f94d3fbfe277a631e61be0b0676fdb3c
```

## Locked content

- benchmark/source/parameter coordinates；
- architecture/dtype/hardware policy；
- points/sensors/loss weights；
- optimizer/stopping/stationarity；
- profile/fit/missing-point rules；
- gamma/plateau rule；
- bootstrap specification；
- robustness seeds and architectures；
- aggregation/scientific-gate/artifact code hashes。

All items above are frozen in `configs/locked/scalar.yaml`, `multi.yaml`, and `robustness.yaml` plus the following policies:

- Python 3.12.13, pinned dependencies, float64 CPU primary policy;
- development seeds `[0,1,2]`, confirmation seeds `[10..19]`;
- scalar benchmark Burgers selected solely by the preregistered screening order;
- CRD joint coordinates `[log_a,log_b]`;
- independent profile initialization, no continuation, locked optimizer/stopping/fit rules;
- scalar `gamma_alpha=1e-8`; multi `gamma_alpha=1e-8`;
- paired percentile bootstrap, 10,000 resamples, RNG seed 20260819;
- robustness seeds `[10..14]`, 3 noise × 3 observation fractions, widths 8/16/32;
- timing uses `perf_counter` wall time and records hardware/dtype/config/commit; peak memory is reported only when reliably available;
- no post-confirmation threshold, source, architecture, sensor, profile, gamma or denominator changes.

## Frozen artifact code hashes

```yaml
scalar_runner: 3eef96a13e624b2ce87f17e90a8dfbe8ee5ee5284de5e6fe9abf2c6564fbbeaa
scalar_aggregation: 0bdc1774f7b675d22d0ff9df8945c47dc5e03c730696100f725585cd85bc72b6
multi_runner: 597d453e62b6b73fd2166c8eade6c040dbe1aa02993c452a77d7f8884430aefa
multi_aggregation: 318ba79b8743f51027a470676ee39588c1b35f74634fbf262e45dfe01903695e
```

LOCK 后不得原地修改。任何后续科学设计变更必须新建协议版本、config namespace 和 split。
