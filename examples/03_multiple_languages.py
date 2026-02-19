"""Multiple-language demo.

Shows that a single database can hold several language pairs
(EN-ES and EN-FR) and that separate sessions keep them isolated.
"""

from rembrandt import Database, ExerciseType, Session


def run_exercise(session: Session, label: str) -> None:
    """Run one exercise and print the result."""
    exercise = session.next_exercise()
    if exercise is None:
        print(f"[{label}] No words available.\n")
        return

    print(f"[{label}] Translate: {exercise.word.word_from}")
    print(f"  Type: {exercise.exercise_type.value}")

    if exercise.exercise_type == ExerciseType.MULTIPLE_CHOICE:
        for idx, opt in enumerate(exercise.options, 1):
            print(f"  {idx}. {opt}")

    answer = exercise.word.word_to
    result = session.answer(answer)
    status = "Correct!" if result.correct else "Wrong"
    print(f"  Answer: {answer} -> {status}\n")


def main() -> None:
    db = Database(":memory:")

    # English -> Spanish vocabulary
    db.add_words([
        ("en", "es", "cat", "gato"),
        ("en", "es", "dog", "perro"),
        ("en", "es", "house", "casa"),
        ("en", "es", "water", "agua"),
    ])

    # English -> French vocabulary
    db.add_words([
        ("en", "fr", "cat", "chat"),
        ("en", "fr", "dog", "chien"),
        ("en", "fr", "house", "maison"),
        ("en", "fr", "water", "eau"),
    ])

    es_session = Session(
        db=db,
        user_id="demo",
        language_from="en",
        language_to="es",
    )
    fr_session = Session(
        db=db,
        user_id="demo",
        language_from="en",
        language_to="fr",
    )

    print("=== Multiple Languages Demo ===\n")

    for _ in range(2):
        run_exercise(es_session, "EN->ES")
        run_exercise(fr_session, "EN->FR")

    db.close()
    print("Done!")


if __name__ == "__main__":
    main()
