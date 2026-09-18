"""List the defensive passages in a manuscript, with line numbers, for a targeted edit.

The revision brief asks for positive framing.  Finding every "this is not" by eye is slow
and uneven, so this prints the sentences that carry disclaimers, concessives or heavy
negation, each with its source line, so the rewrite can be minimal and reviewable.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import manuscript_style as MS  # noqa: E402


def compact(sentence: str) -> str:
    """One-line form of the sentence, for tab-separated dumps."""
    return " ".join(sentence.split())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--min-hits", type=int, default=1)
    parser.add_argument("--dump", type=Path, default=None,
                        help="write line<TAB>score<TAB>sentence<TAB>source line, for editing")
    args = parser.parse_args()

    raw = args.source.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", raw, flags=re.DOTALL)
    body = match.group(1) if match else raw
    start_line = raw[: match.start(1)].count("\n") + 1 if match else 1

    hits = []
    for offset, line in enumerate(body.splitlines()):
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        prose = MS.to_prose(stripped)
        for sentence in MS.sentences_of(prose):
            score = (
                len(MS.DISCLAIMER.findall(sentence)) * 3
                + len(MS.NEGATION.findall(sentence))
                + len(MS.CONCESSIVE.findall(sentence))
            )
            if score >= args.min_hits and (
                MS.DISCLAIMER.search(sentence) or MS.NEGATION.search(sentence)
            ):
                hits.append((start_line + offset, score, sentence, stripped))

    hits.sort(key=lambda h: -h[1])
    print(f"{len(hits)} defensive sentences in {args.source.name}")
    if args.dump:
        args.dump.parent.mkdir(parents=True, exist_ok=True)
        args.dump.write_text(
            "\n".join(
                f"{line}\t{score}\t{compact(sentence)}\t{raw_line}"
                for line, score, sentence, raw_line in hits
            ),
            encoding="utf-8",
        )
        print(f"dumped to {args.dump}")
        return
    for line, score, sentence, _ in hits:
        print(f"  L{line:<5} score={score:<3} {sentence[:150]}")


if __name__ == "__main__":
    main()
