# Objective and units audit

The current implementation in `src/saeps/core.py` computes a residual-space, local Gauss–Newton quantity. With `J_w` the neural-state Jacobian and `J_p` the physical-parameter Jacobian,

`F_raw = J_p.T @ J_p`

and for finite `gamma > 0`,

`F_gamma = J_p.T [I - J_w (J_w.T J_w + gamma I)^(-1) J_w.T] J_p`.

`eta` is the diagonal ratio `diag(F_gamma)/diag(F_raw)`; it is not an uncertainty interval or an observation Fisher information matrix. The matrix-free path applies the same operator using JVP/VJP and conjugate gradients. The SVD helper implements an exact zero-damping projector only relative to the sampled neural-state tangent space.

For an SVD `J_w = U Sigma V.T`, the finite-damping residual operator has eigenvalues `gamma/(sigma_i^2+gamma)` on `range(J_w)` and one on its orthogonal complement. Hence finite damping is positive definite in residual space and generally leaves positive curvature for state-compensable directions. In the zero-damping limit, `F_0` removes `range(J_w)` and its kernel includes every parameter direction whose residual sensitivity lies in that range. These are local, checkpoint-dependent geometric statements; they do not establish structural or practical identifiability of the physical experiment.

Units: all curvature matrices are in squared residual units per squared parameter-coordinate unit. Changing loss weights or parameter coordinates changes their numerical values. An independent observation FIM must instead use the physical observation covariance `Sigma` and `J_y.T Sigma^{-1} J_y`; PDE penalty weights and neural-state damping are not automatically measurement information.

Historical counts in `HISTORICAL_ROOT_AUDIT.csv` are copied from machine-readable evidence files and retain every invalid/failed denominator. No historical output was modified.

## Exact reduced curvature and profile distinction

For a weighted least-squares objective `L(w,p)=1/2 r(w,p)^T W r(w,p)` and a stationary nuisance state `w*(p)`, the exact implicit-function reduced Hessian is

`H_profile = H_pp - H_pw H_ww^{-1} H_wp`,

provided `H_ww` is nonsingular (normally SPD on the retained state subspace). Here each `H_ab` is a block of the full objective Hessian and includes residual second-derivative terms. Replacing these blocks by Gauss–Newton blocks yields a local approximation; adding a state anchor `gamma R` changes the eliminated block to `H_ww + gamma R` and therefore changes the profile itself. A nonstationary checkpoint has no valid implicit profile curvature under this formula.

For a separable linear nuisance amplitude, variable projection minimizes that nuisance exactly at each physical parameter. Its profile derivative contains the derivative of the nuisance projection as the physical parameter changes; it is a nonlinear profile reference, not simply `J_p^T P_gamma J_p` at one checkpoint. The analytic B4/B5 profiles use this bounded amplitude projection, while B3/B6 use a fixed deterministic scalar search for `C`.

For `gamma>0`, the residual operator `P_gamma` is positive definite, so `ker(F_gamma) = {v: J_p v=0}` up to numerical tolerance. In contrast, the exact zero-damping projector has `ker(F_0) = {v: J_p v in range(J_w)}`. Thus a finite-gamma zero eigenvalue is a physical residual-sensitivity null, whereas a zero-damping null can be a state-compensation direction. Neither kernel alone proves structural identifiability: both depend on the sampled residual/observation design and parameter coordinates. Under a coordinate change `p = g(z)` with Jacobian `G`, the same quadratic form transforms by congruence `F_z = G^T F_p G`; eigenvalues and diagonals therefore change, while the represented tangent subspace is the invariant object.
