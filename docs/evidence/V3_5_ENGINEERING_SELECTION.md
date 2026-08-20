# V3.5 Engineering Selection

- Run: `v3-5-engineering_selection-s25-20260820T014248.296550+0000-d89c5dbb178a`
- Seeds: `25,26,27`
- Config hash: `a39f7b922e3769fab21b3e923428c6adec2514ab33402e5a8e165e0ee0bb93fd`
- Clean provenance: `PASS`

Baseline center passes `1/3`; the preregistered extended exact-trust rescue recovers seed25 and raises selected-center validity to `2/3`. Seed27 remains invalid with two negative directions after the fixed rescue budget. Thresholds are unchanged.

Among the two valid centers, standard CG, augmented LSQR and single-pass scaled LSQR pass `0/2`. Two-pass scaled-LSQR iterative refinement passes `2/2`, with verified original normal residuals approximately `2.87e-13` and `5.99e-15`. It is selected by the preregistered lexicographic rule.

The selected solver requires `1500` total LSQR iterations and an exact-development diagonal setup costing `65` JVPs. It is a valid held-out development candidate, not yet a demonstrated practical scalable method.

The engineering seeds have GN-to-exact errors `15.75%` and `10.98%` on valid centers. Comparative `D` remains strongly positive. These values do not enter the engineering selection rule.

