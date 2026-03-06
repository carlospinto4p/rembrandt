# rembrandt-telegram — Specification

A Telegram bot that uses the [rembrandt](https://github.com/carlospinto4p/rembrandt)
library to run Spanish vocabulary exercises via chat.

## Overview

Users interact with a Telegram bot to learn Spanish vocabulary through
definition-mode exercises (ES-ES: word + definition/synonyms). The bot
manages user identity automatically via Telegram accounts, runs exercise
sessions, tracks spaced-repetition progress, and lets users add their
own private words.

## Architecture

```
rembrandt-telegram/
    bot/
        __init__.py
        main.py                # Entry point, bot setup, polling
        config.py              # Environment variables, settings
        handlers/
            __init__.py
            start.py           # /start — auto-registration, welcome
            exercise.py        # /play, /stop, answer handling, /hint, /skip
            words.py           # /addword, /mywords, /deleteword
            stats.py           # /stats, /weak, /streak
        session_manager.py     # telegram_user_id -> rembrandt.Session mapping
        formatting.py          # Exercise -> Telegram message + keyboard
        user_mapping.py        # telegram_user_id -> rembrandt user_id
    docker-compose.yml         # PostgreSQL + bot services
    pyproject.toml
    CLAUDE.md
    README.md
```

### Separate package

This is a standalone Python package, NOT part of the rembrandt library.
Rembrandt is a dependency — it provides the exercise engine, spaced
repetition, and database layer. The bot adds Telegram-specific concerns:
message formatting, conversation state, inline keyboards, deployment.

### Dependencies

- `rembrandt` — core library (exercises, spaced repetition, DB)
- `python-telegram-bot` (v20+) — async Telegram bot framework
- `psycopg[binary]` — PostgreSQL driver (via rembrandt's postgres extra)

## User Identity

No registration flow. Telegram provides a unique `user.id` per chat.

On `/start`:
1. Check if a rembrandt `User` exists with
   `username = f"tg:{telegram_user_id}"`.
2. If not, call `db.register_user(username, password=<random>)` with
   `display_name` from the Telegram user's `first_name`.
3. Store the mapping `telegram_user_id -> rembrandt_user.id` in memory
   (dict) and rebuild on startup by querying users with `tg:` prefix.

No passwords, no tokens — Telegram handles authentication.

## Session Management

The rembrandt `Session` object is stateful (holds the current exercise
in memory). The bot must keep one `Session` per active Telegram user.

```python
# session_manager.py
class SessionManager:
    _sessions: dict[int, Session]  # telegram_user_id -> Session

    def get(self, tg_user_id: int) -> Session | None
    def start(self, tg_user_id: int, db, user_id, ...) -> Session
    def stop(self, tg_user_id: int) -> SessionStats | None
```

- Created on `/play`, destroyed on `/stop` or after inactivity timeout.
- Only one session per user at a time.
- If the bot restarts, sessions are lost (acceptable — progress is in
  the DB, only the current in-flight exercise is lost).

## Exercise Flow

### Starting a session

```
User: /play
Bot:  Let's practice! Here's your first word:
      [exercise message]
```

Creates a `Session(db, user_id, "es", "es", mode=SessionMode.MIXED)`.
Definition mode activates automatically because `language_from == language_to`.

### Exercise display

Definition mode generates three exercise types:

| Exercise type | Telegram rendering |
|---|---|
| **Multiple choice** | Message with definition + 4 inline keyboard buttons |
| **Reverse flashcard** | Show definition, user types the word |
| **Self-graded** | Show word + definition, inline keyboard: 0-5 quality buttons |

#### Multiple choice example
```
Which word matches this definition?

"Que dura poco tiempo"

[efimero] [perpetuo] [antiguo] [moderno]
```

#### Reverse flashcard example
```
What word means:

"Que dura poco tiempo"

Type your answer:
```

#### Self-graded example
```
Review this word:

efimero — Que dura poco tiempo

How well did you know it?
[0 ] [1 ] [2 ] [3 ] [4 ] [5 ]
```

### Answering

- **Inline keyboard tap** -> `session.answer(text=selected_option)`
  or `session.answer(quality=N)` for self-graded.
- **Text message** -> `session.answer(text=user_message)`.

After answering, show result and next exercise:
```
Correct! efimero = Que dura poco tiempo

Next word:
[next exercise]
```

Or on incorrect:
```
Incorrect. The answer was: efimero

Next word:
[next exercise]
```

### Hint and Skip

- `/hint` during an active exercise -> calls `session.hint()`, replies
  with the pattern (e.g. `"e______ (7 letters)"`).
- `/skip` -> calls `session.skip()`, shows next exercise.

### Ending a session

```
User: /stop
Bot:  Session complete!
      Total: 15 | Correct: 12 | Accuracy: 80.0%
      Best streak: 7
```

## Adding Words

Users can add their own private words via `/addword`. These are stored
with `owner_id = user.id` so only they see them.

### Conversational flow

```
User: /addword
Bot:  Send the word:
User: efimero
Bot:  Send the definition:
User: Que dura poco tiempo
Bot:  Added "efimero" — Que dura poco tiempo
```

Implementation:
```python
db.add_word(
    "es", "es",
    word_from="efimero",
    word_to="Que dura poco tiempo",
    owner_id=rembrandt_user_id,
)
```

### Listing and deleting

- `/mywords` — lists the user's private words (paginated if many).
- `/deleteword <word>` — deletes a word the user owns.

## Word Visibility

The rembrandt library supports `owner_id` on the `Word` model:

| `owner_id` | Visibility |
|---|---|
| `None` | Shared — visible to all users (admin-loaded base vocab) |
| `user.id` | Private — visible only to that user |

When fetching words for a session, call:
```python
db.get_words("es", "es", owner_id=rembrandt_user_id)
```
This returns shared words + the user's private words.

The `select_words()` function in `spaced_repetition.py` calls
`db.get_words()` internally. The `Session` and `select_words` will
need to pass `owner_id` through. This requires a small addition to
rembrandt — adding an `owner_id` parameter to `select_words()` and
`Session.__init__()` so it flows through to `get_words()`.

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message, auto-register if new |
| `/play` | Start an exercise session |
| `/stop` | End session and show summary |
| `/hint` | Get a hint for the current exercise |
| `/skip` | Skip the current exercise |
| `/addword` | Add a new word (conversational) |
| `/mywords` | List your private words |
| `/deleteword` | Delete one of your words |
| `/stats` | Show daily stats and accuracy |
| `/weak` | Show your weakest words |

## Configuration

Environment variables (loaded via `config.py`):

| Variable | Description | Example |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | `123456:ABC-DEF...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost/rembrandt` |
| `BASE_VOCAB_PATH` | Path to shared vocabulary JSON (optional) | `data/spanish_10000.json` |

## Database

Use `PostgresDatabase` from rembrandt for production persistence.
On first run, if `BASE_VOCAB_PATH` is set and the words table is empty,
load the shared vocabulary (with `owner_id=None`).

## Deployment

`docker-compose.yml` with two services:

```yaml
services:
  db:
    image: postgres:17
    environment:
      POSTGRES_USER: rembrandt
      POSTGRES_PASSWORD: rembrandt
      POSTGRES_DB: rembrandt
    volumes:
      - pgdata:/var/lib/postgresql/data

  bot:
    build: .
    depends_on:
      - db
    environment:
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      DATABASE_URL: postgresql://rembrandt:rembrandt@db/rembrandt
      BASE_VOCAB_PATH: /app/data/spanish_monolingual_10000.json
    volumes:
      - ./data:/app/data

volumes:
  pgdata:
```

## Implementation Order

1. **Project scaffolding** — `pyproject.toml`, `CLAUDE.md`, basic
   structure.
2. **User mapping** — `/start` handler, auto-registration, telegram-to-
   rembrandt user mapping.
3. **Exercise flow** — `/play`, `/stop`, answer handling, inline
   keyboards for multiple choice and self-graded.
4. **Formatting** — `formatting.py` to render each exercise type as
   Telegram messages with appropriate keyboards.
5. **Hints and skip** — `/hint`, `/skip` handlers.
6. **Word management** — `/addword` conversational handler, `/mywords`,
   `/deleteword`.
7. **Stats** — `/stats`, `/weak` handlers.
8. **Deployment** — `Dockerfile`, `docker-compose.yml`, base vocab
   loading on first run.

## Rembrandt Changes Needed

To fully support the bot, rembrandt needs one more change:

- **Pass `owner_id` through `select_words()` and `Session`**: Currently
  `select_words()` calls `db.get_words(lang_from, lang_to)` without
  `owner_id`. Add an `owner_id` parameter to `select_words()` and
  `Session.__init__()` so word selection respects ownership. Without
  this, all users see all words (shared + everyone's private words).

This is a small change: add `owner_id: int | None = None` to
`select_words()` and pass it to `db.get_words()`, then thread it
through `Session.__init__()` to `next_exercise()`.
