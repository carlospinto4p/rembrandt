"""Quickstart — study data science concepts."""

import asyncio
from rembrandt import quick_session

CONCEPTS = [
    {
        "front": "What is a p-value?",
        "back": (
            "Probability of observing data at least "
            "as extreme as the sample, assuming H0"
        ),
    },
    {
        "front": "What is overfitting?",
        "back": (
            "Model learns noise in training data "
            "and performs poorly on unseen data"
        ),
    },
    {
        "front": "What is gradient descent?",
        "back": (
            "Optimization algorithm that iteratively "
            "adjusts parameters to minimize loss"
        ),
    },
    {
        "front": "What is cross-validation?",
        "back": (
            "Evaluate model by partitioning data "
            "into training and test subsets"
        ),
    },
    {
        "front": "What is regularization?",
        "back": (
            "Penalty term added to loss function "
            "to prevent overfitting"
        ),
    },
]


async def main():
    session = await quick_session(
        CONCEPTS, db_path="quickstart.db",
    )

    for _ in range(3):
        ex = await session.next_exercise()
        if ex is None:
            break
        print(f"\n{ex.exercise_type.value}")
        print(f"  Q: {ex.concept.front}")
        if ex.options:
            for i, opt in enumerate(ex.options, 1):
                print(f"  {i}. {opt}")
        print(f"  A: {ex.concept.back}")

        result = await session.answer(
            ex.concept.back,
        )
        tag = "\u2713" if result.correct else "\u2717"
        print(f"  {tag}")

    stats = session.summary()
    print(
        f"\nScore: {stats.correct}/{stats.total} "
        f"({stats.accuracy_pct}%)"
    )
    await session.db.close()


if __name__ == "__main__":
    asyncio.run(main())
