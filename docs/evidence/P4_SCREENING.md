# P4 Scalar Screening — Development Evidence

**Status:** `PASSED / LOCK_READY`  
**Run:** `p4-screening-s0-20260819T080159.676328+0000-56ebdbadfb52`  
**Implementation commit:** `296a4bb334a9603c0f9417042481abbd6e4bd6e3` (`git_dirty=false`)  
**Config hash:** `4f70ec215ed259c38d67271badce53c5773f84b7280b2989d0d2e614cb6b8847`

Only development seeds `[0,1,2]` and candidates `[Allen-Cahn,Burgers]` were used. No confirmation seed was run.

| Candidate | Hard gate | Stationarity | Reoptimization point failures | Classical median R2 | Nominal gamma alpha |
|---|---|---:|---:|---:|---:|
| Allen-Cahn | PASS | 3/3 | 0/21 | 0.9984252615077979 | 1e-10 |
| Burgers | PASS | 3/3 | 0/21 | 0.9998460719661915 | 1e-8 |

Both candidates passed forward finiteness, state RMSE, joint stationarity-count, classical positive-curvature/interior-minimum, reoptimization and Jacobian/CG gates. Selection remained tied through hard gates and stationarity count. Burgers was selected at the next preregistered criterion, higher classical curvature-profile clarity. Reoptimization failure rate and alphabetical tie-break were not needed.

Forbidden selection metrics—eta, SAEPS advantage, figure appearance, expected regime and validation-only parameter error—were not consulted. The unselected Allen–Cahn rows remain in the raw screening output.

The real-PINN development amendment changed the common profile window to `[-0.075,0.075]`, locked loss plateau to `0.002`, normalized gradient to `0.005`, fit R2 to `0.99`, and normalized fit RMSE to `0.03`. These changes preceded all confirmation runs and apply uniformly.

