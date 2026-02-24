"""Spanish-English translation quiz.

Loads ranked Spanish vocabulary from a pre-built JSON file and
quizzes you on English translations. Uses `quick_session()` to
handle database creation, word loading, and session setup in a
single call. Progress is persisted between runs.

Usage::

    uv run python examples/06_spanish_translation_quiz.py
"""

from pathlib import Path

from rembrandt import quick_session
from rembrandt.models import ExerciseType

_ROOT = Path(__file__).resolve().parent.parent
_VOCAB_PATH = _ROOT / "data" / "spanish_top10000.json"
_DB_PATH = _ROOT / "data" / "spanish_vocab.db"
_TOP_N = 500


def main() -> None:
    if not _VOCAB_PATH.exists():
        print(
            f"Vocabulary file not found: {_VOCAB_PATH}\n"
            "Run the build script first:\n"
            "  uv run python scripts/build_spanish_vocab.py"
        )
        return

    session = quick_session(
        _VOCAB_PATH,
        db_path=_DB_PATH,
        language_from="es",
        language_to="en",
        user_id="demo",
        limit=_TOP_N,
    )

    print("=== Spanish-English Translation Quiz ===")
    print("Type your answer (or 'q' to quit).\n")

    correct = 0
    total = 0

    while True:
        exercise = session.next_exercise()
        if exercise is None:
            break

        total += 1
        etype = exercise.exercise_type

        print(f"--- Question {total} ---")
        print(f"What does '{exercise.word.word_from}' mean?")

        if etype == ExerciseType.MULTIPLE_CHOICE:
            for idx, opt in enumerate(exercise.options, 1):
                print(f"  {idx}. {opt}")

        answer = input("> ").strip()
        if answer.lower() == "q":
            total -= 1
            break

        result = session.answer(answer)
        if result.correct:
            correct += 1
            print("Correct!\n")
        else:
            print(f"Wrong — expected: {result.expected}\n")

    if total > 0:
        pct = correct / total * 100
        print(f"Score: {correct}/{total} ({pct:.0f}%)")

    session.db.close()


if __name__ == "__main__":
    main()
