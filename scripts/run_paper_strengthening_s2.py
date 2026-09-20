"""Run the bounded S2 development profile diagnostic."""

from pathlib import Path
import json

from saeps.paper_strengthening_s2 import run_s2


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(run_s2(root), ensure_ascii=False, indent=2, sort_keys=True))
