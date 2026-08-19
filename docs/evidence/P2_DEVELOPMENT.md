# P2 Controlled Geometry — Development and Phase-Lock Evidence

**Status:** `PASSED / PHASE_LOCK_READY`  
**Development date:** 2026-08-19  
**Validated implementation commit:** `bc2fe2952b7fed19fb61a788212c1fc30a1dbf3a`  
**Development run:** `p2-development-s0-20260819T072005.205758+0000-bc9e08a3bcd1`

## Separation and provenance

- Development seeds were exactly `[0,1,2]`; no confirmation seed was executed.
- Run provenance records the implementation commit above and `git_dirty=false`.
- Development config hash: `439c80c7e16611f913f05cfb6aa7e60aefcefc3a7bea6e3061583879c93b26bd`.
- Generated phase-lock hash: `32003edbcfbe03c6bf357ffce25051ba9b279263a15d2e80b4c762087ec0c30e`.
- Actual wall time: `75.76872750000621` seconds.

## Actual controlled problem

The benchmark uses

\[
u_t-0.05u_{xx}+u=\lambda q_\alpha+s_\alpha,
\quad \lambda^*=1,
\]

with locked truth

\[
u^*=\sin(\pi x)e^{-t}+0.2\sin(3\pi x)\sin(2\pi t).
\]

All source families share this truth through manufactured forcing. The trained state is a float64 `tanh_mlp_2x8x1`; the fixed tensor grid is shared by training and diagnostic evaluation.

## Checkpoint development evidence

| Seed | Training loss | Diagnostic S_theta | State RMSE (validation-only) | SVD rank |
|---:|---:|---:|---:|---:|
| 0 | 0.009744618304600173 | 0.0021225260694753708 | 0.041770659159763086 | 33 |
| 1 | 0.07821128438890147 | 0.008324317256809884 | 0.09020897545422792 | 32 |
| 2 | 0.0025827410815752534 | 0.002124953301007418 | 0.016971458480637434 | 33 |

The phase lock fixes training loss `<=0.1` and diagnostic `S_theta<=0.01`. Confirmation failures remain visible as `CHECKPOINT_INVALID`.

## Fourier screening

The selection statistic is the median development tangent-space overlap. All 20 candidate medians are retained here:

| Candidate | Median overlap | Candidate | Median overlap |
|---|---:|---|---:|
| sin1x_constantt | 0.8691753394141035 | sin3x_constantt | 0.8952557670484286 |
| sin1x_cos1t | 0.9470949584964850 | sin3x_cos1t | 0.9556278133743641 |
| sin1x_cos2t | 0.9442111334237078 | sin3x_cos2t | 0.9669695554441681 |
| sin1x_sin1t | 0.8787740766531298 | sin3x_sin1t | 0.9026637227055336 |
| sin1x_sin2t | 0.9132554827492317 | sin3x_sin2t | 0.9744552801695352 |
| sin2x_constantt | 0.9184642086993666 | sin4x_constantt | 0.7472291536969442 |
| sin2x_cos1t | 0.9563934428331212 | sin4x_cos1t | 0.8537456502364329 |
| sin2x_cos2t | 0.9644914718579030 | sin4x_cos2t | 0.9471587205575321 |
| sin2x_sin1t | 0.9269147519812678 | sin4x_sin1t | 0.7627093039476647 |
| sin2x_sin2t | 0.9533162142756603 | sin4x_sin2t | 0.8984628305771303 |

The deterministic rules selected:

- `q_parallel = sin3x_sin2t` (maximum median overlap `0.9744552801695352`);
- `q_perpendicular = sin4x_constantt` (minimum among candidates orthogonal to `q_parallel`, median `0.7472291536969442`);
- empirical normalized inner product `3.0357660829594124e-18`.

The labels refer to tangent-explainable and relatively transverse directions; they do not claim exact zero transverse/parallel components.

## Gamma selection

The complete alpha grid was `[1e-12,1e-10,1e-8,1e-6,1e-4,1e-2]`. Eligibility was `[false,true,true,true,true,true]`. At `1e-12`, seed 1 reached maximum CG residual `7.92133854771725e-9` but explicit/MF error `5.649994122727536e-6`, exceeding `1e-6`.

Adjacent explicit-eta relative changes were:

```text
[0.011046771439529217,
 0.12327065300820524,
 0.4622256502079963,
 0.5694930298713532,
 0.7309378021669132]
```

The locked algorithm therefore selected the first CG-eligible point whose explicit eta changes by at most 5% from the preceding smaller gamma: `gamma_alpha=1e-10`. This selection used no confirmation result.

## Authorization

The generated files `configs/locked/controlled_geometry.yaml` and `.sha256` must be committed unchanged. Only after that clean lock commit may `scripts/03_run_controlled_confirmation.py` run.

