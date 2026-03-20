"""Demonstrate all exercise types."""

import asyncio
from rembrandt import Concept, Database
from rembrandt.exercises import (
    evaluate_answer,
    generate_multiple_choice,
    generate_self_graded,
)

CONCEPTS = [
    Concept(
        front="Capital of France", back="Paris",
        tags=["geography"],
    ),
    Concept(
        front="Capital of Japan", back="Tokyo",
        tags=["geography"],
    ),
    Concept(
        front="Capital of Brazil",
        back="Bras\u00edlia",
        tags=["geography"],
    ),
    Concept(
        front="Capital of Australia",
        back="Canberra",
        tags=["geography"],
    ),
]


async def main():
    db = await Database.connect(":memory:")
    stored = await db.add_concepts(CONCEPTS)

    print("=== Multiple Choice ===")
    ex = generate_multiple_choice(
        stored[1], stored,
    )
    print(f"  Q: {ex.concept.front}")
    for i, opt in enumerate(ex.options, 1):
        print(f"  {i}. {opt}")
    r = evaluate_answer(ex, "Tokyo")
    print(f"  Correct: {r.correct}")

    print("\n=== Self-Graded ===")
    ex = generate_self_graded(stored[3])
    print(f"  Q: {ex.concept.front}")
    print(f"  (reveal) A: {ex.concept.back}")
    r = evaluate_answer(ex, quality=5)
    print(f"  Correct: {r.correct}")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
