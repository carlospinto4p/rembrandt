
# Rembrandt

A general-purpose spaced-repetition library for any subject.

Study data science, math, history, vocabulary, or anything
else — Rembrandt handles scheduling, exercise generation,
and progress tracking.

## Installation

```bash
pip install rembrandt
```

## Quick Start

```python
import asyncio
from rembrandt import Database, Session, Concept

async def main():
    # Set up database and add concepts
    async with await Database.connect("study.db") as db:
        await db.register_user("default", "default")
        await db.add_concepts([
            Concept(
                front="What is a p-value?",
                back="Probability of observing data as extreme as the sample, given H0",
            ),
            Concept(
                front="What is overfitting?",
                back="Model learns noise, poor generalization",
            ),
            Concept(
                front="What is gradient descent?",
                back="Iterative optimization to minimize loss",
            ),
        ])

        # Start a session and study
        session = Session(db, user_id=1)
        ex = await session.next_exercise()
        if ex:
            print(f"Q: {ex.concept.front}")
            result = await session.answer(ex.concept.back)
            print(f"Correct: {result.correct}")

asyncio.run(main())
```

## Quick Session

The fastest way to start studying:

```python
import asyncio
from rembrandt import quick_session

CONCEPTS = [
    {"front": "Area of a circle", "back": "πr²"},
    {"front": "Pythagorean theorem", "back": "a² + b² = c²"},
    {"front": "Derivative of sin(x)", "back": "cos(x)"},
]

async def main():
    session = await quick_session(
        CONCEPTS, db_path="math.db",
    )
    ex = await session.next_exercise()
    if ex:
        print(f"Q: {ex.concept.front}")
        result = await session.answer(ex.concept.back)
        print(f"Correct: {result.correct}")
    await session.db.close()

asyncio.run(main())
```

Load from a JSON file:

```python
session = await quick_session("concepts.json")
```

Custom keys in JSON:

```python
session = await quick_session(
    "vocab.json",
    front_key="term",
    back_key="definition",
)
```

## Session Statistics

```python
stats = session.summary()
print(f"Score: {stats.correct}/{stats.total}")
print(f"Accuracy: {stats.accuracy_pct}%")
print(f"Streak: {stats.streak}")
print(f"Best streak: {stats.best_streak}")
```

## Hints

Progressive letter reveal:

```python
h = session.hint()    # "g___"
h = session.hint()    # "ga__"
h = session.hint()    # "gat_"
print(h.pattern, h.context)
```

## Session Modes

```python
from rembrandt import SessionMode

# Only new concepts
session = Session(db, user_id=1, mode=SessionMode.LEARN_NEW)

# Only due reviews
session = Session(db, user_id=1, mode=SessionMode.REVIEW_DUE)

# Mixed (default): due first, then new
session = Session(db, user_id=1, mode=SessionMode.MIXED)
```

## Session Persistence

Save and restore sessions (e.g. for a Telegram bot):

```python
# Save
await session.save(key="chat_123")

# Restore
session = await Session.restore(db, user_id=1, key="chat_123")
```

## Conversation State

Track multi-step bot interactions:

```python
from rembrandt import ConversationStage, ConversationState

state = ConversationState(
    user_id=1, key="chat_123",
    stage=ConversationStage.CHOOSING_TOPIC,
    data={"page": 1},
)
await db.save_conversation_state(state)
```

## Learning Steps (Anki-style)

Cards progress through states:
`NEW → LEARNING → REVIEW ↔ RELEARNING`

```python
from rembrandt import ReviewConfig

config = ReviewConfig(
    learning_steps=[1, 10],      # minutes
    graduating_interval=1,        # days
    relearning_steps=[10],        # minutes
    leech_threshold=8,            # suspends after 8 lapses
    max_new_cards=20,
    max_review_cards=100,
)
session = Session(db, user_id=1, review_config=config)
```

## FSRS Algorithm

Use FSRS-5 instead of SM-2:

```python
from rembrandt import FSRSConfig

session = Session(
    db, user_id=1,
    fsrs_config=FSRSConfig(desired_retention=0.9),
)
```

## Topics

Group concepts into topics:

```python
from rembrandt import Topic

topic = await db.add_topic(Topic(
    title="Linear Algebra Basics",
    tags=["math", "beginner"],
    concept_count=3,
    concept_ids=[1, 2, 3],
))

# Filter by tag
topics = await db.get_topics(tag="math")
```

## Topic Progress

```python
from rembrandt import topic_progress

progress = await topic_progress(db, user_id=1, topic=topic)
print(f"Studied: {progress.concepts_studied}/{progress.concepts_total}")
print(f"Mastered: {progress.concepts_mastered}")
print(f"Completion: {progress.completion_pct}%")
print(f"Mastery: {progress.mastery_pct}%")
```

## Filter by Tags

```python
# Concepts with a specific tag
concepts = await db.get_concepts(tag="math")

# Session filtered by tag
session = Session(db, user_id=1, tags=["math"])

# Session restricted to specific concept ids
session = Session(
    db, user_id=1, concept_ids=[1, 2, 3],
)
```

## Weak Concepts

```python
weak = await db.weak_concepts(
    user_id=1,
    tag="math",          # optional filter
    threshold=0.5,       # 50%+ error rate
    min_attempts=3,
)
for wc in weak:
    print(f"{wc.concept.front}: {wc.error_rate:.0%} errors")
```

## Historical Stats

```python
# Daily stats
stats = await db.daily_stats(user_id=1, days=30)
for day in stats:
    print(f"{day.date}: {day.correct}/{day.answers}")

# Retention rate
rate = await db.retention_rate(user_id=1, days=30)
print(f"Retention: {rate}%")

# Review forecast
forecast = await db.forecast(user_id=1, days=7)
for day in forecast:
    print(f"{day.date}: {day.due_count} due")
```

## CSV/TSV Import

```python
from rembrandt import import_concepts_csv

concepts = await import_concepts_csv(
    db, "flashcards.csv",
    front_col="question",
    back_col="answer",
)
```

## Progress Export/Import

```python
# Export
records = await db.export_progress(user_id=1)

# Import
count = await db.import_progress(records)
```

## Exercise Types

Rembrandt generates two exercise types:

| Type | Description |
|------|-------------|
| `MULTIPLE_CHOICE` | Shows front with 4 options |
| `SELF_GRADED` | User sees front, reveals back, self-rates 0-5 |

## Examples

See the `examples/` directory:

**Exercise examples** (`examples/exercises/`):
- `01_quickstart.py` — Data science concepts
- `02_interactive_quiz.py` — Math formulas
- `03_exercise_types.py` — All 4 types, geography
- `04_spanish_vocabulary.py` — Spanish definitions

**Infrastructure examples** (`examples/infrastructure/`):
- `01_crud_operations.py` — Concept and topic CRUD
- `02_user_auth.py` — User registration and sessions
- `03_seed_data_science.py` — Seed DB with 36 Data Science concepts
