# SCIENTIFIC_GATES.md — v2.0

## SG-1 Controlled Geometry

PASS 当且仅当：

\[
median_i\rho_{Spearman}(\alpha,\eta_i^{se})\ge0.9
\]

且至少 8/10 confirmation seeds 满足 LOCK 前定义的正确单调趋势。报告 all seeds、median、IQR、violations 和完整 denominator。

**Observed 2026-08-19:** `FAIL`. All 5 valid seeds were monotonic with Spearman approximately 1, but 5/10 seeds failed the locked checkpoint stationarity gate. The binding denominator is therefore 5/10 monotonic, below 8/10. Evidence: `docs/evidence/P2_ACCEPTANCE.md`.

## SG-2 Scalar Paired Comparison

定义 \(D_i=E_{raw,i}-E_{SAEPS,i}\)。

- `STRONGLY_SUPPORTED`: 至少 9/10 valid paired wins、\(median(D)>0\)、paired bootstrap 95% CI lower \(>0\)；
- `SUPPORTED_WITH_UNCERTAINTY`: 9/10 与 median positive，但 CI 跨 0；
- `PARTIALLY_SUPPORTED`: 轻微或不稳定优势；
- `NOT_SUPPORTED`: \(median(D)\le0\) 或 profiles 系统性不一致。

不得将 9/10 改成 9/N。SG-2 NOT_SUPPORTED 触发 P7 `PROTOCOL_STOP`。

**Observed 2026-08-19:** `PARTIALLY_SUPPORTED`. Only 1/10 seeds formed a valid pair; it had positive D, while eight locked profile fits failed and one checkpoint was invalid. The single-value bootstrap interval is degenerate and is not treated as strong evidence. Evidence: `docs/evidence/P5_ACCEPTANCE.md`.

## SG-3 Multi-parameter Ordering

PASS 当且仅当至少 9/10 valid confirmation seeds 满足：

\[
H_{prof}(v_{max})>H_{prof}(v_{min}),
\]

与 SAEPS eigendirection ordering 一致。必须同时报告 directional curvature ratio error。

**Observed 2026-08-19:** `FAIL`. Zero of ten seeds formed a valid directional profile pair; the denominator remains 0/10, not 0/0. Evidence: `docs/evidence/P6_ACCEPTANCE.md`.

## Robustness 与 Cost

P7 不设强阳性门槛。P8 未给定硬性成本比阈值；两者为描述性证据，不得事后发明 PASS 线。

**Observed P7:** 55/55 new runs completed with 43 PASS, 2 CHECKPOINT_INVALID and 10 SOLVER_FAILURE. Failure frequency concentrated under sparse observations and the wide architecture; valid-cell median elimination effects remained positive. This is descriptive only.

**Observed P8:** the median paired reoptimized-profile/SAEPS wall-time ratio was 2.0483 on three cost-only development seeds. The speedup is modest, not order-of-magnitude; peak native CPU tensor memory was not reliably available and is reported as null.

## Final Mapping

最终结论只能是 `SUPPORTED`、`PARTIALLY_SUPPORTED`、`NOT_SUPPORTED`；具体映射遵循 `docs/EXECUTION_CONTRACT.md` 第 20 节。

**Observed final mapping:** `PARTIALLY_SUPPORTED / INVESTIGATE_NUMERICS`. Numerical core checks passed and the single valid scalar pair was positive, but unresolved stationarity, CG and profile-fit failures prevent broad claims.
