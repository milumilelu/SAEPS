import argparse
import json
from pathlib import Path

from saeps.v48.pipeline import run_scalability_checkpoint


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(run_scalability_checkpoint(Path(__file__).resolve().parents[1], args.checkpoint), indent=2))
