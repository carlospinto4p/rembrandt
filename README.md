
# Rembrandt

A library to do some mental exercises with the help of LLMs.

## Installation

```bash
pip install rembrandt
```

## Quick Start

```python
from rembrandt import Database, Session, Word

# Set up database and add vocabulary
with Database("vocab.db") as db:
    db.add_words([
        Word(language_from="en", language_to="es",
             word_from="cat", word_to="gato"),
        Word(language_from="en", language_to="es",
             word_from="dog", word_to="perro"),
        Word(language_from="en", language_to="es",
             word_from="house", word_to="casa"),
        Word(language_from="en", language_to="es",
             word_from="book", word_to="libro"),
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

### Session Statistics

Call `summary()` at any time to get session stats:

```python
stats = session.summary()
print(f"Score: {stats.correct}/{stats.total}"
      f" ({stats.accuracy_pct}%)")
print(f"Streak: {stats.streak}"
      f" (best: {stats.best_streak})")
```

### Hints

Request a hint before answering — reveals the first letter, word length,
and a masked pattern:

```python
exercise = session.next_exercise()
h = session.hint()
print(f"Hint: {h.pattern} ({h.word_length} letters)")
# e.g. "g___ (4 letters)"
```

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
from rembrandt import Database, Session, Word

db = Database("vocab.db")
db.add_words([
    Word(language_from="en", language_to="en",
         word_from="ephemeral",
         word_to="lasting for a very short time"),
    Word(language_from="en", language_to="en",
         word_from="ubiquitous",
         word_to="present or found everywhere"),
    Word(language_from="en", language_to="en",
         word_from="candid",
         word_to="truthful and straightforward"),
])

session = Session(db, user_id="user1", language_from="en",
                  language_to="en")
exercise = session.next_exercise()
```

When both languages are the same, Rembrandt automatically switches to
definition mode with exercise types suited for learning definitions:
multiple choice, reverse flashcard (definition shown, type the word),
and self-graded (recall and rate yourself 0-5).

## Session Modes

Control which words appear in a session using `SessionMode`:

```python
from rembrandt import Database, Session, SessionMode

with Database("vocab.db") as db:
    # Only new (unreviewed) words
    s = Session(db, "user1", "en", "es",
                mode=SessionMode.LEARN_NEW)

    # Only words due for review
    s = Session(db, "user1", "en", "es",
                mode=SessionMode.REVIEW_DUE)

    # Due first, then new (default)
    s = Session(db, "user1", "en", "es",
                mode=SessionMode.MIXED)
```

You can also restrict a session to a lesson's words:

```python
lesson = db.get_lessons("en", "es", cefr="A1")[0]
s = Session(db, "user1", "en", "es",
            word_ids=lesson.word_ids)
```

## Lessons

Rembrandt supports structured lessons — named sets of words grouped by
CEFR level or topic. Pre-built Spanish lessons are included:

```python
from rembrandt import Database, Lesson, load_lessons

with Database("spanish.db") as db:
    # Load vocabulary first (e.g. via quick_session or add_words)
    # Then load pre-built lessons
    lessons = load_lessons(
        "data/spanish_lessons.json",
        "data/spanish_top10000.json",
        db,
        language_from="en",
        language_to="es",
    )

    # Browse lessons by CEFR level
    a1 = db.get_lessons("en", "es", cefr="A1")
    for lesson in a1:
        print(f"{lesson.title}: {lesson.word_count} words")

    # Filter by topic
    food = db.get_lessons("en", "es", tag="food")
```

The `data/spanish_lessons.json` file contains 467 pre-built lessons:
400 frequency-ordered CEFR chunk lessons (~25 words each) and 67 topic
lessons.

### Lesson Progress

Track how far a user has progressed in a lesson:

```python
from rembrandt import lesson_progress

lp = lesson_progress(db, "user1", lesson)
print(f"Studied: {lp.words_studied}/{lp.words_total}"
      f" ({lp.completion_pct}%)")
print(f"Mastered: {lp.words_mastered}/{lp.words_total}"
      f" ({lp.mastery_pct}%)")
```

A word is "studied" once it has any review history, and "mastered"
after 3+ consecutive correct recalls (SM-2 repetitions >= 3).

## Weak Word Detection

Identify words the user consistently gets wrong and prioritize them in
review sessions:

```python
# Find weak words (>= 50% error rate, >= 3 attempts)
weak = db.weak_words("user1", "en", "es")
for ww in weak:
    print(f"{ww.word.word_from}: {ww.errors}/{ww.attempts}"
          f" ({ww.error_rate:.0%} error rate)")

# Prioritize weak words in a session
from rembrandt.spaced_repetition import select_words

words = select_words(
    db, "user1", "en", "es",
    prioritize_weak=True,
)
```

## Historical Stats

Every call to `session.answer()` automatically logs the result. Query
the history for trends and daily summaries:

```python
# Recent answer history
history = db.get_answer_history("user1", limit=50)
for h in history:
    status = "correct" if h.correct else "wrong"
    print(f"Word {h.word_id}: {status} (q={h.quality})")

# Daily statistics (last 30 days)
for day in db.daily_stats("user1", days=30):
    print(f"{day.date}: {day.correct}/{day.answers}"
          f" ({day.accuracy_pct}%)")
```

## Progress Export/Import

Export a user's spaced-repetition progress as JSON-serializable dicts,
and import them into another database:

```python
# Export
records = db.export_progress("user1")

# Save to file
import json
with open("progress.json", "w") as f:
    json.dump(records, f)

# Import into another database
with open("progress.json") as f:
    records = json.load(f)
count = db.import_progress(records)
print(f"Imported {count} records")
```

## Custom Exercise Config

Extend the built-in cloze templates and adjective bank from a single
JSON config file:

```python
from rembrandt import load_exercise_config

result = load_exercise_config("my_config.json")
print(f"Added {result['templates']} templates,"
      f" {result['adjectives']} adjectives")
```

The JSON file supports two optional keys:

```json
{
  "templates": {
    "verb": ["Deberías {word} más"],
    "noun_m": ["El {word} brilla"]
  },
  "adjectives": [
    ["oscuro", "oscura"],
    ["claro", "clara"]
  ]
}
```

Template keys: `verb`, `noun_m`, `noun_f`, `adjective`, `en_verb`,
`en_noun`, `en_adjective`. Each template must contain `{word}`.

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
| `01_quickstart.py` | Minimal demo using `quick_session()` with an inline word list |
| `02_interactive_quiz.py` | CLI quiz loop with `SessionMode` and `session.summary()` |
| `03_exercise_types.py` | All exercise types: gender match, conjugation, cloze, etc. |
| `04_spaced_repetition_demo.py` | SM-2 algorithm internals visualised |
| `05_definition_quiz.py` | Interactive monolingual definition-based quiz |
| `06_spanish_translation_quiz.py` | Spanish-English translation quiz from pre-built JSON |
| `07_spanish_vocabulary.py` | Monolingual Spanish vocabulary quiz (definition mode) |
| `08_user_auth.py` | User registration, authentication, and session tokens |
| `09_session_features.py` | Hints, skip, and session statistics |
| `10_crud_operations.py` | Word and lesson create/update/delete |
| `11_lessons_and_progress.py` | Lesson loading, progress tracking, and lesson-scoped sessions |
| `12_progress_export_import.py` | Export and import spaced-repetition progress between databases |
| `13_answer_history.py` | Answer history, daily stats, weak word detection |
| `14_custom_templates.py` | Load custom cloze templates and adjectives from JSON |

Run any example with:

```bash
uv run python examples/01_quickstart.py
```
