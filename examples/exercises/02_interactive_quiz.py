"""Interactive quiz — math formulas."""

import asyncio
from rembrandt import quick_session

FORMULAS = [
    {
        "front": "Area of a circle",
        "back": "\u03c0r\u00b2",
    },
    {
        "front": "Quadratic formula",
        "back": "(-b \u00b1 \u221a(b\u00b2-4ac)) / 2a",
    },
    {
        "front": "Pythagorean theorem",
        "back": "a\u00b2 + b\u00b2 = c\u00b2",
    },
    {
        "front": "Derivative of sin(x)",
        "back": "cos(x)",
    },
    {
        "front": "Integral of 1/x",
        "back": "ln|x| + C",
    },
]


async def main():
    session = await quick_session(
        FORMULAS, db_path="math_quiz.db",
    )

    while True:
        ex = await session.next_exercise()
        if ex is None:
            print("No more concepts!")
            break

        print(f"\n[{ex.exercise_type.value}]")
        print(f"  {ex.concept.front}")

        if ex.options:
            for i, opt in enumerate(ex.options, 1):
                print(f"  {i}. {opt}")

        answer = input("  Your answer: ").strip()
        if answer.lower() == "q":
            break
        result = await session.answer(answer)

        if result.correct:
            print("  Correct!")
        else:
            print(
                f"  Wrong \u2014 expected: "
                f"{result.expected}"
            )

    stats = session.summary()
    print(
        f"\nDone: {stats.correct}/{stats.total}"
    )
    await session.db.close()


if __name__ == "__main__":
    asyncio.run(main())
