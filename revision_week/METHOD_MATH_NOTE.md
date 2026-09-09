# Fixed-target directional curvature

ell=1/2||rbar||², G=JᵀJ, H=∇²ell, S=H−G. H/G exclude the anchor penalty.
Fix gamma and anchor. M=Gtt+gamma I, A=Htt+gamma I, BG=Gtl, B=Htl, CG=Gll, C=Hll.
For any n×p response Z, including an inexact solve:

* QG=CG−BGᵀZ−ZᵀBG+ZᵀMZ.
* V=[−Z;I], FSO=QG+VᵀSV=C−BᵀZ−ZᵀB+ZᵀAZ.
* FG=CG−BGᵀ solve(M,BG), RG=BG−MZ, QG−FG=RGᵀ solve(M,RG).
* F*=C−Bᵀ solve(A,B), D=B−AZ, FSO−F*=Dᵀ solve(A,D).

Expand D=B−AZ to prove the last identity using symmetric A. Code computes F*
independently. Invertible indefinite A permits the identity but not a PSD bound.
A SPD implies FSO−F* PSD, without asserting SO closer than GN, SO≤RAW, or positive
reduced curvature. Local minimized-profile interpretation also requires state
stationarity and local minimum of the SAME anchored objective. Numerical old
gates do not establish exact stationarity or finite-difference profile accuracy.

For inexact AW≈D, Z+=Z+W and FSO(Z+)=FSO(Z)−DᵀW−WᵀD+WᵀAW.
Dropping terms is invalid for arbitrary W. Multi-column independent PCG has no
claimed Loewner monotonicity at every iteration.

If A≥mu I>0, 0≤FSO−F*≤DᵀD/mu and U=||D||₂²/mu bounds spectral error.
Only if f=||FSO||₂>U does U/(f−U) bound relative error. Otherwise report no finite
relative guarantee; U/(f+epsilon) is not that bound.
Ordinary eigh plus asymmetry, residual, orthogonality and numerical roundoff
margin gives numerical_bound_estimate, never verified_bound. This margin is not
a rigorous rounded enclosure. Unresolved eigenvalues are not clipped positive.

For B2=LLᵀ, T=L⁻ᵀ, transform every F to TᵀFT and D to DT, using
||DT||₂²/mu in the same coordinates. Repeated eigenspaces have no unique direction.

Directional adapter: QG=(JV)ᵀJV+gamma ZᵀZ, FSO=VᵀHV+gamma ZᵀZ,
D=(HV)theta−gamma Z. Each direction costs one JVP and one HVP for this evaluation;
GN solves, spectrum and refinement are extra. E0's true HVP count is zero.
Dense spectral assistance must be charged and is not full matrix-free certification.

For fixed-weight scalar rbar=a(theta)+exp(lambda)b(theta), Hll−Gll=g_lambda.
With mu=exp(lambda), Hll=mu² Hmm+mu g_mu. Tests check the gradient term away from
stationarity on the actual tiny scalar network. Original E0 tensors are missing,
so original-center T3 is unavailable. These identities are not novelty claims.
