"""Build a ranked Spanish-English vocabulary JSON file.

Downloads frequency and dictionary data from
github.com/doozan/spanish_data (CC-BY-SA), joins them, and
writes a clean JSON array of the top 10,000 content words
to ``data/spanish_top10000.json``.

Usage::

    uv run python scripts/build_spanish_vocab.py
"""

import csv
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

# Allow importing sibling scripts when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from topic_classifier import classify  # noqa: E402

_BASE_URL = (
    "https://raw.githubusercontent.com"
    "/doozan/spanish_data/master"
)
_FREQ_URL = f"{_BASE_URL}/frequency.csv"
_DICT_URL = f"{_BASE_URL}/es-en.data"

_CONTENT_POS = {"v", "n", "adj", "adv"}
_TARGET_COUNT = 10_000

_ROOT = Path(__file__).resolve().parent.parent
_OUTPUT = _ROOT / "data" / "spanish_top10000.json"


def _download(url: str, dest: Path) -> Path:
    """Download `url` to `dest`, overwriting if it exists."""
    print(f"  Downloading {url.rsplit('/', 1)[-1]} ...")
    urllib.request.urlretrieve(url, dest)
    return dest


def _parse_frequency(
    path: Path,
) -> list[tuple[str, str, int]]:
    """Parse frequency.csv into (lemma, pos, count) triples.

    Only keeps content-word POS tags (v, n, adj, adv) and
    skips rows flagged as DUPLICATE.
    """
    results: list[tuple[str, str, int]] = []
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            pos = row["pos"].strip()
            flags = row.get("flags", "").strip()
            if pos not in _CONTENT_POS:
                continue
            if "DUPLICATE" in flags:
                continue
            lemma = row["spanish"].strip()
            count = int(row["count"])
            results.append((lemma, pos, count))
    return results


def _parse_dictionary(
    path: Path,
) -> dict[str, list[tuple[str, str, str | None]]]:
    """Parse es-en.data into {lemma: [(pos, gloss, gender), ...]}.

    Each entry in the file is separated by a line of
    underscores. Within an entry the first line is the lemma,
    subsequent indented lines carry POS, gloss, and gender
    information.  Only the first gloss per POS section is kept.
    """
    dictionary: dict[
        str, list[tuple[str, str, str | None]]
    ] = {}

    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    for block in text.split("_____\n"):
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        lemma = lines[0].strip()

        current_pos: str | None = None
        current_gender: str | None = None
        got_gloss = False

        for line in lines[1:]:
            stripped = line.strip()

            if stripped.startswith("pos: "):
                current_pos = stripped[5:].strip()
                current_gender = None
                got_gloss = False
                continue

            if stripped.startswith("g: "):
                g = stripped[3:].strip()
                if g in ("m", "f"):
                    current_gender = g
                continue

            if (
                stripped.startswith("gloss: ")
                and current_pos is not None
                and not got_gloss
            ):
                gloss = stripped[7:].strip()
                dictionary.setdefault(lemma, []).append(
                    (current_pos, gloss, current_gender)
                )
                got_gloss = True

    return dictionary


def _cefr_level(rank: int) -> str:
    """Map a frequency rank to a CEFR level.

    :param rank: 1-based frequency rank.
    :return: CEFR level string (`"A1"` through `"C2"`).
    """
    if rank <= 500:
        return "A1"
    if rank <= 1500:
        return "A2"
    if rank <= 3500:
        return "B1"
    if rank <= 6500:
        return "B2"
    if rank <= 8500:
        return "C1"
    return "C2"


def _conjugation_group(word: str, pos: str) -> str | None:
    """Derive the conjugation group from a verb's infinitive.

    :param word: The lemma (infinitive form for verbs).
    :param pos: Part-of-speech tag.
    :return: `"ar"`, `"er"`, or `"ir"` for verbs, `None`
        otherwise.
    """
    if pos != "v":
        return None
    for suffix in ("ar", "er", "ir"):
        if word.endswith(suffix):
            return suffix
    return None


def _lookup_gloss(
    dictionary: dict[str, list[tuple[str, str, str | None]]],
    lemma: str,
    pos: str,
) -> tuple[str, str | None] | None:
    """Find the best gloss and gender for `lemma` with `pos`.

    Tries an exact (lemma, pos) match first, then falls back
    to the first gloss for that lemma regardless of POS.

    :return: `(gloss, gender)` or `None` if no entry found.
    """
    entries = dictionary.get(lemma)
    if not entries:
        return None

    # Exact POS match.
    for entry_pos, gloss, gender in entries:
        if entry_pos == pos:
            return gloss, gender

    # Fallback: first available gloss.
    return entries[0][1], entries[0][2]


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        freq_path = _download(_FREQ_URL, tmp / "frequency.csv")
        dict_path = _download(_DICT_URL, tmp / "es-en.data")

        print("  Parsing frequency list ...")
        freq_list = _parse_frequency(freq_path)
        print(f"  {len(freq_list)} content words found.")

        print("  Parsing dictionary ...")
        dictionary = _parse_dictionary(dict_path)
        print(f"  {len(dictionary)} lemmas loaded.")

    print("  Joining data ...")
    vocab: list[dict[str, object]] = []
    skipped = 0
    rank = 0

    for lemma, pos, count in freq_list:
        result = _lookup_gloss(dictionary, lemma, pos)
        if result is None:
            skipped += 1
            continue

        gloss, gender = result
        conj = _conjugation_group(lemma, pos)
        tags = classify(gloss)

        rank += 1
        vocab.append({
            "rank": rank,
            "word": lemma,
            "pos": pos,
            "definition": gloss,
            "frequency": count,
            "gender": gender,
            "conjugation_group": conj,
            "tags": tags,
            "cefr": _cefr_level(rank),
        })
        if rank >= _TARGET_COUNT:
            break

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT, "w", encoding="utf-8") as fh:
        json.dump(vocab, fh, ensure_ascii=False, indent=2)

    print(
        f"\n  Wrote {len(vocab)} words to {_OUTPUT}"
        f" ({skipped} skipped — no gloss found)."
    )


if __name__ == "__main__":
    print("Building Spanish vocabulary ...\n")
    main()
    print("\nDone!")
