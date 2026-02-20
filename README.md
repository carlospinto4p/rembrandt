
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

### Quick Session

For even faster setup, use `quick_session()` to handle database creation,
word loading, and session setup in a single call:

```python
from rembrandt import quick_session

session = quick_session(
    "vocab.json",              # JSON file with word/definition dicts
    language_from="es",
    language_to="en",
    limit=500,
)

exercise = session.next_exercise()
```

Words are loaded only on first run — subsequent calls reuse the existing
database and spaced-repetition progress. You can also pass an inline list
of dicts instead of a file path:

```python
session = quick_session(
    [{"word": "cat", "definition": "gato"}, ...],
    db_path="vocab.db",
    language_from="en",
    language_to="es",
)
```

## Definition Learning

Rembrandt also supports monolingual definition-based learning — learn
words through their definitions within the same language:

```python
from rembrandt import Database, Session

db = Database("vocab.db")
db.add_words([
    ("en", "en", "ephemeral", "lasting for a very short time"),
    ("en", "en", "ubiquitous", "present or found everywhere"),
    ("en", "en", "candid", "truthful and straightforward"),
])

session = Session(db, user_id="user1", language_from="en",
                  language_to="en")
exercise = session.next_exercise()
```

When both languages are the same, Rembrandt automatically switches to
definition mode with exercise types suited for learning definitions:
multiple choice, reverse flashcard (definition shown, type the word),
and self-graded (recall and rate yourself 0-5).

## Documentation

The `docs/` folder explains the theory behind the library:

| Document | Topics |
|----------|--------|
| [Spaced Repetition](docs/spaced-repetition.md) | Forgetting curve, SM-2 algorithm, easiness factor, worked example |
| [Exercise Types](docs/exercise-types.md) | Active recall, flashcard vs. multiple choice, answer evaluation |

## Examples

The `examples/` folder contains runnable scripts that showcase the full API:

| Script | Description |
|--------|-------------|
| `01_quickstart.py` | Minimal self-contained demo (flashcard + multiple choice) |
| `02_interactive_quiz.py` | CLI quiz loop with score tracking |
| `03_multiple_languages.py` | Multiple language pairs in one database |
| `04_spaced_repetition_demo.py` | SM-2 algorithm internals visualised |
| `05_definition_quiz.py` | Monolingual definition-based vocabulary learning |
| `06_load_spanish_vocab.py` | Load ranked Spanish vocabulary from pre-built JSON |

Run any example with:

```bash
uv run python examples/01_quickstart.py
```
