"""Multiple-language demo.

Shows that a single database can hold several language pairs
(EN-ES and EN-FR) and that separate sessions keep them isolated.
"""

from pathlib import Path

from rembrandt import Database, Session, Word
from rembrandt.models import ExerciseType

_DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "multi_lang.db"
)


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
    fresh = not _DB_PATH.exists()
    db = Database(_DB_PATH)

    if fresh:
        # English -> Spanish vocabulary
        db.add_words([
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
                word_from="water", word_to="agua",
            ),
        ])

        # English -> French vocabulary
        db.add_words([
            Word(
                language_from="en", language_to="fr",
                word_from="cat", word_to="chat",
            ),
            Word(
                language_from="en", language_to="fr",
                word_from="dog", word_to="chien",
            ),
            Word(
                language_from="en", language_to="fr",
                word_from="house", word_to="maison",
            ),
            Word(
                language_from="en", language_to="fr",
                word_from="water", word_to="eau",
            ),
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
