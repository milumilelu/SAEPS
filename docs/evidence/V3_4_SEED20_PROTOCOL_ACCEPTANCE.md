# V3.4 Seed-20 Protocol Acceptance

- Run: `v3-4-curvature-s20-20260819T160211.376626+0000-1472845aab14`
- Clean implementation commit: `37e057c0a73c2f2897c60351c91fb64521779328`
- Config hash: `89374e212ee3960d944600d08b4c18821db6d7622096fabe81334dd10949ec6f`
- Engineering gate: `PASSED`
- Readiness gate: `PASS`
- Seeds 21--24: authorized under the unchanged v3.4 configuration
- Confirmation 30--44: forbidden

The curvature solver gate passed with both standard CG and augmented LSQR. The nonbinding score solver and Jacobi-PCG diagnostics failed and remain recorded. Explicit GN versus exact gamma reduction error was `0.0117243`.

Profile scales `h=0.05` and `0.025` were `CERTIFIED`. Scales `0.0125` and `0.00625` were classified `RESOLUTION_LIMIT`, with strict optimization-curvature relative budgets approximately `0.06` and `0.22`. The two certified scales passed exact-reference agreement. Branch-audit output was complete; maximum parent-relative function distance was `0.00542124`.

