# Amendment 017 — v4.6 Two-Parameter Exact Geometry

**Date:** 2026-08-21  
**State:** development authorization only

V4.5 is permanently closed as `NOT_SUPPORTED`; its conditional monotonic mechanism evidence and center-availability failure are both retained. This amendment activates the next ordered v4 node without modifying any historical result.

The retained coupled reaction-diffusion benchmark is evaluated on fresh development seeds `100--104` and untouched confirmation seeds `105--114`. Engineering seeds are `100--102`; seeds `103--104` are held out until an executable freeze. Confirmation remains inactive until a separate lock and one-shot authorization.

The primary geometric objects are the full matrices `F_raw`, explicit/matrix-free `F_se^GN`, and the exact finite-gamma reduced Hessian. Coordinatewise eta is not primary. The stable generalized eigenproblem uses `F_raw + tau I`, with `tau=1e-10*max(trace(F_raw)/2,1)`, and eigenvectors normalized in that metric. Development must establish nontrivial coupling, exact-Hessian availability, state-local-minimum availability and two-column solver validity without selecting settings using comparative D.

The candidate future confirmation endpoint is paired Frobenius error improvement `D=E_raw-E_SAEPS` against exact finite-gamma reduced geometry, with at least 8/10 valid pairs, 8/10 planned strict wins, positive median D and a one-sided exact sign test at 0.05. Generalized eigendirections, condition number and coupling are mandatory secondary matrix evidence. A 5x5 nonlinear surface is restricted to the first valid confirmation seed by ascending locked rule.
