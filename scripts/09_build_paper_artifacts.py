"""Build all paper-facing and supplementary artifacts from accepted raw runs."""

from __future__ import annotations

import json
from pathlib import Path

from saeps.artifacts import build_paper_artifacts


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = build_paper_artifacts(root)
    print(json.dumps(result, indent=2, sort_keys=True))
