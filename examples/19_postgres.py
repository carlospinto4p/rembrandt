"""PostgreSQL database backend example.

Demonstrates using `PostgresDatabase` instead of the default SQLite
`Database`. Requires a running PostgreSQL instance (see
`docker-compose.yml` in the project root).

Usage::

    docker compose up -d
    uv run python examples/19_postgres.py
"""

from rembrandt import PostgresDatabase, Word
from rembrandt.session import Session

_DSN = "postgresql://rembrandt:rembrandt@localhost/rembrandt"


def main() -> None:
    with PostgresDatabase(_DSN) as db:
        user = db.get_user("user1")
        if user is None:
            user = db.register_user("user1", "user1")

        words = db.add_words([
            Word(
                language_from="en", language_to="es",
                word_from="cat", word_to="gato",
                gender="m", tags=["animals"],
            ),
            Word(
                language_from="en", language_to="es",
                word_from="dog", word_to="perro",
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
        ])
        print(f"Added {len(words)} words to PostgreSQL")

        session = Session(
            db,
            user_id=user.id,
            language_from="en",
            language_to="es",
        )

        for i in range(3):
            exercise = session.next_exercise()
            if exercise is None:
                break

            print(f"\n--- Exercise {i + 1} ---")
            print(f"Type: {exercise.exercise_type.value}")
            print(f"Translate: {exercise.word.word_from}")

            result = session.answer(exercise.word.word_to)
            status = (
                "Correct!" if result.correct else "Wrong"
            )
            print(f"Answer: {result.expected} -> {status}")

        stats = session.summary()
        print(
            f"\nScore: {stats.correct}/{stats.total} "
            f"({stats.accuracy_pct}%)"
        )


if __name__ == "__main__":
    main()
