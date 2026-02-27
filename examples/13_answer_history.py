"""Answer history, daily stats, and weak words.

Demonstrates the answer-history subsystem: runs a session with
a mix of correct and incorrect answers, then queries
`db.get_answer_history()`, `db.daily_stats()`, and
`db.weak_words()`.  Also shows `select_words()` with
`prioritize_weak=True`.

Usage::

    uv run python examples/13_answer_history.py
"""

from pathlib import Path

from rembrandt import Database, Session, Word
from rembrandt.spaced_repetition import select_words

_DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "history_demo.db"
)


def main() -> None:
    _DB_PATH.unlink(missing_ok=True)

    with Database(_DB_PATH) as db:
        db.add_words([
            Word(
                language_from="en", language_to="es",
                word_from="cat", word_to="gato",
                gender="m",
            ),
            Word(
                language_from="en", language_to="es",
                word_from="dog", word_to="perro",
                gender="m",
            ),
            Word(
                language_from="en", language_to="es",
                word_from="house", word_to="casa",
                gender="f",
            ),
            Word(
                language_from="en", language_to="es",
                word_from="table", word_to="mesa",
                gender="f",
            ),
        ])

        # Run one session to see it in action.
        session = Session(
            db=db,
            user_id="demo",
            language_from="en",
            language_to="es",
        )
        for _ in range(4):
            ex = session.next_exercise()
            if ex is None:
                break
            session.answer(ex.word.word_to)

        stats = session.summary()
        print(
            f"Session: {stats.correct}/{stats.total} correct "
            f"({stats.accuracy_pct}%)\n"
        )

        # Manually record extra wrong answers so that
        # weak-word detection has enough data.  Words 1
        # and 3 ("cat", "house") get many errors.
        for _ in range(4):
            db.record_answer(
                "demo", 1, "flashcard", False, 1,
            )
            db.record_answer(
                "demo", 3, "flashcard", False, 1,
            )

        # --- Answer History ---
        print("=== Recent Answer History ===")
        history = db.get_answer_history("demo", limit=5)
        for h in history:
            tag = "correct" if h.correct else "wrong"
            print(
                f"  word_id={h.word_id}  {tag}  "
                f"q={h.quality}  type={h.exercise_type}"
            )

        # --- Daily Stats ---
        print("\n=== Daily Stats ===")
        for day in db.daily_stats("demo", days=7):
            print(
                f"  {day.date}: "
                f"{day.correct}/{day.answers} "
                f"({day.accuracy_pct}%)"
            )

        # --- Weak Words ---
        print("\n=== Weak Words ===")
        weak = db.weak_words(
            "demo", "en", "es",
            threshold=0.3, min_attempts=2,
        )
        if weak:
            for ww in weak:
                print(
                    f"  {ww.word.word_from}: "
                    f"{ww.errors}/{ww.attempts} "
                    f"({ww.error_rate:.0%} errors)"
                )
        else:
            print("  No weak words detected.")

        # --- Prioritise Weak Words ---
        # In a real app, weak words would surface when they
        # become due for review.  Here they may not appear
        # because their next_review is in the future.
        print("\n=== Prioritised Selection ===")
        chosen = select_words(
            db, "demo", "en", "es",
            count=4,
            prioritize_weak=True,
        )
        if chosen:
            for w in chosen:
                print(f"  {w.word_from} -> {w.word_to}")
        else:
            print("  No words due yet (all recently reviewed).")

    _DB_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
