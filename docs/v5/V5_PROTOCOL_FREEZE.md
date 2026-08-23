# V5 Effective Protocol Freeze

**冻结日期：** 2026-08-23

## Effective protocol identity

V5唯一有效科学协议是以下有序组合：

1. Parent protocol：commit `126f125a91b4e0df654e8aa7dacb68fded68c3a8`中的LF-normalized `V5_JCP_MINIMAL_PROTOCOL.md`，SHA-256 `6abb0864cddb40fd63f29a24d97004c539727744d35b2ac9821888d0a90d0f12`；用户提供的pre-normalization source bytes SHA-256为`274b1179ace363cdd61897c05c43001a9435cbbf2f8d0caa58ef09a7dd796b52`；
2. Pre-execution amendment：`docs/v5/V5_PROTOCOL_AMENDMENT_001.md`，SHA-256 `e197feb05404de5f5eb2a09b4e6c245f4e7248747a47b4cd626170d7fdaf83fd`。

冲突时Amendment 001优先。当前root protocol包含effective-protocol notice，其规范LF文件SHA-256为`28a262cc6c42d3838f6b3a3208237166d0b2e6a57d64b0aa1f769f817ca0f131`。

## Composite identity

对以下UTF-8 bytes计算SHA-256（每行以LF结尾）：

```text
parent_sha256=6abb0864cddb40fd63f29a24d97004c539727744d35b2ac9821888d0a90d0f12
amendment_sha256=e197feb05404de5f5eb2a09b4e6c245f4e7248747a47b4cd626170d7fdaf83fd
precedence=amendment_over_parent_on_conflict
```

**Effective protocol composite SHA-256：** `080a68cb3d8635b5c3ab660fccc1e65382ab852c20042e10c8fbacb080dde53c`

## Execution state

Amendment与freeze均在任何V5 scientific output产生前建立。V5.0完成不等于授权V5.1；所有phase config的execution flag保持`false`，等待用户后续明确指令。
