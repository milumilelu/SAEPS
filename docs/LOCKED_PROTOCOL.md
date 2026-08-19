# LOCKED_PROTOCOL.md

**状态:** `UNLOCKED`  
**警告:** 本文件当前是模板，不授权任何 confirmation run。

只有 P0–P4 engineering gates 通过、development decisions 完成且所有待定项被解析后，才能将状态改为 `LOCKED`。

## Lock Metadata

```yaml
status: UNLOCKED
contract_id: SAEPS-JCP-EXEC-v2.0
lock_date: null
git_commit: null
decision_id: null
locked_config_hashes: {}
```

## 必须锁定的内容

- benchmark/source/parameter coordinates；
- architecture/dtype/hardware policy；
- points/sensors/loss weights；
- optimizer/stopping/stationarity；
- profile/fit/missing-point rules；
- gamma/plateau rule；
- bootstrap specification；
- robustness seeds and architectures；
- aggregation/scientific-gate/artifact code hashes。

LOCK 后不得原地修改。任何后续科学设计变更必须新建协议版本、config namespace 和 split。

