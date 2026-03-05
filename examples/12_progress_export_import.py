"""Progress export and import.

Demonstrates `db.export_progress()` and `db.import_progress()`.
Creates a database with vocabulary, runs a short session to
generate spaced-repetition progress, exports it, then imports
the records into a second database and verifies the roundtrip.

Usage::

    uv run python examples/12_progress_export_import.py
"""

from pathlib import Path

from rembrandt import Database, Session, Word

_ROOT = Path(__file__).resolve().parent.parent / "data"
_DB_SRC = _ROOT / "export_demo_src.db"
_DB_DST = _ROOT / "export_demo_dst.db"


def main() -> None:
    _DB_SRC.unlink(missing_ok=True)
    _DB_DST.unlink(missing_ok=True)

    words = [
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
            gender="m",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="house", word_to="casa",
            gender="f",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="to speak", word_to="hablar",
            conjugation_group="ar",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="water", word_to="agua",
        ),
    ]

    # --- Step 1: Build source DB and generate progress ---
    with Database(_DB_SRC) as src:
        src.add_words(words)
        user = src.register_user("demo", "demo")

        session = Session(
            db=src,
            user_id=user.id,
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
            f"Session: {stats.correct}/{stats.total} correct"
        )

        # --- Step 2: Export progress ---
        records = src.export_progress(user.id)
        print(f"Exported {len(records)} progress records")

    # --- Step 3: Import into a fresh DB ---
    with Database(_DB_DST) as dst:
        dst.add_words(words)
        dst.register_user("demo", "demo")
        count = dst.import_progress(records)
        print(f"Imported {count} records into new DB")

        # --- Step 4: Verify roundtrip ---
        reimported = dst.export_progress(user.id)
        assert len(reimported) == len(records), (
            f"Mismatch: {len(reimported)} != {len(records)}"
        )
        print(
            f"Roundtrip verified: {len(reimported)} records "
            f"match"
        )

    # Clean up demo files
    _DB_SRC.unlink(missing_ok=True)
    _DB_DST.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
