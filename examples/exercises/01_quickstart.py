"""Quick-start example for Rembrandt.

Creates a session from an inline word list and runs a few exercises,
printing the type, prompt, and auto-answer for each one.

Usage::

    uv run python examples/exercises/01_quickstart.py
"""

from pathlib import Path

from rembrandt import quick_session
from rembrandt.models import ExerciseType

_DB_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "quickstart.db"
)

_WORDS = [
    {"word": "cat", "definition": "gato"},
    {"word": "dog", "definition": "perro"},
    {"word": "house", "definition": "casa"},
    {"word": "book", "definition": "libro"},
    {"word": "water", "definition": "agua"},
    {"word": "sun", "definition": "sol"},
]


def main() -> None:
    session = quick_session(
        _WORDS,
        db_path=_DB_PATH,
        language_from="en",
        language_to="es",
    )

    for i in range(4):
        exercise = session.next_exercise()
        if exercise is None:
            break

        print(f"--- Exercise {i + 1} ---")
        print(f"Type: {exercise.exercise_type.value}")
        print(f"Translate: {exercise.word.word_from}")

        if exercise.exercise_type == (
            ExerciseType.MULTIPLE_CHOICE
        ):
            for idx, opt in enumerate(exercise.options, 1):
                print(f"  {idx}. {opt}")

        result = session.answer(exercise.word.word_to)
        status = "Correct!" if result.correct else "Wrong"
        print(f"Answer: {result.expected} -> {status}\n")

    stats = session.summary()
    print(
        f"Score: {stats.correct}/{stats.total} "
        f"({stats.accuracy_pct}%)"
    )
    session.db.close()


if __name__ == "__main__":
    main()
