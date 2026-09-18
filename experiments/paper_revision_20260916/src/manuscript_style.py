"""Measure the writing style of a manuscript so a revision can match it.

The revision brief is to write in the original's register: positive framing, mostly
passive voice, short sentences.  "Short" and "mostly passive" need numbers, otherwise the
revision is judged by impression.  This script extracts prose from a LaTeX source, drops
equations, tables, figures and citations, and reports the measured profile.

Automated counts do not replace reading.  They are a target to hit and a regression check,
not a statement about quality.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\\])")
# "is/are/was/were/be/been/being/becomes/remains + past participle" as a first approximation
PASSIVE = re.compile(
    r"\b(?:is|are|was|were|be|been|being|remains?|becomes?|appears?)\s+"
    r"(?:\w+ly\s+)?(\w+(?:ed|en|wn|ne|t))\b",
    re.IGNORECASE,
)
FIRST_PERSON = re.compile(r"\b(?:we|our|us|I)\b", re.IGNORECASE)
HEDGE = re.compile(r"\b(?:may|might|could|would|should|perhaps|possibly|likely)\b", re.IGNORECASE)
MODAL_STRONG = re.compile(r"\b(?:must|will|shall)\b", re.IGNORECASE)
NEGATION = re.compile(
    r"\b(?:not|no|never|neither|nor|cannot|fails?|failed|without|none)\b", re.IGNORECASE
)
CONCESSIVE = re.compile(
    r"\b(?:however|although|though|but|yet|nevertheless|despite|whereas)\b", re.IGNORECASE
)
DISCLAIMER = re.compile(
    r"\b(?:do not|does not|did not|is not|are not|was not|were not|cannot be|should not|"
    r"must not|not intended|not evidence|not a claim|nothing here)\b",
    re.IGNORECASE,
)


def strip_environment(text: str, names: tuple[str, ...]) -> str:
    for name in names:
        text = re.sub(
            rf"\\begin\{{{name}\}}.*?\\end\{{{name}\}}", " ", text, flags=re.DOTALL
        )
    return text


def to_prose(text: str) -> str:
    """Reduce LaTeX to prose sentences."""
    text = re.sub(r"(?<!\\)%.*", " ", text)                 # comments
    text = strip_environment(text, ("equation", "equation*", "align", "align*", "table",
                                    "table*", "figure", "figure*", "tabular", "verbatim"))
    text = re.sub(r"\\\[.*?\\\]", " ", text, flags=re.DOTALL)   # display math
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.DOTALL)
    text = re.sub(r"\$[^$]*\$", " MATH ", text)                  # inline math
    text = re.sub(r"\\(?:cite|ref|eqref|label|cref|Cref)\{[^}]*\}", " ", text)
    text = re.sub(r"\\(?:begin|end)\{[^}]*\}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", text)
    text = re.sub(r"[{}~]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def sentences_of(text: str) -> list[str]:
    chunks = []
    for line in text.split("\n"):
        chunks.extend(SENTENCE_SPLIT.split(line.strip()))
    out = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        words = [w for w in re.split(r"\s+", chunk) if re.search(r"[A-Za-z]", w)]
        if len(words) >= 3:
            out.append(" ".join(words))
    return out


def analyse(text: str) -> dict:
    sentences = sentences_of(text)
    lengths = [len(re.findall(r"[A-Za-z][A-Za-z'-]*", s)) for s in sentences]
    if not lengths:
        return {"sentences": 0}
    passive_hits = sum(len(PASSIVE.findall(s)) for s in sentences)
    verb_like = sum(len(re.findall(r"\b\w+(?:ed|es|s)\b", s)) for s in sentences)
    return {
        "sentences": len(sentences),
        "words": sum(lengths),
        "mean_words_per_sentence": round(statistics.mean(lengths), 2),
        "median_words_per_sentence": statistics.median(lengths),
        "p90_words_per_sentence": sorted(lengths)[int(0.9 * (len(lengths) - 1))],
        "max_words_per_sentence": max(lengths),
        "share_at_most_20_words": round(sum(1 for v in lengths if v <= 20) / len(lengths), 3),
        "passive_constructions": passive_hits,
        "passive_per_sentence": round(passive_hits / len(sentences), 3),
        "first_person_per_sentence": round(
            sum(len(FIRST_PERSON.findall(s)) for s in sentences) / len(sentences), 3
        ),
        "Hedges_per_sentence": round(sum(len(HEDGE.findall(s)) for s in sentences) / len(sentences), 3),
        "Strong_modals_per_sentence": round(
            sum(len(MODAL_STRONG.findall(s)) for s in sentences) / len(sentences), 3
        ),
        "negation_per_sentence": round(
            sum(len(NEGATION.findall(s)) for s in sentences) / len(sentences), 3
        ),
        "share_with_negation": round(
            sum(1 for s in sentences if NEGATION.search(s)) / len(sentences), 3
        ),
        "concessive_per_sentence": round(
            sum(len(CONCESSIVE.findall(s)) for s in sentences) / len(sentences), 3
        ),
        "disclaimer_per_sentence": round(
            sum(len(DISCLAIMER.findall(s)) for s in sentences) / len(sentences), 3
        ),
        "longest_sentences": sorted(sentences, key=lambda s: -len(s.split()))[:3],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    result = {}
    for source in args.sources:
        raw = source.read_text(encoding="utf-8", errors="replace")
        body = raw
        match = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", raw, flags=re.DOTALL)
        if match:
            body = match.group(1)
        prose = to_prose(body)
        profile = analyse(prose)
        # per-section breakdown, so a long appendix cannot dominate the average
        sections = {}
        for section in re.split(r"\\section\{", body)[1:]:
            title = section.split("}", 1)[0]
            sections[title[:60]] = analyse(to_prose(section.split("}", 1)[1])) if "}" in section else {}
        profile["by_section"] = sections
        result[source.name] = profile

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    for name, profile in result.items():
        print(f"{name}: {profile['sentences']} sentences, "
              f"mean {profile['mean_words_per_sentence']} words, "
              f"{profile['share_at_most_20_words']:.1%} at or under 20 words, "
              f"passive {profile['passive_per_sentence']:.2f}/sentence, "
              f"first-person {profile['first_person_per_sentence']:.2f}/sentence")


if __name__ == "__main__":
    main()
