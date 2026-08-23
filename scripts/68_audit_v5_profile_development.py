from __future__ import annotations

import json
from pathlib import Path

from saeps.v5.profile_development_audit import write_profile_development_audit


if __name__ == "__main__":
    result = write_profile_development_audit(Path(__file__).resolve().parents[1])
    print(json.dumps({key: result[key] for key in ["engineering_status", "selected_candidate", "heldout_authorized"]}, indent=2))
