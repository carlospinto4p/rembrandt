"""PostgreSQL database backend example.

Demonstrates using `PostgresDatabase` instead of the default
SQLite `Database`. Requires a running PostgreSQL instance
(see `docker-compose.yml` in the project root).

Usage::

    docker compose up -d
    uv run python examples/infrastructure/03_postgres.py
"""

import asyncio
from rembrandt import Concept, PostgresDatabase, Session

_DSN = (
    "postgresql://rembrandt:rembrandt"
    "@localhost/rembrandt"
)


async def main() -> None:
    db = await PostgresDatabase.connect(_DSN)

    user = await db.get_user("user1")
    if user is None:
        user = await db.register_user(
            "user1", "user1",
        )

    concepts = await db.add_concepts([
        Concept(
            front="What is HTTP?",
            back="HyperText Transfer Protocol",
            tags=["web"],
        ),
        Concept(
            front="What is DNS?",
            back="Domain Name System",
            tags=["networking"],
        ),
        Concept(
            front="What is TCP?",
            back="Transmission Control Protocol",
            tags=["networking"],
        ),
        Concept(
            front="What is an API?",
            back="Application Programming Interface",
            tags=["web"],
        ),
    ])
    print(
        f"Added {len(concepts)} concepts "
        f"to PostgreSQL"
    )

    session = Session(
        db, user_id=user.id,
    )

    for i in range(3):
        exercise = await session.next_exercise()
        if exercise is None:
            break

        print(f"\n--- Exercise {i + 1} ---")
        print(
            f"Type: {exercise.exercise_type.value}"
        )
        print(f"Q: {exercise.concept.front}")

        result = await session.answer(
            exercise.concept.back,
        )
        status = (
            "Correct!"
            if result.correct
            else "Wrong"
        )
        print(
            f"Answer: {result.expected} "
            f"-> {status}"
        )

    stats = session.summary()
    print(
        f"\nScore: {stats.correct}/{stats.total} "
        f"({stats.accuracy_pct}%)"
    )
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
