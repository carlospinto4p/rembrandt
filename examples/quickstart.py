"""Quick-start example for Rembrandt.

Creates an in-memory database, adds a small EN-ES vocabulary set,
and runs a few exercises showing both flashcard and multiple-choice
output.
"""

from rembrandt import Database, ExerciseType, Session


def main() -> None:
    db = Database(":memory:")
    db.add_words([
        ("en", "es", "cat", "gato"),
        ("en", "es", "dog", "perro"),
        ("en", "es", "house", "casa"),
        ("en", "es", "book", "libro"),
        ("en", "es", "water", "agua"),
        ("en", "es", "sun", "sol"),
    ])

    session = Session(
        db=db,
        user_id="demo",
        language_from="en",
        language_to="es",
    )

    for i in range(4):
        exercise = session.next_exercise()
        if exercise is None:
            break

        print(f"--- Exercise {i + 1} ---")
        print(f"Translate: {exercise.word.word_from}")
        print(f"Type: {exercise.exercise_type.value}")

        if exercise.exercise_type == ExerciseType.MULTIPLE_CHOICE:
            for idx, opt in enumerate(exercise.options, 1):
                print(f"  {idx}. {opt}")

        # Auto-answer with the correct translation
        answer = exercise.word.word_to
        result = session.answer(answer)
        status = "Correct!" if result.correct else "Wrong"
        print(f"Answer: {answer} -> {status}")
        print()

    db.close()
    print("Done!")


if __name__ == "__main__":
    main()
