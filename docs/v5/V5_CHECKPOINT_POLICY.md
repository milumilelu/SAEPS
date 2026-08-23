# V5 Checkpoint Persistence and Provenance Policy

所有V5重建或新训练模型必须同时写入：

1. reloadable `model_state.pt`，payload至少含有限`theta` tensor、coordinate及model metadata；
2. `checkpoint_manifest.json`，符合 `configs/v5/schemas/checkpoint_manifest.schema.json`；
3. diagnostic set的机器可读定义与hash。

写入仅允许在 `outputs/runs/v5/checkpoints/`。artifact先原子写入，计算SHA-256，再写manifest。manifest缺字段、artifact越界、hash不符、`torch.load(..., weights_only=True)`失败、theta非有限或source seed不在registry时，下游validator必须拒绝。

固定reconstruction key为`benchmark:source_seed`。同一key已有terminal manifest时禁止重训，包括失败manifest。任何retry/replacement均不被授权。

重建artifact不是历史checkpoint，不得宣称cross-environment bit identity或与V4 tensor相同。
