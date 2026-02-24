"""Build a monolingual Spanish definitions file.

Downloads the Spanish Wiktionary extract from kaikki.org,
matches entries against the existing ranked word list
(``data/spanish_top10000.json``), and writes a new file with
Spanish-Spanish definitions to
``data/spanish_monolingual_10000.json``.

Usage::

    uv run python scripts/build_spanish_definitions.py
"""

import gzip
import json
import tempfile
import urllib.request
from pathlib import Path

_KAIKKI_URL = (
    "https://kaikki.org/dictionary/downloads"
    "/es/es-extract.jsonl.gz"
)

_POS_MAP: dict[str, str] = {
    "verb": "v",
    "noun": "n",
    "adj": "adj",
    "adv": "adv",
}

_ROOT = Path(__file__).resolve().parent.parent
_INPUT = _ROOT / "data" / "spanish_top10000.json"
_OUTPUT = _ROOT / "data" / "spanish_monolingual_10000.json"


def _download(url: str, dest: Path) -> Path:
    """Download `url` to `dest`, overwriting if it exists."""
    print(f"  Downloading {url.rsplit('/', 1)[-1]} ...")
    urllib.request.urlretrieve(url, dest)
    return dest


def _load_frequency_list(
    path: Path,
) -> dict[tuple[str, str], dict]:
    """Load the ranked word list as a lookup keyed by
    ``(word, pos)``.

    Returns a dict mapping ``(word, pos)`` to the full entry
    dict (rank, word, pos, definition, frequency).
    """
    with open(path, encoding="utf-8") as fh:
        words = json.load(fh)

    lookup: dict[tuple[str, str], dict] = {}
    for entry in words:
        key = (entry["word"], entry["pos"])
        if key not in lookup:
            lookup[key] = entry
    return lookup


def _extract_gender(entry: dict) -> str | None:
    """Extract noun gender from a kaikki entry's tags.

    Looks for `"masculine"` or `"feminine"` in the top-level
    `tags` list.
    """
    for tag in entry.get("tags", []):
        if tag == "masculine":
            return "m"
        if tag == "feminine":
            return "f"
    return None


def _conjugation_group(word: str, pos: str) -> str | None:
    """Derive conjugation group from a verb's infinitive.

    :return: `"ar"`, `"er"`, or `"ir"` for verbs, `None`
        otherwise.
    """
    if pos != "v":
        return None
    for suffix in ("ar", "er", "ir"):
        if word.endswith(suffix):
            return suffix
    return None


def _parse_kaikki(
    gz_path: Path,
    words: dict[tuple[str, str], dict],
) -> dict[tuple[str, str], list[str]]:
    """Stream the gzipped kaikki JSONL and extract senses.

    Only processes entries where ``lang_code == "es"`` and
    the ``(word, mapped_pos)`` pair exists in `words`.

    :param gz_path: Path to the downloaded ``.jsonl.gz`` file.
    :param words: Lookup dict from `_load_frequency_list`.
    :return: Dict mapping ``(word, pos)`` to a list of Spanish
        definition strings.
    """
    senses_map: dict[tuple[str, str], list[str]] = {}

    with gzip.open(gz_path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue

            entry = json.loads(line)

            if entry.get("lang_code") != "es":
                continue

            raw_pos = entry.get("pos", "")
            mapped_pos = _POS_MAP.get(raw_pos)
            if mapped_pos is None:
                continue

            word = entry.get("word", "")
            key = (word, mapped_pos)
            if key not in words:
                continue

            # Already processed this (word, pos) pair.
            if key in senses_map:
                continue

            glosses: list[str] = []
            for sense in entry.get("senses", []):
                for gloss in sense.get("glosses", []):
                    gloss = gloss.strip()
                    if gloss:
                        glosses.append(gloss)

            if glosses:
                senses_map[key] = glosses

    return senses_map


def main() -> None:
    if not _INPUT.exists():
        print(
            f"  ERROR: {_INPUT} not found.\n"
            "  Run build_spanish_vocab.py first."
        )
        return

    words = _load_frequency_list(_INPUT)
    print(f"  Loaded {len(words)} words from frequency list.")

    with tempfile.TemporaryDirectory() as tmpdir:
        gz_path = _download(
            _KAIKKI_URL, Path(tmpdir) / "es-extract.jsonl.gz"
        )

        print("  Parsing kaikki extract ...")
        senses_map = _parse_kaikki(gz_path, words)

    print(f"  Found definitions for {len(senses_map)} words.")

    # Build output sorted by rank.
    vocab: list[dict[str, object]] = []
    matched = 0
    missing = 0

    for key, entry in sorted(
        words.items(), key=lambda kv: kv[1]["rank"]
    ):
        senses = senses_map.get(key, [])
        definition = "; ".join(senses) if senses else ""

        vocab.append({
            "rank": entry["rank"],
            "word": entry["word"],
            "pos": entry["pos"],
            "frequency": entry["frequency"],
            "senses": senses,
            "definition": definition,
            "gender": entry.get("gender"),
            "conjugation_group": entry.get(
                "conjugation_group"
            ),
            "tags": entry.get("tags", []),
            "cefr": entry.get("cefr"),
        })

        if senses:
            matched += 1
        else:
            missing += 1

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT, "w", encoding="utf-8") as fh:
        json.dump(vocab, fh, ensure_ascii=False, indent=2)

    print(
        f"\n  Wrote {len(vocab)} words to {_OUTPUT}"
        f"\n  With definitions: {matched}"
        f"\n  Without definitions: {missing}"
        f" ({missing / len(vocab) * 100:.1f}%)"
    )


if __name__ == "__main__":
    print("Building Spanish monolingual definitions ...\n")
    main()
    print("\nDone!")
