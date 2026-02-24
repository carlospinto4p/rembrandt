"""Build pre-structured Spanish lessons from vocabulary data.

Reads ``data/spanish_top10000.json`` and outputs
``data/spanish_lessons.json`` with two types of lessons:

1. **CEFR chunk lessons** — ~25 words each, ordered by frequency
   within each CEFR level.
2. **Topic lessons** — words grouped by topic tag within each
   CEFR level (minimum 5 words per lesson).

Usage::

    uv run python scripts/build_spanish_lessons.py
"""

import json
from collections import defaultdict
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_VOCAB_PATH = _DATA_DIR / "spanish_top10000.json"
_OUTPUT_PATH = _DATA_DIR / "spanish_lessons.json"

_CHUNK_SIZE = 25
_MIN_TOPIC_WORDS = 5

_CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]


def _build_cefr_chunks(
    words_by_cefr: dict[str, list[dict]],
) -> list[dict]:
    """Build frequency-ordered chunk lessons per CEFR level."""
    lessons: list[dict] = []
    for cefr in _CEFR_ORDER:
        words = words_by_cefr.get(cefr, [])
        if not words:
            continue
        for i in range(0, len(words), _CHUNK_SIZE):
            chunk = words[i : i + _CHUNK_SIZE]
            num = i // _CHUNK_SIZE + 1
            ranks = [w["rank"] for w in chunk]
            lessons.append({
                "title": f"{cefr} - Lesson {num}",
                "description": (
                    f"Most common {cefr} words "
                    f"(ranks {ranks[0]}-{ranks[-1]})"
                ),
                "language_from": "en",
                "language_to": "es",
                "cefr": cefr,
                "tags": [],
                "word_ranks": ranks,
                "word_count": len(ranks),
            })
    return lessons


def _build_topic_lessons(
    words_by_cefr: dict[str, list[dict]],
) -> list[dict]:
    """Build topic-grouped lessons per CEFR level."""
    lessons: list[dict] = []
    for cefr in _CEFR_ORDER:
        words = words_by_cefr.get(cefr, [])
        if not words:
            continue
        topic_words: dict[str, list[dict]] = defaultdict(list)
        for w in words:
            for tag in w.get("tags", []):
                topic_words[tag].append(w)
        for tag in sorted(topic_words):
            tagged = topic_words[tag]
            if len(tagged) < _MIN_TOPIC_WORDS:
                continue
            ranks = [w["rank"] for w in tagged]
            lessons.append({
                "title": f"{cefr} {tag.title()}",
                "description": (
                    f"{cefr} words related to {tag} "
                    f"({len(ranks)} words)"
                ),
                "language_from": "en",
                "language_to": "es",
                "cefr": cefr,
                "tags": [tag],
                "word_ranks": ranks,
                "word_count": len(ranks),
            })
    return lessons


def main() -> None:
    with open(_VOCAB_PATH, encoding="utf-8") as f:
        vocab = json.load(f)

    words_by_cefr: dict[str, list[dict]] = defaultdict(list)
    for entry in vocab:
        cefr = entry.get("cefr")
        if cefr:
            words_by_cefr[cefr].append(entry)

    lessons = _build_cefr_chunks(words_by_cefr)
    lessons.extend(_build_topic_lessons(words_by_cefr))

    with open(_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(lessons, f, indent=2, ensure_ascii=False)

    # Summary
    cefr_count = sum(
        1 for ls in lessons if not ls["tags"]
    )
    topic_count = len(lessons) - cefr_count
    print(f"Generated {len(lessons)} lessons:")
    print(f"  CEFR chunks: {cefr_count}")
    print(f"  Topic lessons: {topic_count}")

    for cefr in _CEFR_ORDER:
        cefr_lessons = [
            ls for ls in lessons
            if ls["cefr"] == cefr and not ls["tags"]
        ]
        topic_lessons = [
            ls for ls in lessons
            if ls["cefr"] == cefr and ls["tags"]
        ]
        print(
            f"  {cefr}: {len(cefr_lessons)} chunk"
            f" + {len(topic_lessons)} topic"
        )

    print(f"\nWritten to {_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
