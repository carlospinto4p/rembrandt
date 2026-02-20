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
import tempfile
import urllib.request
from pathlib import Path

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
) -> dict[str, list[tuple[str, str]]]:
    """Parse es-en.data into {lemma: [(pos, gloss), ...]}.

    Each entry in the file is separated by a line of
    underscores. Within an entry the first line is the lemma,
    subsequent indented lines carry POS and gloss information.
    Only the first gloss per POS section is kept.
    """
    dictionary: dict[str, list[tuple[str, str]]] = {}

    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    for block in text.split("_____\n"):
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        lemma = lines[0].strip()

        current_pos: str | None = None
        got_gloss = False

        for line in lines[1:]:
            stripped = line.strip()

            if stripped.startswith("pos: "):
                current_pos = stripped[5:].strip()
                got_gloss = False
                continue

            if (
                stripped.startswith("gloss: ")
                and current_pos is not None
                and not got_gloss
            ):
                gloss = stripped[7:].strip()
                dictionary.setdefault(lemma, []).append(
                    (current_pos, gloss)
                )
                got_gloss = True

    return dictionary


def _lookup_gloss(
    dictionary: dict[str, list[tuple[str, str]]],
    lemma: str,
    pos: str,
) -> str | None:
    """Find the best gloss for `lemma` with `pos`.

    Tries an exact (lemma, pos) match first, then falls back
    to the first gloss for that lemma regardless of POS.
    """
    entries = dictionary.get(lemma)
    if not entries:
        return None

    # Exact POS match.
    for entry_pos, gloss in entries:
        if entry_pos == pos:
            return gloss

    # Fallback: first available gloss.
    return entries[0][1]


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
        gloss = _lookup_gloss(dictionary, lemma, pos)
        if gloss is None:
            skipped += 1
            continue

        rank += 1
        vocab.append({
            "rank": rank,
            "word": lemma,
            "pos": pos,
            "definition": gloss,
            "frequency": count,
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
