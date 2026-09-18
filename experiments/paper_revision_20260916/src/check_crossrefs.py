"""List undefined cross-references introduced by an edit.

Adding a pointer to a section that does not exist is a real defect in a manuscript, and a
single pdflatex pass reports citations as undefined too, so the two must be separated.
This checks the reference targets in the edited file against the labels it defines, and
compares the undefined set against the pre-edit file so only new danglers are reported.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LABEL = re.compile(r"\\label\{([^}]*)\}")
REF = re.compile(r"\\(?:ref|eqref|autoref|Cref|cref)\{([^}]*)\}")


def profile(path: Path) -> tuple[set[str], set[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return set(LABEL.findall(text)), set(REF.findall(text))


if __name__ == "__main__":
    before_labels, before_refs = profile(Path(sys.argv[1]))
    after_labels, after_refs = profile(Path(sys.argv[2]))

    dangling_before = before_refs - before_labels
    dangling_after = after_refs - after_labels
    new_danglers = dangling_after - dangling_before

    print(f"labels  before={len(before_labels)} after={len(after_labels)}")
    print(f"refs    before={len(before_refs)} after={len(after_refs)}")
    print(f"dangling before={len(dangling_before)} after={len(dangling_after)}")
    print()
    if new_danglers:
        print(f"NEW DANGLING REFERENCES ({len(new_danglers)}):")
        for name in sorted(new_danglers):
            print(f"  {name}")
    else:
        print("no new dangling references")
    fixed = dangling_before - dangling_after
    if fixed:
        print(f"also removed {len(fixed)} pre-existing dangling target(s): {sorted(fixed)}")
