# v3.6 Confirmation Lock Acceptance

**Status:** `PASSED`  
**Protocol state:** `LOCKED_NOT_EXECUTED`  
**Execution authorized:** `false`  
**Confirmation runs executed:** `0`

## Locked identity

- First lock commit: `4eb28f54bda7133efb317211ecd3833afd8d510b`
- Locked config: `configs/v3_6/locked_scalar_confirmation.yaml`
- Raw SHA-256: `b52b9a16a16d557bd7f9b13a6a59825295ccae1d72d415b3234dfa2344e31f99`
- Planned seeds: exactly `30--44`, 15 total, no replacement

The current config bytes equal the bytes stored in the first lock commit. The v2 scalar config, v3.5 development config and v3.5 frozen engineering-choice hashes all match their registered sources.

## Frozen scientific decision

The primary estimand is paired `D=Eraw-Esaeps` against the exact finite-gamma reduced Hessian. `SUPPORTED` requires at least 12 valid pairs, at least 12 strict wins in the planned denominator of 15, positive valid-pair median D and a one-sided exact sign-test p-value at most 0.05. Invalid planned seeds remain planned non-wins.

Absolute `E_SAEPS` median, linear-quantile IQR, range, all values and 5% count are secondary. The 5% threshold is not a universal accuracy requirement. The first-order GN indicator and its 5% classification are frozen as a nonbinding secondary diagnostic.

## Static verification

- `44 passed`; no experiment runner was invoked.
- `python scripts/26_validate_v3_6_lock.py --write-evidence`: exit `0`.
- All seven static checks passed.
- No path matching `outputs/runs/v3_6*` exists.

The evidence JSON is `docs/evidence/v3_6_lock_validation.json`. No claim about confirmation performance is made.
