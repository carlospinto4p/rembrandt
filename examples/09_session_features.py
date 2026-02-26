"""Session features: hints, skip, and statistics.

Runs a short quiz demonstrating `Session.hint()`,
`Session.skip()`, and `Session.summary()`.

Usage::

    uv run python examples/09_session_features.py
"""

from pathlib import Path

from rembrandt import Database, Session, Word

_DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "session_features.db"
)


def main() -> None:
    _DB_PATH.unlink(missing_ok=True)
    db = Database(_DB_PATH)

    db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="dog", word_to="perro",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="house", word_to="casa",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="sun", word_to="sol",
        ),
    ])

    session = Session(
        db=db,
        user_id="demo",
        language_from="en",
        language_to="es",
    )

    # --- Exercise 1: use a hint, then answer ---
    ex = session.next_exercise()
    print(f"Q1: Translate '{ex.word.word_from}'")

    hint = session.hint()
    print(
        f"  Hint: starts with '{hint.first_letter}', "
        f"{hint.word_length} letters -> {hint.pattern}"
    )

    result = session.answer(ex.word.word_to)
    print(f"  Answer: {result.expected} -> Correct!\n")

    # --- Exercise 2: skip it ---
    ex = session.next_exercise()
    print(f"Q2: Translate '{ex.word.word_from}'")

    skipped = session.skip()
    print(
        f"  Skipped '{skipped.word.word_from}' "
        f"(no effect on progress)\n"
    )

    # --- Exercise 3: wrong answer ---
    ex = session.next_exercise()
    print(f"Q3: Translate '{ex.word.word_from}'")

    result = session.answer("wrong")
    print(
        f"  Answer: 'wrong' -> "
        f"{'Correct' if result.correct else 'Incorrect'} "
        f"(expected: {result.expected})\n"
    )

    # --- Session summary ---
    stats = session.summary()
    print("=== Session Summary ===")
    print(f"  Total answered : {stats.total}")
    print(f"  Correct        : {stats.correct}")
    print(f"  Incorrect      : {stats.incorrect}")
    print(f"  Current streak : {stats.streak}")
    print(f"  Best streak    : {stats.best_streak}")
    print(f"  Accuracy       : {stats.accuracy_pct}%")

    db.close()


if __name__ == "__main__":
    main()
