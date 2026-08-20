# Future Confirmation Candidate — Not Locked

This document is a candidate only. `confirmation_authorized` remains false.

For every planned confirmation seed, attempt the frozen baseline-then-rescue center and two-pass scaled-LSQR refinement. Retain every invalid center or solver failure in the planned denominator.

For each valid exact local reference compute:

\[
E_{SAEPS}=\frac{|F_{se}^{GN}-H_{red}^{exact}|}{|H_{red}^{exact}|+10^{-8}},\quad
E_{raw}=\frac{|F_{raw}-H_{red}^{exact}|}{|H_{red}^{exact}|+10^{-8}},
\]

\[
D_i=E_{raw,i}-E_{SAEPS,i}.
\]

The primary direction is `D_i>0`. Absolute 5% SAEPS errors remain secondary and all v3.4 failures remain unchanged. The first-order reduced-correction indicator is reported as a development-selected diagnostic and must not be recalibrated on confirmation data.

Seeds, required valid denominator, paired test/bootstrap rule and Go/No-Go thresholds are intentionally not locked by this candidate document and require explicit user authorization before confirmation.

