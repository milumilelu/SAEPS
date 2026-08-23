# V5 Semantic Gate Graph

机器权威版本为 `configs/v5/semantic_gate_graph.json`。

```text
V5.0 PASSED
 ├─ reconstruction artifacts (fixed sources, at most once, no scientific selection)
 ├─ V5.1 descriptive audit
 ├─ V5.2A engineering freeze
 │    └─ V5.2B 200--204 → evaluable count → scientific profile status → STOP
 ├─ V5.3A 210--212 [3/3]
 │    └─ V5.3B 213--214 [2/2]
 │         └─ one-shot V5.3C 215--224 → matrix primary status → STOP
 ├─ V5.4 cost audit
 └─ V5.5 → V5.6 final audit
```

所有runner fail-soft保存已合法计算对象。Selection nodes禁止读取协议排除的`D`、errors、favorable eigen information或plots。Confirmation authorization guard同时要求upstream gates、frozen hashes、clean source和zero prior output。
