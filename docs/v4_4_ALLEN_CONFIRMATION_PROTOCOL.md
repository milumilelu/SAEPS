# v4.4 Allen--Cahn External Confirmation

> **HISTORICAL v4 PROTOCOL — not the current paper-facing evidence state.** See [`../V5_FINAL_JCP_AUDIT_REPORT.md`](../V5_FINAL_JCP_AUDIT_REPORT.md) for the V5 final audit. The protocol below remains preserved as executed history.

## Scope

This is the first external-PDE confirmation after v4.2 Burgers support. It tests whether the comparative scalar-curvature result replicates on the previously retained Allen--Cahn benchmark. It is not a corrected or repeated Burgers experiment.

## Frozen cohort and estimand

- planned seeds: `75--84`, no replacement or selective rerun;
- selected network: width 8, fixed before held-out seeds 73--74;
- primary gold: exact finite-`gamma` reduced Hessian;
- primary: paired `D=E_raw-E_SAEPS`;
- secondary: absolute SAEPS error, frozen GN indicator and gamma-matched nonlinear-profile bridge.

## Joint success rule

`SUPPORTED` requires all of:

1. valid pairs at least 8/10;
2. planned strict wins at least 8/10;
3. median valid-pair D greater than zero;
4. exact one-sided paired sign test `p<=0.05`.

Insufficient valid pairs is `NOT_SUPPORTED` with the reason retained. Profile or indicator failures cannot invalidate an otherwise valid exact-curvature pair, but they constrain the corresponding secondary claims.

## Execution discipline

The config, runner, aggregator, preflight, tests and semantic graph must be hash-locked before authorization. All seed records are fail-soft. After execution, the cohort is permanently closed regardless of outcome.
