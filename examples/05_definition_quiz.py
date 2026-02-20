"""Definition-based vocabulary quiz.

Demonstrates monolingual (EN-EN) definition learning, where
you learn words through their definitions rather than
translations. Uses all three definition-mode exercise types:
multiple choice, reverse flashcard, and self-graded.
"""

from pathlib import Path

from rembrandt import Database, ExerciseType, Session

_DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "definition_quiz.db"
)


def main() -> None:
    fresh = not _DB_PATH.exists()
    db = Database(_DB_PATH)

    if fresh:
        db.add_words([
            ("en", "en", "ephemeral",
             "lasting for a very short time"),
            ("en", "en", "ubiquitous",
             "present or found everywhere"),
            ("en", "en", "candid",
             "truthful and straightforward"),
            ("en", "en", "pragmatic",
             "dealing with things practically"),
            ("en", "en", "verbose",
             "using more words than needed"),
            ("en", "en", "diligent",
             "showing care and effort in one's work"),
        ])

    session = Session(
        db=db,
        user_id="demo",
        language_from="en",
        language_to="en",
    )

    print("=== Definition Quiz ===")
    print("Learn English words through their definitions.\n")

    for i in range(4):
        exercise = session.next_exercise()
        if exercise is None:
            break

        print(f"--- Exercise {i + 1} ---")
        etype = exercise.exercise_type

        if etype == ExerciseType.MULTIPLE_CHOICE:
            print(
                f"What does '{exercise.word.word_from}' "
                "mean?"
            )
            for idx, opt in enumerate(exercise.options, 1):
                print(f"  {idx}. {opt}")
            result = session.answer(exercise.word.word_to)

        elif etype == ExerciseType.REVERSE_FLASHCARD:
            print(
                f"Definition: {exercise.word.word_to}"
            )
            print("Which word matches this definition?")
            result = session.answer(exercise.word.word_from)

        else:  # SELF_GRADED
            print(
                f"Word: {exercise.word.word_from}"
            )
            print("(Think of the definition...)")
            print(
                f"  -> {exercise.word.word_to}"
            )
            print("Self-assessment: 4/5")
            result = session.answer(quality=4)

        status = "Correct!" if result.correct else "Wrong"
        print(f"-> {status}")
        print()

    db.close()
    print("Done!")


if __name__ == "__main__":
    main()
