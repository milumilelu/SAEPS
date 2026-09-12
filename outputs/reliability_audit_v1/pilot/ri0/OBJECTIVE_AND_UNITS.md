# Objective and units audit

The current implementation in `src/saeps/core.py` computes a residual-space, local Gauss–Newton quantity. With `J_w` the neural-state Jacobian and `J_p` the physical-parameter Jacobian,

`F_raw = J_p.T @ J_p`

and for finite `gamma > 0`,

`F_gamma = J_p.T [I - J_w (J_w.T J_w + gamma I)^(-1) J_w.T] J_p`.

`eta` is the diagonal ratio `diag(F_gamma)/diag(F_raw)`; it is not an uncertainty interval or an observation Fisher information matrix. The matrix-free path applies the same operator using JVP/VJP and conjugate gradients. The SVD helper implements an exact zero-damping projector only relative to the sampled neural-state tangent space.

For an SVD `J_w = U Sigma V.T`, the finite-damping residual operator has eigenvalues `gamma/(sigma_i^2+gamma)` on `range(J_w)` and one on its orthogonal complement. Hence finite damping is positive definite in residual space and generally leaves positive curvature for state-compensable directions. In the zero-damping limit, `F_0` removes `range(J_w)` and its kernel includes every parameter direction whose residual sensitivity lies in that range. These are local, checkpoint-dependent geometric statements; they do not establish structural or practical identifiability of the physical experiment.

Units: all curvature matrices are in squared residual units per squared parameter-coordinate unit. Changing loss weights or parameter coordinates changes their numerical values. An independent observation FIM must instead use the physical observation covariance `Sigma` and `J_y.T Sigma^{-1} J_y`; PDE penalty weights and neural-state damping are not automatically measurement information.

Historical counts in `HISTORICAL_ROOT_AUDIT.csv` are copied from machine-readable evidence files and retain every invalid/failed denominator. No historical output was modified.
