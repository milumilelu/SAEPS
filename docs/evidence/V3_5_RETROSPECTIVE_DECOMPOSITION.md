# V3.5 Retrospective Second-Order Decomposition

- Run: `v3-5-retrospective_diagnostic-s20-20260820T013547.321155+0000-4efb89fce19b`
- Clean implementation commit: `8ce1d38cf788b477c5d9d6c7f2f27b3b8cd26609`
- Config hash: `a39f7b922e3769fab21b3e923428c6adec2514ab33402e5a8e165e0ee0bb93fd`
- Seeds: `20,22,23,24`
- Engineering: `PASSED`

All Shapley decompositions reproduce exact-minus-GN within the registered tolerance. The block contributions show strong cancellation and change sign across seeds:

| Seed | GN error | Shapley Sθθ | Shapley Sθλ | Shapley Sλλ |
|---:|---:|---:|---:|---:|
| 20 | 1.17% | -2.74 | +7.07 | -4.75 |
| 22 | 8.24% | +0.05 | +1.63 | -3.33 |
| 23 | 9.33% | +1.52 | +0.85 | +0.85 |
| 24 | 4.97% | -1.29 | +1.55 | -1.47 |

The first-order reduced-correction ratio has four-point Spearman `0.8` with GN error. Individual block ratios and absolute-Shapley magnitude are not stable monotone predictors; several correlate in the opposite direction because cancellation, not raw block magnitude, determines the scalar reduced correction. No stable trust indicator is claimed from four retrospective seeds.

For all four seeds, paired `D=Eraw-Esaeps` is strongly positive: raw relative errors are approximately `21.4,44.1,24.4,30.6`, whereas SAEPS errors are `0.0117,0.0824,0.0933,0.0497`. This is development evidence for comparative superiority, not confirmation.

