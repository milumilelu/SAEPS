# V3.5 Second-Order Diagnostic and Engineering Acceptance

## Outcome

- Engineering validation: `PASSED`
- Valid second-order decompositions: `8`
- New development center validity: `4/5`
- Selected solver validity: `4/4` valid centers
- Held-out development: center `2/2`, solver `2/2`
- Confirmation 30--44: not authorized

## Scientific diagnostic

Residual-Hessian Shapley decompositions show that GN error is governed by signed interaction and cancellation among `S_theta_theta`, `S_theta_lambda`, and `S_lambda_lambda`; individual block norm ratios are poor trust indicators.

The preregistered first-order reduced-correction candidate is the strongest development indicator:

- Spearman with actual GN error: `0.8095` over 8 valid seeds;
- same 5% classification: `8/8`;
- median absolute calibration error: `0.0345`.

Because six candidates were evaluated and no untouched confirmation seed was used, this remains a promising development-selected indicator, not a validated self-certification rule.

## Engineering

Baseline exact-trust center passes `2/5` new seeds. The frozen baseline-then-rescue policy recovers two more and passes `4/5`; seed27 remains invalid. Two-pass scaled-LSQR refinement passes all `4/4` valid centers, including `2/2` held-out seeds. It requires 1500 total LSQR iterations and 65 exact-development setup JVPs per seed, so practical scalability is not yet established.

## Comparative estimand

Across all eight valid development seeds:

- `D=Eraw-Esaeps > 0`: `8/8`;
- median `D`: `28.3801`;
- minimum `D`: `21.3964`.

Thus SAEPS can have 10--20% absolute GN-to-exact error and still be dramatically closer to the exact reduced geometry than raw sensitivity. The comparative endpoint is supported as the appropriate candidate primary estimand for a future untouched confirmation protocol, but no confirmation claim is made here.

## Decision

V3.5 is ready to support drafting a separate confirmation lock. Before any seed 30--44 is run, that lock must freeze the selected center/solver, indicator reporting, paired comparative hypothesis, planned denominator, and statistical rule. This acceptance does not itself authorize confirmation.

