# Amendment 018 — v4.6 Held-Out Isolation Recovery

**Date:** 2026-08-21  
**State:** engineering recovery; confirmation remains inactive

The first attempted held-out freeze was not committed. During its test command, a test written to expect a missing freeze invoked real seed103 after the freeze file appeared. Seed103 completed with `git_dirty=true` and the test then failed because no exception was raised. No comparative D/E or eigenspectrum was inspected or used.

Seed103 is permanently contaminated and retained as an implementation-failure attempt. Seed104 is not run. Neither may support held-out acceptance. The test is corrected to pass an unauthorized confirmation seed so it can never trigger real training, regardless of freeze presence.

Fresh held-out recovery seeds are fixed to `115--116`, outside untouched confirmation `105--114` and scalability `120--124`. All executable settings and scientific thresholds remain unchanged. Both fresh seeds must pass the complete frozen binding chain before confirmation can be locked. This amendment is caused solely by execution semantics, not numerical or scientific outcomes.
