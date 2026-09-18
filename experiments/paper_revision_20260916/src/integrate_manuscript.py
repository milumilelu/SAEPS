"""Splice the new experiment sections into the manuscript.

Takes the narrative-pass manuscript and inserts the E3 non-affine benchmark, the E6
architecture extension, the E7 profile-resolution check and the E8 matched-damping cost
comparison, together with the statistical-unit paragraph and the generated tables.

Every anchor must occur exactly once.  If the manuscript moves underneath this script the
run fails and prints the missing anchor, rather than silently inserting a section in the
wrong place.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import paper_fragments as F

# where the generated macros and tables are pulled in
PREAMBLE_ANCHOR = r"\begin{document}"
NUMBERS_INPUT = r"\input{paper_numbers}"
TABLES_INPUT = r"\input{paper_tables}"


def splice(text: str, anchor: str, insertion: str, where: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise SystemExit(f"anchor occurs {count} times, expected exactly one: {anchor[:70]}")
    if where == "before":
        return text.replace(anchor, insertion + "\n" + anchor, 1)
    return text.replace(anchor, anchor + "\n" + insertion, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()

    if args.out.exists() or args.log.exists():
        raise FileExistsError("refusing to overwrite an existing output")

    text = args.source.read_text(encoding="utf-8")
    before_lines = len(text.splitlines())

    # macros must be defined before the body; tables are pulled in after the last results block
    text = splice(text, PREAMBLE_ANCHOR, NUMBERS_INPUT, "before")
    for index, (anchor, insertion, where) in enumerate(F.SPLICES):
        if index == len(F.SPLICES) - 1:
            insertion = insertion + "\n" + TABLES_INPUT
        text = splice(text, anchor, insertion, where)

    args.out.write_text(text, encoding="utf-8")

    inserted = {
        "sections": [
            "sec:nonaffine_setup",
            "sec:nonaffine_results",
            "sec:architecture",
            "sec:profile_resolution",
            "sec:matched_cost",
        ],
        "tables": ["tab:e3_heldout", "tab:e3_seeds", "tab:e6_architecture",
                   "tab:e7_scope", "tab:e8_cost"],
        "macros": sorted(set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", NUMBERS_INPUT))),
    }
    new_labels = re.findall(r"\\label\{(sec:[a-z_]+|tab:[a-z0-9_]+)\}", text)
    used = sorted({m for m in re.findall(r"\\([A-Za-z]+)", text)})
    args.log.write_text(
        json.dumps(
            {
                "source": str(args.source),
                "output": str(args.out),
                "lines_before": before_lines,
                "lines_after": len(text.splitlines()),
                "inserted": inserted,
                "labels_defined": sorted(set(new_labels)),
                "note": "numbers come from paper_numbers.tex; none is typed into the prose",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"lines {before_lines} -> {len(text.splitlines())}")
    print(args.out)


if __name__ == "__main__":
    main()
