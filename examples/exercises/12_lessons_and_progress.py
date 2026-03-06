"""Lessons and progress tracking.

Loads the pre-built Spanish lessons from JSON, picks a lesson,
runs a short lesson-scoped session, then prints progress stats.
Demonstrates `load_lessons()`, `lesson_progress()`, `Session`
with `word_ids`, and `SessionMode`.

Requires the data files in ``data/`` — see `README.md`.

Usage::

    uv run python examples/exercises/12_lessons_and_progress.py
"""

from pathlib import Path

from rembrandt import (
    Session,
    SessionMode,
    lesson_progress,
    load_lessons,
    quick_session,
)

_ROOT = Path(__file__).resolve().parent.parent.parent
_VOCAB_PATH = _ROOT / "data" / "spanish_top10000.json"
_LESSONS_PATH = _ROOT / "data" / "spanish_lessons.json"
_DB_PATH = _ROOT / "data" / "lessons_demo.db"
_TOP_N = 500


def main() -> None:
    for path in (_VOCAB_PATH, _LESSONS_PATH):
        if not path.exists():
            print(f"Data file not found: {path}")
            return

    # --- Step 1: Load vocabulary into DB ---
    # quick_session handles first-run loading; swap keys
    # so word_from=English definition, word_to=Spanish
    # word — matching the orientation load_lessons expects.
    qs = quick_session(
        _VOCAB_PATH,
        db_path=_DB_PATH,
        language_from="en",
        language_to="es",
        word_from_key="definition",
        word_to_key="word",
        limit=_TOP_N,
    )
    db = qs.db

    # --- Step 2: Load lessons ---
    lessons = db.get_lessons("en", "es")
    if not lessons:
        lessons = load_lessons(
            _LESSONS_PATH,
            _VOCAB_PATH,
            db,
            language_from="en",
            language_to="es",
        )
    print(f"Loaded {len(lessons)} lessons.\n")

    # Pick the first A1 lesson
    lesson = next(
        (ls for ls in lessons if ls.cefr == "A1"), None,
    )
    if lesson is None:
        print("No A1 lesson found.")
        db.close()
        return

    print(
        f"Lesson: {lesson.title} "
        f"({lesson.word_count} words, "
        f"CEFR {lesson.cefr})"
    )

    # --- Step 3: Run a lesson-scoped session ---
    user = db.get_user("default")
    if user is None:
        user = db.register_user("default", "default")

    session = Session(
        db=db,
        user_id=user.id,
        language_from="en",
        language_to="es",
        mode=SessionMode.LEARN_NEW,
        word_ids=lesson.word_ids,
    )

    rounds = min(5, lesson.word_count)
    for i in range(rounds):
        exercise = session.next_exercise()
        if exercise is None:
            break
        print(
            f"  {i + 1}. {exercise.word.word_from[:40]} "
            f"-> {exercise.word.word_to}"
        )
        session.answer(exercise.word.word_to)

    stats = session.summary()
    print(
        f"\nSession: {stats.correct}/{stats.total} correct"
    )

    # --- Step 4: Check lesson progress ---
    lp = lesson_progress(db, user.id, lesson)
    print(f"\nLesson progress for '{lesson.title}':")
    print(
        f"  Studied : {lp.words_studied}/{lp.words_total}"
        f"  ({lp.completion_pct}%)"
    )
    print(
        f"  Mastered: {lp.words_mastered}/{lp.words_total}"
        f"  ({lp.mastery_pct}%)"
    )

    db.close()


if __name__ == "__main__":
    main()
