"""Generate the V5.1 machine aggregate, report, and same-source figure."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.finite_gamma_aggregation import (
    write_finite_gamma_figure,
    write_finite_gamma_report,
)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    aggregate = write_finite_gamma_report(root)
    figure = write_finite_gamma_figure(root, aggregate)
    print(json.dumps({"engineering_status": aggregate["engineering_status"], "terminal_count": aggregate["terminal_count"], "pass_count": aggregate["pass_count"], "figure": figure.relative_to(root).as_posix()}, indent=2))
