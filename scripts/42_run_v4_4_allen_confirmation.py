from __future__ import annotations

import json
from pathlib import Path

from saeps.v44.execution import run_v44_confirmation


ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    print(json.dumps(run_v44_confirmation(ROOT), indent=2))

