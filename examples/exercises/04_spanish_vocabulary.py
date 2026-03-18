"""Spanish vocabulary — learn words with definitions."""

import asyncio
from rembrandt import quick_session

SPANISH = [
    {
        "front": "efímero",
        "back": "Que dura poco tiempo",
        "context": "Las flores son efímeras.",
        "tags": ["español", "vocabulario"],
    },
    {
        "front": "ubicuo",
        "back": "Que está presente en todas partes",
        "tags": ["español", "vocabulario"],
    },
    {
        "front": "pragmático",
        "back": (
            "Que se orienta a la práctica "
            "y la utilidad"
        ),
        "tags": ["español", "vocabulario"],
    },
    {
        "front": "resiliencia",
        "back": (
            "Capacidad de adaptarse a "
            "situaciones adversas"
        ),
        "tags": ["español", "vocabulario"],
    },
]


async def main():
    session = await quick_session(
        SPANISH, db_path="spanish.db",
    )

    for _ in range(4):
        ex = await session.next_exercise()
        if ex is None:
            break
        print(f"\n{ex.exercise_type.value}")
        print(f"  Palabra: {ex.concept.front}")
        if ex.options:
            for i, opt in enumerate(ex.options, 1):
                print(f"  {i}. {opt}")
        print(
            f"  Definición: {ex.concept.back}"
        )
        result = await session.answer(
            ex.concept.back,
        )
        status = "✓" if result.correct else "✗"
        print(f"  {status}")

    stats = session.summary()
    print(f"\n{stats.correct}/{stats.total}")
    await session.db.close()


if __name__ == "__main__":
    asyncio.run(main())
