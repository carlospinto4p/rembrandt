
# Backlog - Rembrandt

### 2026.03.02 — Anki-style scheduling improvements

- [x] Add learning steps for new cards (short-interval steps before entering SM-2 review queue)
- [x] Add lapse/relearning steps (forgotten mature cards re-enter learning steps instead of hard reset)
- [x] Add fuzz factor to intervals (small randomization to prevent review clustering)
- [x] Add leech detection (flag/suspend cards that repeatedly fail)
- [x] Add daily limits (separate caps for new cards and review cards per session)
- [x] Add sibling burying (avoid showing the same word in different exercise types in one session)

### 2026.03.03 — Refactoring review (v0.37.0)

- [x] Break `review()` into per-state handler functions (`_handle_new`, `_handle_learning`, `_handle_review`, `_handle_relearning`) — 200+ lines, cyclomatic complexity ~15
- [x] Extract `_schedule_review(minutes=..., days=...)` helper in `spaced_repetition.py` — 11 repeated `datetime.now() + timedelta(...)` blocks
- [x] Extract `_get_eligible_exercise_types()` from `generate_exercise()` in `exercises.py` — simplifies 95-line dispatch function
- [x] Define SM-2 constants (`QUALITY_PASS_THRESHOLD = 3`, `SECOND_CORRECT_INTERVAL = 6`) in `spaced_repetition.py` — replaces magic numbers
- [x] Wrap `db.py::_migrate()` ALTER TABLE statements in a transaction for schema consistency
- [x] Extract complex SQL queries (`weak_words`, `daily_stats`) to module-level constants in `db.py`

### 2026.03.04 — Refactoring review (v0.38.0)

- [x] Deduplicate SQL in `get_answer_history()` — two near-identical queries (with/without `since` filter) differ only in the WHERE clause; build query dynamically
- [x] Extract magic numbers in `exercises.py` — definition-mode thresholds `0.4`/`0.7` (line 498-500) and shuffle retry limit `20` (line 383) should be module-level constants
- [x] Extract mastery threshold constant — `repetitions >= 3` in `lessons.py:123` should use a named constant (shared or local)
- [x] Consolidate `session_db` and `db_with_words` test fixtures — both create an EN-ES database with 4-5 words; unify in `conftest.py` to reduce duplication
- [x] Rename `quick_session` key params for consistency — `word_key`/`definition_key` → `word_from_key`/`word_to_key` to match codebase terminology (breaking change — major bump)


### 2026.03.09 — Improvements pass

- [x] Add fuzzy answer matching (Levenshtein distance) to `_answers_match()` — accept near-misses with a warning instead of marking wrong
- [x] Add retention & forecast analytics — `retention_rate(user_id)` and `forecast(user_id, days)` for review load prediction
- [x] Add CSV/TSV word import — `import_words_csv(path)` for bulk-loading vocabulary from spreadsheets
- [ ] Add FSRS algorithm as alternative to SM-2 — modern, data-driven scheduler with better retention
- [ ] Add `LISTENING` exercise type — TTS URL generation via pluggable provider for audio comprehension drills
- [ ] Add Anki `.apkg` export — export decks in Anki's package format for interoperability
- [ ] Add `SessionMode.EXAM` — timed session with configurable limit and final score
- [x] Add richer hints — example sentence hints and "reveal next letter" progression to `Session.hint()`
- [ ] Add leech management — `unsuspend_word(user_id, word_id)` and `get_suspended(user_id)` methods
- [ ] Add French conjugation engine — extend `conjugation.py` with French verb morphology (-er/-ir/-re + irregulars)


### 2026.03.05 — Feature roadmap

- [x] Add examples for all library functionalities — review existing examples, improve them, and add missing ones for full coverage
- [x] Add PostgreSQL database support with Docker Compose for production-ready persistence
- [x] Add user IDs to the database — persist sessions, vocabulary, and progress per user
- [ ] Add Telegram bot support — design the interaction model and integrate with the library
