# V5 Seed Registry

机器权威版本为 `configs/v5/seed_registry.yaml`。

| Role | Seeds/checkpoints | Replacement | Scientific selection |
|---|---|---|---|
| Burgers reconstruction | 45--47 | 禁止 | 固定历史source rule |
| Allen reconstruction/profile engineering | 70--74 | 禁止 | 固定历史source rule |
| V5.4 base reconstruction | 120 | 禁止 | V4.7最小registered checkpoint ID |
| Profile held-out | 200--204 | 禁止 | planned denominator 5 |
| Two-param development | 210--212 | 禁止 | center/numerics only |
| Two-param held-out | 213--214 | 禁止 | byte-frozen |
| Two-param confirmation | 215--224 | 禁止 | planned denominator 10 |

永久保护至少包括`30--44`、`55--69`、`75--84`、`90--99`、`105--114`；所有V2--V4.8 outputs均只读。
