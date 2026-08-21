import json
from pathlib import Path

from saeps.v45.confirmation import run_v45_confirmation


if __name__ == "__main__":
    print(json.dumps(run_v45_confirmation(Path(__file__).resolve().parents[1]), indent=2))
