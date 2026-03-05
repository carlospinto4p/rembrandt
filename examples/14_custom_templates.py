"""Custom exercise configuration.

Demonstrates `load_exercise_config()`: writes a small JSON
config file at runtime, loads it to extend the cloze template
and adjective banks, then runs a short session showing
exercises that use the expanded pools.

Usage::

    uv run python examples/14_custom_templates.py
"""

import json
from pathlib import Path

from rembrandt import Database, Session, Word, load_exercise_config

_ROOT = Path(__file__).resolve().parent.parent / "data"
_DB_PATH = _ROOT / "custom_config_demo.db"
_CONFIG_PATH = _ROOT / "custom_config_demo.json"


def main() -> None:
    _DB_PATH.unlink(missing_ok=True)
    _CONFIG_PATH.unlink(missing_ok=True)

    # --- Step 1: Write a temporary config file ---
    config = {
        "templates": {
            "noun_m": [
                "El {word} es impresionante.",
                "Necesito un {word} nuevo.",
            ],
            "verb": [
                "Deberías {word} más a menudo.",
            ],
        },
        "adjectives": [
            ["oscuro", "oscura"],
            ["claro", "clara"],
        ],
    }
    _CONFIG_PATH.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote config to {_CONFIG_PATH.name}")

    # --- Step 2: Load the config ---
    result = load_exercise_config(_CONFIG_PATH)
    print(
        f"Loaded: {result['templates']} templates, "
        f"{result['adjectives']} adjectives\n"
    )

    # --- Step 3: Run a session using the expanded pools ---
    with Database(_DB_PATH) as db:
        user = db.register_user("demo", "demo")

        db.add_words([
            Word(
                language_from="en", language_to="es",
                word_from="cat", word_to="gato",
                gender="m",
            ),
            Word(
                language_from="en", language_to="es",
                word_from="house", word_to="casa",
                gender="f",
            ),
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
        ])

        session = Session(
            db=db,
            user_id=user.id,
            language_from="en",
            language_to="es",
        )

        print("=== Exercises with Custom Config ===\n")
        for i in range(6):
            ex = session.next_exercise()
            if ex is None:
                break
            etype = ex.exercise_type.value
            prompt = ex.prompt or ex.word.word_from
            print(f"  {i + 1}. [{etype}] {prompt}")
            session.answer(ex.expected_answer or ex.word.word_to)

        stats = session.summary()
        print(
            f"\nDone: {stats.correct}/{stats.total} correct "
            f"({stats.accuracy_pct}%)"
        )

    # Clean up
    _DB_PATH.unlink(missing_ok=True)
    _CONFIG_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
