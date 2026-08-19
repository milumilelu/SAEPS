"""Residual-first abstractions shared by every benchmark."""

from __future__ import annotations

from collections.abc import Mapping

import torch


def stack_weighted_residuals(
    blocks: Mapping[str, torch.Tensor],
    weights: Mapping[str, float],
) -> torch.Tensor:
    if not blocks:
        raise ValueError("at least one residual block is required")
    if set(blocks) != set(weights):
        raise ValueError("residual blocks and weights must have identical keys")
    pieces: list[torch.Tensor] = []
    reference_dtype: torch.dtype | None = None
    reference_device: torch.device | None = None
    for name, values in blocks.items():
        if not torch.is_tensor(values) or not values.is_floating_point():
            raise TypeError(f"residual block {name!r} must be a floating tensor")
        weight = float(weights[name])
        if not weight > 0.0:
            raise ValueError(f"residual weight {name!r} must be positive")
        if reference_dtype is None:
            reference_dtype = values.dtype
            reference_device = values.device
        if values.dtype != reference_dtype or values.device != reference_device:
            raise ValueError("all residual blocks must share dtype and device")
        pieces.append(values.reshape(-1) * weight**0.5)
    result = torch.cat(pieces)
    if not torch.all(torch.isfinite(result)):
        raise ValueError("weighted residual contains non-finite values")
    return result

