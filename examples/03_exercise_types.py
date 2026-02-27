"""Exercise types showcase.

Demonstrates the full range of exercise types available in
translation mode: flashcard, multiple choice, gender match,
conjugation, cloze, translation cloze, adjective agreement,
and sentence ordering.  Uses words with `gender` and
`conjugation_group` metadata to unlock all types.

Usage::

    uv run python examples/03_exercise_types.py
"""

from pathlib import Path

from rembrandt import Database, Session, Word
from rembrandt.models import ExerciseType

_DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "exercise_types.db"
)


def main() -> None:
    _DB_PATH.unlink(missing_ok=True)

    with Database(_DB_PATH) as db:
        db.add_words([
            # Nouns with gender (enables GENDER_MATCH)
            Word(
                language_from="en", language_to="es",
                word_from="cat", word_to="gato",
                gender="m", tags=["animals"],
            ),
            Word(
                language_from="en", language_to="es",
                word_from="house", word_to="casa",
                gender="f", tags=["home"],
            ),
            Word(
                language_from="en", language_to="es",
                word_from="book", word_to="libro",
                gender="m", tags=["education"],
            ),
            Word(
                language_from="en", language_to="es",
                word_from="table", word_to="mesa",
                gender="f", tags=["home"],
            ),
            # Verbs with conjugation_group
            # (enables CONJUGATION)
            Word(
                language_from="en", language_to="es",
                word_from="to speak", word_to="hablar",
                conjugation_group="ar",
            ),
            Word(
                language_from="en", language_to="es",
                word_from="to eat", word_to="comer",
                conjugation_group="er",
            ),
            Word(
                language_from="en", language_to="es",
                word_from="to live", word_to="vivir",
                conjugation_group="ir",
            ),
            # Plain word (only FLASHCARD, MC, CLOZE,
            # TRANSLATION_CLOZE)
            Word(
                language_from="en", language_to="es",
                word_from="water", word_to="agua",
            ),
        ])

        session = Session(
            db=db,
            user_id="demo",
            language_from="en",
            language_to="es",
        )

        print("=== Exercise Types Showcase ===\n")

        for i in range(10):
            exercise = session.next_exercise()
            if exercise is None:
                break

            etype = exercise.exercise_type
            w = exercise.word
            print(f"--- Exercise {i + 1}: {etype.value} ---")

            if etype == ExerciseType.FLASHCARD:
                print(f"  Translate: {w.word_from}")
                answer = w.word_to

            elif etype == ExerciseType.MULTIPLE_CHOICE:
                print(f"  Translate: {w.word_from}")
                for idx, opt in enumerate(
                    exercise.options, 1
                ):
                    print(f"    {idx}. {opt}")
                answer = w.word_to

            elif etype == ExerciseType.GENDER_MATCH:
                print(f"  Pick the article: {exercise.prompt}")
                print(f"    Options: {exercise.options}")
                answer = exercise.expected_answer

            elif etype == ExerciseType.CONJUGATION:
                print(f"  Conjugate: {exercise.prompt}")
                answer = exercise.expected_answer

            elif etype == ExerciseType.CLOZE:
                print(f"  Fill the blank: {exercise.prompt}")
                answer = exercise.expected_answer

            elif etype == ExerciseType.TRANSLATION_CLOZE:
                print(f"  Translate: {exercise.prompt}")
                answer = exercise.expected_answer

            elif etype == ExerciseType.ADJECTIVE_AGREEMENT:
                print(f"  Agree adjective: {exercise.prompt}")
                answer = exercise.expected_answer

            elif etype == ExerciseType.SENTENCE_ORDER:
                print(f"  Reorder: {exercise.prompt}")
                answer = exercise.expected_answer

            else:
                answer = w.word_to

            result = session.answer(answer)
            tag = "Correct!" if result.correct else "Wrong"
            print(f"  Answer: {answer} -> {tag}\n")

        stats = session.summary()
        print(
            f"Done — {stats.correct}/{stats.total} correct "
            f"({stats.accuracy_pct}%)"
        )


if __name__ == "__main__":
    main()
