"""Compare pdflatex logs for the manuscript before and after the narrative pass."""

from __future__ import annotations

import re
import sys
from pathlib import Path

UNDEFINED = re.compile(r"LaTeX Warning: (?:Reference|Citation) .*? undefined")
OVERFULL = re.compile(r"Overfull \\hbox")
UNDERFULL = re.compile(r"Underfull \\hbox")
PAGES = re.compile(r"Output written on \S+ \((\d+) pages")


def scan(path: Path, label: str) -> dict:
    if not path.is_file():
        print(f"{label}: no log at {path}")
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    pages = PAGES.search(text)
    result = {
        "label": label,
        "pages": int(pages.group(1)) if pages else None,
        "undefined_refs": len(UNDEFINED.findall(text)),
        "overfull": len(OVERFULL.findall(text)),
        "underfull": len(UNDERFULL.findall(text)),
    }
    print(
        f"{label:<8} pages={result['pages']}  undefined={result['undefined_refs']}  "
        f"overfull={result['overfull']}  underfull={result['underfull']}"
    )
    return result


if __name__ == "__main__":
    scan(Path(sys.argv[1]), "before")
    scan(Path(sys.argv[2]), "after")
