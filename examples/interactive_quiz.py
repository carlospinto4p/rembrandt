"""Interactive vocabulary quiz.

Runs a CLI loop where you type translations for English words.
Type 'q' or press Ctrl+C to quit. A score summary is printed
at the end.
"""

from rembrandt import Database, ExerciseType, Session


WORDS = [
    ("en", "es", "cat", "gato"),
    ("en", "es", "dog", "perro"),
    ("en", "es", "house", "casa"),
    ("en", "es", "book", "libro"),
    ("en", "es", "water", "agua"),
    ("en", "es", "sun", "sol"),
    ("en", "es", "moon", "luna"),
    ("en", "es", "tree", "arbol"),
    ("en", "es", "fire", "fuego"),
    ("en", "es", "sky", "cielo"),
]


def main() -> None:
    db = Database(":memory:")
    db.add_words(WORDS)

    session = Session(
        db=db,
        user_id="player",
        language_from="en",
        language_to="es",
    )

    correct = 0
    total = 0

    print("=== Rembrandt Vocabulary Quiz ===")
    print("Type the Spanish translation (or 'q' to quit).\n")

    try:
        while True:
            exercise = session.next_exercise()
            if exercise is None:
                print("No more words available.")
                break

            prompt = f"Translate '{exercise.word.word_from}'"
            if exercise.exercise_type == (
                ExerciseType.MULTIPLE_CHOICE
            ):
                prompt += " (choose one)"
                for idx, opt in enumerate(
                    exercise.options, 1
                ):
                    print(f"  {idx}. {opt}")

            answer = input(f"{prompt}: ").strip()
            if answer.lower() == "q":
                break

            total += 1
            result = session.answer(answer)

            if result.correct:
                correct += 1
                print("  Correct!\n")
            else:
                print(
                    f"  Wrong — expected '{result.expected}'\n"
                )

    except (KeyboardInterrupt, EOFError):
        print()

    print("=== Results ===")
    if total:
        pct = correct / total * 100
        print(f"Score: {correct}/{total} ({pct:.0f}%)")
    else:
        print("No answers submitted.")

    db.close()


if __name__ == "__main__":
    main()
