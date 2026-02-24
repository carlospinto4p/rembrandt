"""Interactive vocabulary quiz.

Runs a CLI loop where you type translations for English words.
Type 'q' or press Ctrl+C to quit. A score summary is printed
at the end. Progress is persisted between runs.
"""

from pathlib import Path

from rembrandt import Database, ExerciseType, Session, Word

_DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "interactive_quiz.db"
)

_WORDS = [
    Word(
        language_from="en", language_to="es",
        word_from="cat", word_to="gato",
    ),
    Word(
        language_from="en", language_to="es",
        word_from="dog", word_to="perro",
    ),
    Word(
        language_from="en", language_to="es",
        word_from="house", word_to="casa",
    ),
    Word(
        language_from="en", language_to="es",
        word_from="book", word_to="libro",
    ),
    Word(
        language_from="en", language_to="es",
        word_from="water", word_to="agua",
    ),
    Word(
        language_from="en", language_to="es",
        word_from="sun", word_to="sol",
    ),
    Word(
        language_from="en", language_to="es",
        word_from="moon", word_to="luna",
    ),
    Word(
        language_from="en", language_to="es",
        word_from="tree", word_to="arbol",
    ),
    Word(
        language_from="en", language_to="es",
        word_from="fire", word_to="fuego",
    ),
    Word(
        language_from="en", language_to="es",
        word_from="sky", word_to="cielo",
    ),
]


def main() -> None:
    fresh = not _DB_PATH.exists()
    db = Database(_DB_PATH)

    if fresh:
        db.add_words(_WORDS)

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
