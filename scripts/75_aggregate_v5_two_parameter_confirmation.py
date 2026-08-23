from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.two_parameter_aggregation import (
    write_two_parameter_confirmation_report,
    write_two_parameter_figure,
)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = write_two_parameter_confirmation_report(root)
    figure = write_two_parameter_figure(root, result)
    print(json.dumps({"engineering_status": result["engineering_status"], "scientific_status": result["scientific_status"], "binding_valid": result["binding_valid_count"], "planned_wins": result["planned_win_count"], "sign_p": result["one_sided_exact_sign_test_p"], "figure": figure.relative_to(root).as_posix()}, indent=2))
