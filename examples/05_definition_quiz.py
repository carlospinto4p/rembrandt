"""Definition-based vocabulary quiz.

Demonstrates monolingual (EN-EN) definition learning, where
you learn words through their definitions rather than
translations. Handles all three definition-mode exercise types:
multiple choice, reverse flashcard, and self-graded.

Usage::

    uv run python examples/05_definition_quiz.py
"""

from pathlib import Path

from rembrandt import Database, Session, Word
from rembrandt.models import ExerciseType

_DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "definition_quiz.db"
)


def main() -> None:
    fresh = not _DB_PATH.exists()

    with Database(_DB_PATH) as db:
        if fresh:
            db.add_words([
                Word(
                    language_from="en", language_to="en",
                    word_from="ephemeral",
                    word_to=(
                        "lasting for a very short time"
                    ),
                ),
                Word(
                    language_from="en", language_to="en",
                    word_from="ubiquitous",
                    word_to=(
                        "present or found everywhere"
                    ),
                ),
                Word(
                    language_from="en", language_to="en",
                    word_from="candid",
                    word_to=(
                        "truthful and straightforward"
                    ),
                ),
                Word(
                    language_from="en", language_to="en",
                    word_from="pragmatic",
                    word_to=(
                        "dealing with things practically"
                    ),
                ),
                Word(
                    language_from="en", language_to="en",
                    word_from="verbose",
                    word_to=(
                        "using more words than needed"
                    ),
                ),
                Word(
                    language_from="en", language_to="en",
                    word_from="diligent",
                    word_to=(
                        "showing care and effort in"
                        " one's work"
                    ),
                ),
            ])

        user = db.get_user("demo")
        if user is None:
            user = db.register_user("demo", "demo")

        session = Session(
            db=db,
            user_id=user.id,
            language_from="en",
            language_to="en",
        )

        print("=== Definition Quiz ===")
        print(
            "Learn English words through their "
            "definitions."
        )
        print("Type your answer (or 'q' to quit).\n")

        try:
            total = 0
            while True:
                exercise = session.next_exercise()
                if exercise is None:
                    print("No more words available.")
                    break

                total += 1
                etype = exercise.exercise_type
                print(f"--- Question {total} ---")

                if etype == ExerciseType.MULTIPLE_CHOICE:
                    print(
                        "What does "
                        f"'{exercise.word.word_from}' "
                        "mean?"
                    )
                    for idx, opt in enumerate(
                        exercise.options, 1
                    ):
                        print(f"  {idx}. {opt}")
                    answer = input("> ").strip()
                    if answer.lower() == "q":
                        break
                    result = session.answer(answer)

                elif etype == (
                    ExerciseType.REVERSE_FLASHCARD
                ):
                    print(
                        "Definition: "
                        f"{exercise.word.word_to}"
                    )
                    print("Which word matches?")
                    answer = input("> ").strip()
                    if answer.lower() == "q":
                        break
                    result = session.answer(answer)

                else:  # SELF_GRADED
                    print(
                        f"Word: {exercise.word.word_from}"
                    )
                    print("(Think of the definition...)")
                    input(
                        "Press Enter to reveal the "
                        "answer."
                    )
                    print(
                        f"  -> {exercise.word.word_to}"
                    )
                    while True:
                        answer = input(
                            "Rate your recall (0-5): "
                        ).strip()
                        if answer.lower() == "q":
                            break
                        if (
                            answer.isdigit()
                            and 0 <= int(answer) <= 5
                        ):
                            break
                        print("  Please enter 0-5.")
                    if answer.lower() == "q":
                        break
                    result = session.answer(
                        quality=int(answer),
                    )

                if result.correct:
                    print("Correct!\n")
                else:
                    print(
                        "Wrong — expected: "
                        f"'{result.expected}'\n"
                    )

        except (KeyboardInterrupt, EOFError):
            print()

        stats = session.summary()
        if stats.total:
            print(
                f"Score: {stats.correct}/{stats.total} "
                f"({stats.accuracy_pct}%)"
            )


if __name__ == "__main__":
    main()
