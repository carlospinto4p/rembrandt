"""Advanced word selection with `select_words()`.

Demonstrates session modes (`LEARN_NEW`, `REVIEW_DUE`, `MIXED`),
`max_new` / `max_review` caps, `prioritize_weak`, `word_ids`
filtering, and `exclude_word_ids` for sibling burying.

Usage::

    uv run python examples/exercises/11_word_selection.py
"""

from datetime import datetime, timedelta
from pathlib import Path

from rembrandt import Database, SessionMode, Word
from rembrandt.models import UserProgress
from rembrandt.spaced_repetition import review, select_words

_DB_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "selection_demo.db"
)

_WORDS = [
    ("cat", "gato"),
    ("dog", "perro"),
    ("house", "casa"),
    ("book", "libro"),
    ("water", "agua"),
    ("sun", "sol"),
    ("moon", "luna"),
    ("tree", "árbol"),
]


def _print_words(label: str, words: list[Word]) -> None:
    """Print a labelled word list."""
    names = [w.word_from for w in words]
    print(f"  {label}: {names}")


def main() -> None:
    _DB_PATH.unlink(missing_ok=True)

    with Database(_DB_PATH) as db:
        user = db.register_user("demo", "demo")

        db.add_words([
            Word(
                language_from="en", language_to="es",
                word_from=en, word_to=es,
            )
            for en, es in _WORDS
        ])

        # Review the first 4 words and set next_review
        # in the past so they appear as "due".
        all_words = db.get_words("en", "es")
        yesterday = datetime.now() - timedelta(days=1)
        for w in all_words[:4]:
            p = UserProgress(
                user_id=user.id, word_id=w.id,
            )
            p = review(p, 4)
            # Several passes to reach REVIEW state
            p = review(p, 4)
            p = review(p, 4)
            # Force next_review into the past
            p = p.model_copy(
                update={"next_review": yesterday},
            )
            db.upsert_progress(p)

        # Also record some wrong answers for "cat" and "dog"
        # so they are detected as weak words.
        for _ in range(5):
            db.record_answer(
                user.id, all_words[0].id,
                "flashcard", False, 1,
            )
            db.record_answer(
                user.id, all_words[1].id,
                "flashcard", False, 1,
            )

        # --- Session modes ---
        print("=== Session Modes ===\n")

        new_only = select_words(
            db, user.id, "en", "es", count=5,
            mode=SessionMode.LEARN_NEW,
        )
        _print_words("LEARN_NEW", new_only)

        due_only = select_words(
            db, user.id, "en", "es", count=5,
            mode=SessionMode.REVIEW_DUE,
        )
        _print_words("REVIEW_DUE", due_only)

        mixed = select_words(
            db, user.id, "en", "es", count=5,
            mode=SessionMode.MIXED,
        )
        _print_words("MIXED", mixed)

        # --- Caps: max_new and max_review ---
        print("\n=== Caps ===\n")

        capped = select_words(
            db, user.id, "en", "es", count=10,
            max_new=2, max_review=1,
        )
        _print_words("max_new=2, max_review=1", capped)

        # --- Prioritise weak words ---
        print("\n=== Prioritise Weak ===\n")

        normal = select_words(
            db, user.id, "en", "es", count=4,
            mode=SessionMode.REVIEW_DUE,
        )
        _print_words("Normal order", normal)

        weak_first = select_words(
            db, user.id, "en", "es", count=4,
            mode=SessionMode.REVIEW_DUE,
            prioritize_weak=True,
        )
        _print_words("Weak first", weak_first)

        # --- word_ids filtering (lesson scope) ---
        print("\n=== word_ids Filtering ===\n")

        subset_ids = [
            all_words[0].id, all_words[4].id,
            all_words[6].id,
        ]
        subset = select_words(
            db, user.id, "en", "es", count=5,
            word_ids=subset_ids,
        )
        _print_words(
            f"Only ids {subset_ids}", subset,
        )

        # --- exclude_word_ids (sibling burying) ---
        print("\n=== exclude_word_ids (Burying) ===\n")

        exclude = {all_words[0].id, all_words[1].id}
        buried = select_words(
            db, user.id, "en", "es", count=5,
            exclude_word_ids=exclude,
        )
        _print_words(
            f"Excluding ids {sorted(exclude)}", buried,
        )

    _DB_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
