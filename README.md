
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

    # Register a user and start a session
    user = db.register_user("user1", "pass")
    session = Session(db, user_id=user.id, language_from="en",
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

    # Typos are accepted with a warning
    if result.near_miss:
        print(f"Close! The exact answer was: {result.expected}")
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

user = db.register_user("user1", "pass")
session = Session(db, user_id=user.id, language_from="en",
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
    user = db.register_user("user1", "pass")

    # Only new (unreviewed) words
    s = Session(db, user.id, "en", "es",
                mode=SessionMode.LEARN_NEW)

    # Only words due for review
    s = Session(db, user.id, "en", "es",
                mode=SessionMode.REVIEW_DUE)

    # Due first, then new (default)
    s = Session(db, user.id, "en", "es",
                mode=SessionMode.MIXED)
```

You can also restrict a session to a lesson's words:

```python
lesson = db.get_lessons("en", "es", cefr="A1")[0]
s = Session(db, user.id, "en", "es",
            word_ids=lesson.word_ids)
```

## Learning Steps

By default, new cards go through short-interval learning steps before
entering the SM-2 review queue, and forgotten review cards go through
relearning steps before returning. This follows the Anki-style approach
for better retention:

```python
from rembrandt import ReviewConfig, Session

# Default: learning_steps=[1, 10], relearning_steps=[10]
session = Session(db, user.id, "en", "es")

# Custom configuration
config = ReviewConfig(
    learning_steps=[1, 5, 15],     # minutes
    graduating_interval=2,          # days after graduation
    relearning_steps=[5, 20],       # minutes
    lapse_new_interval_factor=0.7,  # 70% of old interval
    lapse_min_interval=1,           # minimum 1 day
    leech_threshold=8,              # suspend after 8 lapses (0=off)
    max_new_cards=20,               # new cards per session (0=off)
    max_review_cards=100,           # review cards per session (0=off)
)
session = Session(db, user.id, "en", "es",
                  review_config=config)
```

Cards progress through states: `NEW` -> `LEARNING` -> `REVIEW`.
When a review card is forgotten it enters `RELEARNING` before returning
to `REVIEW` with a reduced interval. Cards that lapse too many times
(default 8) are flagged as leeches and moved to `SUSPENDED`, where they
are excluded from review until manually unsuspended.

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

lp = lesson_progress(db, user.id, lesson)
print(f"Studied: {lp.words_studied}/{lp.words_total}"
      f" ({lp.completion_pct}%)")
print(f"Mastered: {lp.words_mastered}/{lp.words_total}"
      f" ({lp.mastery_pct}%)")
```

A word is "studied" once it has any review history, and "mastered"
when it is in `REVIEW` state with 3+ consecutive correct recalls.

## Weak Word Detection

Identify words the user consistently gets wrong and prioritize them in
review sessions:

```python
# Find weak words (>= 50% error rate, >= 3 attempts)
weak = db.weak_words(user.id, "en", "es")
for ww in weak:
    print(f"{ww.word.word_from}: {ww.errors}/{ww.attempts}"
          f" ({ww.error_rate:.0%} error rate)")

# Prioritize weak words in a session
from rembrandt.spaced_repetition import select_words

words = select_words(
    db, user.id, "en", "es",
    prioritize_weak=True,
)
```

## Historical Stats

Every call to `session.answer()` automatically logs the result. Query
the history for trends and daily summaries:

```python
# Recent answer history
history = db.get_answer_history(user.id, limit=50)
for h in history:
    status = "correct" if h.correct else "wrong"
    print(f"Word {h.word_id}: {status} (q={h.quality})")

# Daily statistics (last 30 days)
for day in db.daily_stats(user.id, days=30):
    print(f"{day.date}: {day.correct}/{day.answers}"
          f" ({day.accuracy_pct}%)")
```

## Progress Export/Import

Export a user's spaced-repetition progress as JSON-serializable dicts,
and import them into another database:

```python
# Export
records = db.export_progress(user.id)

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

## PostgreSQL Backend

For production use, Rembrandt supports PostgreSQL via the
`PostgresDatabase` class, which has the same API as the SQLite
`Database`:

```bash
# Start PostgreSQL with Docker Compose
docker compose up -d
```

```python
from rembrandt import PostgresDatabase, Word
from rembrandt.session import Session

dsn = "postgresql://rembrandt:rembrandt@localhost/rembrandt"

with PostgresDatabase(dsn) as db:
    db.add_words([
        Word(language_from="en", language_to="es",
             word_from="cat", word_to="gato"),
    ])

    user = db.register_user("user1", "pass")
    session = Session(db, user_id=user.id,
                      language_from="en", language_to="es")
    exercise = session.next_exercise()
```

All features (lessons, progress, answer history, weak words, etc.)
work identically with both backends. Tags are stored as native
`JSONB` and booleans as `BOOLEAN` in PostgreSQL.

## Documentation

The `docs/` folder explains the theory behind the library:

| Document | Topics |
|----------|--------|
| [Spaced Repetition](docs/spaced-repetition.md) | Forgetting curve, SM-2 algorithm, easiness factor, worked example |
| [Exercise Types](docs/exercise-types.md) | Active recall, flashcard vs. multiple choice, answer evaluation |

## Examples

The `examples/` folder contains runnable scripts organised into two
categories:

### Exercises

Core learning features — exercise types, spaced repetition, sessions,
and progress tracking.

| Script | Description |
|--------|-------------|
| `01_quickstart.py` | Minimal demo using `quick_session()` with an inline word list |
| `02_interactive_quiz.py` | CLI quiz loop with `SessionMode` and `session.summary()` |
| `03_exercise_types.py` | All exercise types: gender match, conjugation, cloze, etc. |
| `04_definition_quiz.py` | Interactive monolingual definition-based quiz |
| `05_spanish_translation_quiz.py` | Spanish-English translation quiz from pre-built JSON |
| `06_spanish_vocabulary.py` | Monolingual Spanish vocabulary quiz (definition mode) |
| `07_session_features.py` | Hints, skip, and session statistics |
| `08_spaced_repetition_demo.py` | SM-2 algorithm internals visualised |
| `09_review_config.py` | Customising `ReviewConfig` for Anki-style scheduling |
| `10_card_states.py` | `CardState` lifecycle: NEW → LEARNING → REVIEW → RELEARNING → SUSPENDED |
| `11_word_selection.py` | Advanced `select_words()`: modes, caps, weak priority, filtering |
| `12_lessons_and_progress.py` | Lesson loading, progress tracking, and lesson-scoped sessions |
| `13_answer_history.py` | Answer history, daily stats, weak word detection |
| `14_progress_export_import.py` | Export and import spaced-repetition progress between databases |
| `15_custom_templates.py` | Load custom cloze templates and adjectives from JSON |
| `16_tags_and_cefr.py` | Organising vocabulary by tags and CEFR levels |

### Infrastructure

Database backends, CRUD operations, and user authentication.

| Script | Description |
|--------|-------------|
| `01_crud_operations.py` | Word and lesson create/update/delete |
| `02_user_auth.py` | User registration, authentication, and session tokens |
| `03_postgres.py` | PostgreSQL backend with Docker Compose |

Run any example with:

```bash
uv run python examples/exercises/01_quickstart.py
```
