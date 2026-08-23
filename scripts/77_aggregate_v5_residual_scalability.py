from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.residual_scalability_aggregation import (
    write_residual_scalability_figure,
    write_residual_scalability_report,
)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    aggregate = write_residual_scalability_report(root)
    figure = write_residual_scalability_figure(root, aggregate)
    print(json.dumps({"engineering_status": aggregate["engineering_status"], "pass_count": aggregate["pass_count"], "figure": figure.relative_to(root).as_posix()}, indent=2))
