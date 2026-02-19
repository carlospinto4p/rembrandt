
# Rembrandt

A library to do some mental exercises with the help of LLMs.

## Installation

```bash
pip install rembrandt
```

## Quick Start

```python
from rembrandt import Database, Session

# Set up database and add vocabulary
db = Database("vocab.db")
db.add_words([
    ("en", "es", "cat", "gato"),
    ("en", "es", "dog", "perro"),
    ("en", "es", "house", "casa"),
    ("en", "es", "book", "libro"),
])

# Start a session
session = Session(db, user_id="user1", language_from="en",
                  language_to="es")

# Get an exercise
exercise = session.next_exercise()
print(f"Translate: {exercise.word.word_from}")
print(f"Type: {exercise.exercise_type}")

if exercise.options:
    print(f"Options: {exercise.options}")

# Submit an answer
result = session.answer("gato")
print(f"Correct: {result.correct}")
print(f"Expected: {result.expected}")
```

The `Session` class handles spaced-repetition scheduling (SM-2 algorithm)
automatically — words you get wrong come back sooner, words you know well
are spaced further apart.

## Examples

The `examples/` folder contains runnable scripts that showcase the full API:

| Script | Description |
|--------|-------------|
| `quickstart.py` | Minimal self-contained demo (flashcard + multiple choice) |
| `interactive_quiz.py` | CLI quiz loop with score tracking |
| `spaced_repetition_demo.py` | SM-2 algorithm internals visualised |
| `multiple_languages.py` | Multiple language pairs in one database |

Run any example with:

```bash
uv run python examples/quickstart.py
```
