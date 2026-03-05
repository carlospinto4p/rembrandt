"""Organising vocabulary by tags and CEFR levels.

Shows how to add words with `tags` and `cefr`, filter them in
application code, and run tag-scoped or level-scoped sessions.

Usage::

    uv run python examples/18_tags_and_cefr.py
"""

from pathlib import Path

from rembrandt import Database, Session, Word

_DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "tags_cefr_demo.db"
)

_WORDS = [
    # Animals (A1)
    Word(
        language_from="en", language_to="es",
        word_from="cat", word_to="gato",
        tags=["animals"], cefr="A1",
    ),
    Word(
        language_from="en", language_to="es",
        word_from="dog", word_to="perro",
        tags=["animals"], cefr="A1",
    ),
    Word(
        language_from="en", language_to="es",
        word_from="whale", word_to="ballena",
        tags=["animals", "nature"], cefr="B1",
    ),
    # Food (A1-A2)
    Word(
        language_from="en", language_to="es",
        word_from="bread", word_to="pan",
        tags=["food"], cefr="A1",
    ),
    Word(
        language_from="en", language_to="es",
        word_from="cheese", word_to="queso",
        tags=["food"], cefr="A2",
    ),
    # Nature (B1)
    Word(
        language_from="en", language_to="es",
        word_from="forest", word_to="bosque",
        tags=["nature"], cefr="B1",
    ),
    Word(
        language_from="en", language_to="es",
        word_from="river", word_to="río",
        tags=["nature"], cefr="B1",
    ),
]


def main() -> None:
    _DB_PATH.unlink(missing_ok=True)

    with Database(_DB_PATH) as db:
        user = db.register_user("demo", "demo")
        db.add_words(_WORDS)
        all_words = db.get_words("en", "es")

        # --- Show all words with their metadata ---
        print("=== All Words ===\n")
        for w in all_words:
            print(
                f"  {w.word_from:<10} -> {w.word_to:<10} "
                f"cefr={w.cefr}  tags={w.tags}"
            )

        # --- Filter by tag ---
        print("\n=== Filter by Tag: 'animals' ===\n")
        animals = [
            w for w in all_words if "animals" in w.tags
        ]
        for w in animals:
            print(f"  {w.word_from} -> {w.word_to}")

        # --- Filter by CEFR level ---
        print("\n=== Filter by CEFR: 'A1' ===\n")
        a1_words = [
            w for w in all_words if w.cefr == "A1"
        ]
        for w in a1_words:
            print(
                f"  {w.word_from} -> {w.word_to} "
                f"({w.tags})"
            )

        # --- Tag-scoped session ---
        print("\n=== Tag-Scoped Session: 'nature' ===\n")
        nature = [
            w for w in all_words if "nature" in w.tags
        ]
        nature_ids = [w.id for w in nature]

        session = Session(
            db=db,
            user_id=user.id,
            language_from="en",
            language_to="es",
            word_ids=nature_ids,
        )

        for _ in range(len(nature_ids)):
            ex = session.next_exercise()
            if ex is None:
                break
            result = session.answer(ex.word.word_to)
            status = "ok" if result.correct else "wrong"
            print(
                f"  {ex.word.word_from} -> "
                f"{result.expected} [{status}]"
            )

        stats = session.summary()
        print(
            f"\n  Score: {stats.correct}/{stats.total} "
            f"({stats.accuracy_pct}%)"
        )

        # --- Level-based study flow ---
        print("\n=== Level-Based Flow ===\n")
        for level in ("A1", "A2", "B1"):
            level_words = [
                w for w in all_words if w.cefr == level
            ]
            names = [w.word_from for w in level_words]
            print(f"  {level}: {names}")

    _DB_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
