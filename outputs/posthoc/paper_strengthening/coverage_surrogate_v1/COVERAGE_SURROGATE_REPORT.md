# Local-Gaussian coverage surrogate audit

This is a feasibility screen derived from saved exact reduced curvatures. It is not an empirical Monte Carlo coverage experiment.

| benchmark | nominal | method | rows | median surrogate coverage | range |
|---|---:|---|---:|---:|---:|
| Allen-Cahn | 0.90 | SAEPS | 9 | 0.8542 | 0.8256–0.8799 |
| Allen-Cahn | 0.90 | block | 9 | 0.9077 | 0.8978–0.9107 |
| Allen-Cahn | 0.90 | raw | 9 | 0.2780 | 0.2521–0.3082 |
| Allen-Cahn | 0.95 | SAEPS | 9 | 0.9170 | 0.8944–0.9360 |
| Allen-Cahn | 0.95 | block | 9 | 0.9552 | 0.9485–0.9571 |
| Allen-Cahn | 0.95 | raw | 9 | 0.3284 | 0.2983–0.3634 |
| Allen-Cahn | 0.99 | SAEPS | 9 | 0.9773 | 0.9666–0.9851 |
| Allen-Cahn | 0.99 | block | 9 | 0.9916 | 0.9895–0.9922 |
| Allen-Cahn | 0.99 | raw | 9 | 0.4226 | 0.3853–0.4653 |
| Burgers | 0.90 | SAEPS | 12 | 0.8935 | 0.8656–0.9165 |
| Burgers | 0.90 | block | 12 | 0.9119 | 0.8811–0.9248 |
| Burgers | 0.90 | raw | 12 | 0.2411 | 0.2060–0.2804 |
| Burgers | 0.95 | SAEPS | 12 | 0.9456 | 0.9256–0.9608 |
| Burgers | 0.95 | block | 12 | 0.9579 | 0.9369–0.9660 |
| Burgers | 0.95 | raw | 12 | 0.2854 | 0.2443–0.3312 |
| Burgers | 0.99 | SAEPS | 12 | 0.9885 | 0.9809–0.9933 |
| Burgers | 0.99 | block | 12 | 0.9924 | 0.9854–0.9947 |
| Burgers | 0.99 | raw | 12 | 0.3692 | 0.3174–0.4261 |

The audit retains 4 excluded exact-block files in the planned denominator.
The signal supports proceeding to an end-to-end refitting pilot, but cannot establish finite-sample CI coverage or a statistical guarantee.
