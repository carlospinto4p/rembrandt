"""CRUD operations for words and lessons.

Shows how to create, update, and delete words and lessons
using the `Database` API.

Usage::

    uv run python examples/infrastructure/01_crud_operations.py
"""

from pathlib import Path

from rembrandt import Database, Lesson, Word

_DB_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "crud_demo.db"
)


def main() -> None:
    _DB_PATH.unlink(missing_ok=True)
    db = Database(_DB_PATH)

    # --- Words: create, update, delete ---
    print("=== Word CRUD ===\n")

    word = db.add_word(
        "en", "es", "cat", "gato", gender="m",
    )
    print(f"Created: {word.word_from} -> {word.word_to}")

    word = word.model_copy(
        update={"word_to": "gato/a", "gender": None},
    )
    word = db.update_word(word)
    print(f"Updated: {word.word_from} -> {word.word_to}")

    words = db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="dog", word_to="perro",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="bird", word_to="pájaro",
        ),
    ])
    print(f"Bulk added: {[w.word_from for w in words]}")

    db.delete_word(words[1].id)
    print(f"Deleted: {words[1].word_from}")

    remaining = db.get_words("en", "es")
    print(
        f"Remaining: "
        f"{[w.word_from for w in remaining]}\n"
    )

    # --- Lessons: create, update, delete ---
    print("=== Lesson CRUD ===\n")

    word_ids = [w.id for w in remaining]
    lesson = db.add_lesson(Lesson(
        title="Animals & Things",
        description="A mixed lesson",
        language_from="en",
        language_to="es",
        word_count=len(word_ids),
        word_ids=word_ids,
    ))
    print(
        f"Created lesson: '{lesson.title}' "
        f"({lesson.word_count} words)"
    )

    lesson = lesson.model_copy(
        update={
            "title": "Basics",
            "word_ids": word_ids[:1],
            "word_count": 1,
        },
    )
    lesson = db.update_lesson(lesson)
    print(
        f"Updated lesson: '{lesson.title}' "
        f"({lesson.word_count} word)"
    )

    fetched = db.get_lesson(lesson.id)
    print(
        f"Fetched: '{fetched.title}', "
        f"word_ids={fetched.word_ids}"
    )

    db.delete_lesson(lesson.id)
    print(f"Deleted lesson id={lesson.id}")

    all_lessons = db.get_lessons("en", "es")
    print(f"Remaining lessons: {len(all_lessons)}")

    db.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
