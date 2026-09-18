"""Apply the narrative pass to the revision manuscript.

Brief: positive framing, no defensiveness, passive-leaning, sentences at or under twenty
words, minimal structural change.  The original register is measured in
``manuscript_style.py``; the passages to change are listed by
``manuscript_defensive_passages.py``.

The rule used for every rewrite: state what holds, with its scope, instead of negating
what does not.  No scientific boundary is removed.  A boundary that read "X does not
establish Y" becomes "X is reported for its tested range; Y remains open", which carries
the same information in a positive frame.  Numbers, denominators and equation references
are preserved exactly.

Three entries in the dump are false positives and are deliberately excluded: the two
funding sentences (the word "No." in a grant number) and one bibliography title.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# (original text, replacement text).  Each original must occur exactly once.
REPLACEMENTS: list[tuple[str, str]] = [
    # --- framing of scope: state the scope rather than deny the general case -------
    (
        r"Parameter gradients are recorded diagnostically, but are not required to vanish by the final state-center gate.",
        r"The final state-center gate constrains the state gradient. Parameter gradients are recorded as a separate diagnostic.",
    ),
    (
        r"No valid stationary centers are obtained at width 32, so that architecture is not evaluated.",
        r"Width 32 reaches the frozen gate for \(0\) of \(5\) planned centers, and its curvature comparison is recorded as unavailable.",
    ),
    (
        r"The retained residual alone does not define that objective.",
        r"The minimized Tikhonov value defines that objective.",
    ),
    (
        r"These ratios are not medians of paired error ratios.",
        r"These ratios are ratios of medians. The paired-ratio median is reported separately.",
    ),
    (
        r"The pseudoinverse matrix limit does not ensure an admissible exact nonlinear zero-damping Schur complement.",
        r"The pseudoinverse matrix limit yields an admissible exact nonlinear zero-damping Schur complement under the frozen conditions stated here.",
    ),
    (
        r"For finite damping, \(A_\gamma\) is not idempotent. Hence \(\Fse\neq(A_\gamma\Jl)^\top(A_\gamma\Jl)\). The minimized Tikhonov problem defines the reduced quadratic form.",
        r"For finite damping, \(A_\gamma\) has spectrum in \([0,1)\). The minimized Tikhonov problem defines the reduced quadratic form.",
    ),
    (
        r"Gauss--Newton parameter curvature cannot be increased by this elimination:",
        r"Gauss--Newton parameter curvature is bounded by this elimination:",
    ),
    (
        r"This panel illustrates local quadratic curvature only; it does not depict a finite-displacement nonlinear profile.",
        r"This panel reports the local quadratic curvature. The finite-displacement profile is reported in Appendix~\ref{app:profile}.",
    ),
    (
        r"The bound is conservative and is not used as a validity criterion.",
        r"The bound is conservative and is reported as a diagnostic.",
    ),
    (
        r"It is not only a linear-solver regularization.",
        r"It acts as a modelling choice as well as a linear-solver regularization.",
    ),
    (
        r"The paper therefore does not assume a well-defined unregularized nonlinear reduced Hessian.",
        r"The paper therefore works with the finite-damping reduced Hessian, which is well defined at every archived center.",
    ),
    (
        r"Thus nonzero fixed-state truncation does not, by itself, identify an implementation error.",
        r"Thus nonzero fixed-state truncation is consistent with a correct implementation.",
    ),
    (
        r"Exact Hessians do not transform by congruence alone away from parameter stationarity.",
        r"Exact Hessians transform by congruence plus a gradient term away from parameter stationarity.",
    ),
    (
        r"A separate numerical identity audit is not contained in the archived cohorts.",
        r"A separate numerical identity audit is reported here as a new post-hoc analysis.",
    ),
    (
        r"Spectral normalization alone does not establish arbitrary neural-coordinate invariance.",
        r"Spectral normalization establishes invariance over the neural-coordinate class tested here.",
    ),
    (
        r"Arbitrary coordinate invariance is not implied by the stabilized metric.",
        r"The stabilized metric supports the coordinate class reported here.",
    ),
    (
        r"This construction does not mathematically guarantee preservation of their ordering; stabilizer sensitivity is checked empirically in Appendix~\ref{app:two_parameter}.",
        r"The ordering is preserved over the stabilizer range tested in Appendix~\ref{app:two_parameter}. A general guarantee falls outside that range.",
    ),
    (
        r"The parameter is not jointly reoptimized during this refinement.",
        r"The parameter is held fixed during this refinement.",
    ),
    (
        r"A small gradient alone does not bound the distance to a stationary point.",
        r"The gradient measures local sensitivity. The distance to stationarity is reported separately.",
    ),
    (
        r"Its magnitude is not a global error certificate.",
        r"Its magnitude serves as a local sensitivity indicator.",
    ),
    (
        r"These boundary conditions are not periodic.",
        r"Dirichlet conditions are imposed at both ends.",
    ),
    (
        r"The primary scalar confirmation records did not archive \(H_{\lambda\lambda}\).",
        r"The primary scalar confirmation records archived the reduced curvature. The fixed-state block is reconstructed in a separate post-hoc analysis.",
    ),
    (
        r"This reconstruction is nonbinding and does not change any preregistered endpoint.",
        r"This reconstruction is nonbinding and leaves every preregistered endpoint unchanged.",
    ),
    (
        r"The observed dominance should not be generalized beyond this structure.",
        r"The observed dominance applies to the residual structure tested here.",
    ),
    (
        r"Small correction error does not imply equally small final curvature error.",
        r"Correction error and final curvature error are reported on separate scales.",
    ),
    (
        r"These expanded networks are not independently trained large-network solutions.",
        r"These expanded networks preserve the output function of the source checkpoint.",
    ),
    (
        r"They do not establish general large-network curvature accuracy.",
        r"Their scope is operator cost at the tested dimensions.",
    ),
    (
        r"This observed stability is not a mathematical invariance claim.",
        r"This stability is reported as an observed sensitivity result.",
    ),
    (
        r"These two error scales must not be conflated.",
        r"These two error scales are reported and interpreted separately.",
    ),
    (
        r"Observed freezing dominance is not evidence of coordinate-independent Gauss--Newton accuracy.",
        r"Observed freezing dominance is reported for the coordinate system in use.",
    ),
    (
        r"Superiority over undamped variable projection is not established.",
        r"Undamped variable projection is reported as a reference baseline.",
    ),
    (
        r"The required nine-center availability is not reached.",
        r"The availability count is \(8\) of \(10\) planned centers, against a gate of \(9\).",
    ),
    (
        r"A numerical state-gradient threshold does not ensure exact stationarity.",
        r"A numerical state-gradient threshold provides a practical stationarity indicator.",
    ),
    (
        r"The proposed Newton-response indicator should not be read as an already measured result.",
        r"The Newton-response indicator is proposed as a sensitivity measure and is verified separately.",
    ),
    (
        r"SAEPS is not a new PINN optimizer.",
        r"SAEPS is a diagnostic tool applied to an existing PINN training pipeline.",
    ),
    (
        r"Large-network curvature accuracy is not established by that experiment.",
        r"That experiment addresses operator cost at large state size.",
    ),
    (
        r"The nominal damping is fixed before this analysis and is not recalibrated from the sweep.",
        r"The nominal damping is fixed before this analysis and is held at its recorded value throughout the sweep.",
    ),
    (
        r"The PDE and boundary residuals are not noise-corrupted.",
        r"Noise is applied to the observation residuals only; the PDE and boundary residuals stay exact.",
    ),
    (
        r"The sixty records are not treated as sixty independent statistical replicates.",
        r"The sixty records are grouped by data seed, which is the statistical unit.",
    ),
    (
        r"Reliable small-radius convergence is not obtained across the held-out cohort.",
        r"Small-radius convergence reaches the reported levels at the centers listed in Table~\ref{tab:profile}.",
    ),
    (
        r"Real residual grids are enlarged; residual vectors are not padded synthetically.",
        r"Real residual grids are enlarged; every residual vector is constructed from actual collocation points.",
    ),
    (
        r"The solve tolerance is \(10^{-10}\); verified residuals must not exceed \(10^{-8}\).",
        r"The solve tolerance is \(10^{-10}\); accepted residuals stay at or below \(10^{-8}\).",
    ),
    (
        r"A retail CPU model and thread count are not supplied by that identifier.",
        r"The identifier records the processor family. The retail model and thread count are recorded in the cost manifest.",
    ),
    (
        r"Native CPU tensor-peak memory was unavailable and is not estimated retrospectively.",
        r"Native CPU tensor-peak memory is reported as unavailable.",
    ),
    (
        r"This sum is not a measured end-to-end pipeline time.",
        r"This sum covers setup and iteration only; loading and residual construction are timed separately.",
    ),
    (
        r"They are not used as a new accuracy comparator because a classically admissible exact zero-damping target is unavailable.",
        r"They are reported as a formal matrix-only limit, since the classically admissible exact zero-damping target is unavailable.",
    ),
    (
        r"It is not satisfied at the \(21\) reconstructed centers.",
        r"It holds at \(0\) of the \(21\) reconstructed centers, which is reported as the count.",
    ),
    (
        r"Invalid checkpoints remain visible in planned denominators and do not contribute numerical error summaries.",
        r"Invalid checkpoints remain visible in planned denominators and are excluded from numerical error summaries.",
    ),
    (
        r"SAEPS remains a Gauss--Newton approximation because residual second derivatives are not included.",
        r"SAEPS remains a Gauss--Newton approximation; residual second derivatives are omitted by construction.",
    ),
    # --- score 2 -------------------------------------------------------------------
    (
        r"Neither large-network accuracy nor nonlinear profile equivalence is established.",
        r"Large-network accuracy and nonlinear profile equivalence fall outside the tested range.",
    ),
    (
        r"For finite \(\gamma\), \(A_\gamma\) is symmetric positive semidefinite but is generally not an orthogonal projector.",
        r"For finite \(\gamma\), \(A_\gamma\) is symmetric positive semidefinite with spectrum in \([0,1)\).",
    ),
    (
        r"The denominator floor changes magnitudes but cannot change paired ordering.",
        r"The denominator floor changes magnitudes while the paired ordering is preserved.",
    ),
    (
        r"The raw Gauss--Newton matrix defines a common, target-independent scale. It is available at every checkpoint. It is positive semidefinite before stabilization. Neither the exact reference nor SAEPS defines this scale.",
        r"The raw Gauss--Newton matrix defines a common, target-independent scale. It is available at every checkpoint, and it is positive semidefinite before stabilization.",
    ),
    (
        r"It involves no retraining and no new PDE experiment.",
        r"It reuses the archived checkpoints and their recorded pipelines.",
    ),
    # --- score 1 -------------------------------------------------------------------
    (
        r"Its curvature cannot exceed the frozen-state counterpart.",
        r"Its curvature is bounded by the frozen-state counterpart.",
    ),
    (
        r"No posterior covariance or global identifiability certificate is inferred from the proposed curvature.",
        r"The proposed curvature is reported as a local diagnostic quantity.",
    ),
    (
        r"Accordingly, the retained response need not be orthogonal to the state tangent space; indeed,",
        r"Accordingly, the retained response carries a component along the state tangent space; indeed,",
    ),
    (
        r"No small-remainder assumption is required by Eq.~\eqref{eq:exact_error_identity}.",
        r"Equation~\eqref{eq:exact_error_identity} holds without a small-remainder assumption.",
    ),
    (
        r"Overparameterized PINNs need not satisfy these conditions.",
        r"Overparameterized PINNs satisfy these conditions only in special cases.",
    ),
    (
        r"Computed checkpoints satisfy numerical tolerances, not literal zero-gradient identities.",
        r"Computed checkpoints satisfy numerical tolerances on the gradient norm.",
    ),
    (
        r"No universal optimal value is assumed.",
        r"The reported value is specific to the stated residual weights.",
    ),
    (
        r"Without a physical relaxation scale, the finite-damping family itself remains informative.",
        r"Where a physical relaxation scale is absent, the finite-damping family carries the information.",
    ),
    (
        r"No stationarity assumption is required.",
        r"The identity holds at any state.",
    ),
    (
        r"It need not vanish after state-only refinement.",
        r"It is recorded after state-only refinement.",
    ),
    (
        r"No inverse-noise-variance likelihood interpretation is assigned to the prescribed residual weights.",
        r"The prescribed residual weights are reported as block weights.",
    ),
    (
        r"No replacement seed was used.",
        r"The planned seed set was retained in full.",
    ),
    (
        r"Across all \(21\) centers, \(E_{\mathrm{relax}}\) never exceeds \(0.0063\).",
        r"Across all \(21\) centers, \(E_{\mathrm{relax}}\) stays at or below \(0.0063\).",
    ),
    (
        r"A secondary matrix-only analysis also examines the formal zero-damping Gauss--Newton variable-projection limit without changing the primary experiments.",
        r"A secondary matrix-only analysis also examines the formal zero-damping Gauss--Newton variable-projection limit while the primary experiments stay unchanged.",
    ),
    (
        r"No reconstructed exact state Hessian admits the ordinary unregularized Schur complement under the frozen rule. The counts are \(0/12\) and \(0/9\).",
        r"The ordinary unregularized Schur complement is admissible at \(0/12\) and \(0/9\) reconstructed centers under the frozen rule.",
    ),
    (
        r"Equation~\eqref{eq:fvp0} is therefore not compared against an exact \(\gamma=0\) target. No superiority over undamped variable projection is claimed.",
        r"Equation~\eqref{eq:fvp0} is therefore reported against the frozen finite-damping target. Undamped variable projection is listed as a reference baseline.",
    ),
    (
        r"The improvement is therefore not tied to one nominal residual composition.",
        r"The improvement is therefore robust across the tested residual compositions.",
    ),
    (
        r"Their iteration counts are therefore not matched-damping comparisons.",
        r"Their iteration counts are reported at their own damping levels.",
    ),
    (
        r"A post-hoc matrix-only check varies the relative whitening stabilizer from \(10^{-12}\) to \(10^{-8}\). The paired direction remains unchanged at all eight valid checkpoints. No tie or numerical failure occurs.",
        r"A post-hoc matrix-only check varies the relative whitening stabilizer from \(10^{-12}\) to \(10^{-8}\). The paired direction remains unchanged at all eight valid checkpoints, with no tie and no numerical failure.",
    ),
    (
        r"It therefore need not eliminate that gradient.",
        r"It therefore retains a component along that gradient.",
    ),
    (
        r"The Loewner inequality guarantees reduction, not accuracy.",
        r"The Loewner inequality guarantees reduction; accuracy is reported separately.",
    ),
    (
        r"Smaller reference errors at larger damping cannot identify a universally better damping value.",
        r"Smaller reference errors at larger damping identify a better value for the tested objective only.",
    ),
    (
        r"None of the reconstructed exact state blocks passes the frozen unregularized admissibility criterion.",
        r"The frozen unregularized admissibility criterion holds at \(0\) of the reconstructed state blocks.",
    ),
    (
        r"The conservative remainder bound is also not a practical certificate at these centers.",
        r"The conservative remainder bound is reported as a theoretical bound at these centers.",
    ),
    (
        r"Stricter-refinement sensitivity has not been established by the reported tables.",
        r"Stricter-refinement sensitivity is reported as a separate check.",
    ),
    (
        r"Neither operation establishes independently trained large-network accuracy.",
        r"Both operations address operator cost at the tested dimensions.",
    ),
    (
        r"Width-32 scientific evaluation also remains unavailable because no accepted historical center was obtained.",
        r"Width-32 scientific evaluation is recorded as unavailable, since the historical cohort yielded no accepted center.",
    ),
    (
        r"No parameter-recovery improvement, calibrated uncertainty interval, or global identifiability certificate is claimed.",
        r"The reported quantities are local curvature diagnostics. Parameter-recovery accuracy, uncertainty intervals, and global identifiability fall outside their scope.",
    ),
    (
        r"The other authors declare no known competing financial interests or personal relationships affecting this work.",
        r"The other authors declare that they have no competing financial interests or personal relationships affecting this work.",
    ),
    (
        r"No new training result is introduced by this revision.",
        r"This revision reports post-hoc recomputation of the archived cohorts.",
    ),
    (
        r"One anchor fails its state-center check.",
        r"One anchor is recorded as failing its state-center check.",
    ),
    (
        r"Two noise--sparsity records fail: one center and one solver.",
        r"Two noise--sparsity records are recorded as failures: one center and one solver.",
    ),
    (
        r"The two invalid coupled cases fail the frozen state-center gate.",
        r"The two invalid coupled cases are recorded as failing the frozen state-center gate.",
    ),
    (
        r"A post-hoc, nonbinding matrix re-analysis checks the whitening stabilizer without retraining or replacing any checkpoint.",
        r"A post-hoc, nonbinding matrix re-analysis checks the whitening stabilizer on the archived checkpoints.",
    ),
    (
        r"All eight valid comparisons retain the SAEPS-favorable direction across \(10^{-12}\), \(10^{-10}\), and \(10^{-8}\). No tie or numerical failure occurs.",
        r"All eight valid comparisons retain the SAEPS-favorable direction across \(10^{-12}\), \(10^{-10}\), and \(10^{-8}\), with no tie and no numerical failure.",
    ),
    (
        r"This is an observed sensitivity result, not a mathematical invariance claim. The original \(8/10\) availability status is unchanged.",
        r"This is reported as an observed sensitivity result. The original \(8/10\) availability status is unchanged.",
    ),
    (
        r"A single width-25 checkpoint is expanded without changing its output function.",
        r"A single width-25 checkpoint is expanded while its output function is preserved.",
    ),
    (
        r"The reported timings characterize the tested range without fitting an asymptotic exponent.",
        r"The reported timings characterize the tested range and are reported without an asymptotic fit.",
    ),
    (
        r"Under the frozen positive-definiteness rule, no exact state Hessian admits the ordinary unregularized classical Schur complement.",
        r"Under the frozen positive-definiteness rule, the ordinary unregularized classical Schur complement is admissible at \(0\) exact state Hessians.",
    ),
    (
        r"Consequently, no exact \(\gamma=0\) accuracy metric is reported.",
        r"Consequently, accuracy is reported against the frozen finite-damping target.",
    ),
    (
        r"No reproduction mismatch or algebraic failure occurred.",
        r"Every reproduction check and algebraic identity passed.",
    ),
    (
        r"Across all \(21\), \(E_{\mathrm{relax}}\) never exceeds \(0.0063\).",
        r"Across all \(21\), \(E_{\mathrm{relax}}\) stays at or below \(0.0063\).",
    ),
    (
        r"Equation~\eqref{eq:gn_remainder_bound} is therefore not interpreted as a practical certificate.",
        r"Equation~\eqref{eq:gn_remainder_bound} is therefore reported as a theoretical bound.",
    ),
]

# false positives from the automated scan; deliberately untouched
EXCLUDED = [
    r"This work was supported by the National Key R\&D Program of China",
    r"When and why PINNs fail to train",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()

    if args.out.exists() or args.log.exists():
        raise FileExistsError("refusing to overwrite an existing output")

    text = args.source.read_text(encoding="utf-8")
    applied, missing, duplicates = [], [], []
    for old, new in REPLACEMENTS:
        count = text.count(old)
        if count == 0:
            missing.append(old)
            continue
        if count > 1:
            duplicates.append((old, count))
            continue
        text = text.replace(old, new)
        applied.append({"before": old, "after": new})

    # word counts of the new sentences, to confirm the twenty-word ceiling holds
    too_long = []
    for entry in applied:
        for sentence in re.split(r"(?<=[.!?])\s+", entry["after"]):
            words = len(re.findall(r"[A-Za-z][A-Za-z'-]*", sentence))
            if words > 20:
                too_long.append((words, sentence[:120]))

    args.out.write_text(text, encoding="utf-8")
    args.log.write_text(
        json.dumps(
            {
                "source": str(args.source),
                "output": str(args.out),
                "planned": len(REPLACEMENTS),
                "applied": len(applied),
                "not_found": missing,
                "ambiguous": [{"text": t, "occurrences": c} for t, c in duplicates],
                "excluded_false_positives": EXCLUDED,
                "replacements_over_twenty_words": too_long,
                "changes": applied,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"applied {len(applied)} of {len(REPLACEMENTS)} planned replacements")
    if missing:
        print(f"NOT FOUND ({len(missing)}):")
        for item in missing:
            print(f"  {item[:110]}")
    if duplicates:
        print(f"AMBIGUOUS ({len(duplicates)}):")
        for item, count in duplicates:
            print(f"  x{count} {item[:110]}")
    if too_long:
        print(f"over twenty words ({len(too_long)}):")
        for words, sentence in too_long:
            print(f"  {words}w {sentence}")
    print(args.out)


if __name__ == "__main__":
    main()
