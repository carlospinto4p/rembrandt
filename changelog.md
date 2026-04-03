
## Changelog - Rembrandt

### v6.3.4 - 3rd April 2026

- `.claude/`:
  - Updated hooks to v2: read stdin JSON instead of
    broken `$CLAUDE_TOOL_INPUT`/`$CLAUDE_FILE` env vars.
  - Added script files in `.claude/hooks/`.


### v6.3.3 - 2nd April 2026

- `.claude/settings.json`:
  - Added PreToolUse hook to block compound git commands.


### v6.3.2 - 2nd April 2026

- `CLAUDE.md`:
  - Added Shell Commands, Project Configuration, Versioning / Release,
    and Testing sections.


### v6.3.1 - 2nd April 2026

- Added `/backlog` skill in `.claude/skills/backlog/`.


### v6.3.0 - 31st March 2026

- Added `preferred` parameter to `generate_multiple_choice()`
  and `generate_exercise()` in `exercises.py`: distractors are
  drawn from the preferred pool first (e.g. same-topic concepts),
  falling back to `all_concepts` for remaining slots.
- Updated `Session.next_exercise()` in `session.py`: when a
  session has `concept_ids` set (topic-scoped), builds a
  topic-filtered distractor pool so MC options come from the same
  topic, producing harder exercises.
- Added preferred-distractor tests in `test_exercises.py`.


### v6.2.1 - 31st March 2026

- Fixed `evaluate_answer()` in `exercises.py`: `FLASHCARD`
  exercises now support quality-based evaluation when `quality`
  is provided, falling back to text-based matching when omitted.
  Previously, passing `quality` to a `FLASHCARD` exercise was
  silently ignored and text matching with empty string always
  returned incorrect.
- Added flashcard quality evaluation tests in
  `test_exercises.py`.


### v6.2.0 - 23rd March 2026

- Added schema migration system to `Database`:
  - `schema_version` table tracks the current schema version.
  - `_MIGRATIONS` list holds incremental SQL scripts.
  - `Database.connect()` applies pending migrations
    automatically, so existing client databases are upgraded
    on next connection.
- Moved `languages` and `concept_translations` tables from the
  base schema into migration 1, so pre-v6.1.0 databases get
  them via migration.


### v6.1.1 - 23rd March 2026

- Updated `.claude/rules/committing.md`: added shell command rules
  (no `cd` prefix, one simple command per Bash call).


### v6.1.0 - 23rd March 2026

- Added `Language` model in `models`: represents an available
  language by ISO 639-1 code and name.
- Added `ConceptTranslation` model in `models`: stores a
  translated version of a concept (front, back, context) in a
  specific language.
- Added `languages` and `concept_translations` tables to the
  database schema.
- Added `Database` methods for language management:
  - `add_language()`
  - `get_languages()`
  - `get_language()`
  - `delete_language()`
- Added `Database` methods for concept translations:
  - `add_translation()`
  - `get_translations()`
  - `get_translation()`
  - `update_translation()`
  - `delete_translation()`
- Exported `Language` and `ConceptTranslation` from the public
  API.


### v6.0.0 - 19th March 2026

- Removed `REVERSE_FLASHCARD` exercise type — exercises should not
  require typing answers without extra hints beyond a definition.
- Removed `generate_reverse_flashcard()` from `exercises`.
- Updated `evaluate_answer()`: removed reverse-flashcard branch.
- Updated `Session.hint()`: simplified answer resolution.


### v5.0.2 - 19th March 2026

- Removed `data/` directory with legacy Spanish vocabulary files:
  - `spanish_top10000.json`
  - `spanish_monolingual_10000.json`
  - `spanish_lessons.json`


### v5.0.1 - 19th March 2026

- Added `examples/infrastructure/03_seed_data_science.py`: seeds a
  SQLite database with 36 Data Science concepts across 5 topics
  (Statistics, ML, Deep Learning, Python Tools, Data Engineering).


### v5.0.0 - 19th March 2026

- Removed PostgreSQL backend — the library now uses SQLite only:
  - `db_postgres.py`
  - `PostgresDatabase` export
  - `psycopg[binary]` dependency
- Removed `docker-compose.yml`.
- Removed `examples/infrastructure/03_postgres.py`.


### v4.0.0 - 18th March 2026

- Transformed from a language-focused vocabulary tool into a
  general-purpose spaced-repetition library for any subject.
- Renamed `Word` to `Concept` with new fields:
  - `front` (was `word_from`)
  - `back` (was `word_to`)
  - `context` (new, optional explanation/notes)
- Removed `Word` fields:
  - `language_from`
  - `language_to`
  - `gender`
  - `conjugation_group`
  - `cefr`
- Renamed `Lesson` to `Topic` with new fields:
  - `concept_count` (was `word_count`)
  - `concept_ids` (was `word_ids`)
- Removed `Topic` fields:
  - `language_from`
  - `language_to`
  - `cefr`
- Renamed `LessonProgress` to `TopicProgress` with:
  - `concepts_total` (was `words_total`)
  - `concepts_studied` (was `words_studied`)
  - `concepts_mastered` (was `words_mastered`)
- Renamed `WeakWord` to `WeakConcept`.
- Renamed `Exercise.word` to `Exercise.concept`.
- Renamed `AnswerResult.word` to `AnswerResult.concept`.
- Renamed `UserProgress.word_id` to `concept_id`.
- Renamed `AnswerHistory.word_id` to `concept_id`.
- Renamed `ConversationStage.CHOOSING_LESSON` to
  `CHOOSING_TOPIC`.
- Renamed `Hint.example_sentence` to `context`.
- Simplified `ExerciseType` to 4 values:
  - `FLASHCARD`
  - `MULTIPLE_CHOICE`
  - `REVERSE_FLASHCARD`
  - `SELF_GRADED`
- Removed exercise types:
  - `GENDER_MATCH`
  - `CONJUGATION`
  - `CLOZE`
  - `TRANSLATION_CLOZE`
  - `ADJECTIVE_AGREEMENT`
  - `SENTENCE_ORDER`
- Removed `LearningMode` enum and `learning_mode()` function.
- Removed modules:
  - `conjugation.py`
  - `sentences.py`
- Renamed `lessons.py` to `topics.py`:
  - `load_lessons()` → `load_topics()`
  - `lesson_progress()` → `topic_progress()`
- Updated `SessionSnapshot`:
  - Removed `language_from`, `language_to`
  - Renamed `word_ids` → `concept_ids`
  - Renamed `buried_word_ids` → `buried_concept_ids`
  - Added `tags` field
- Updated `Session`:
  - Removed `language_from`, `language_to` parameters
  - Added optional `tags` filter
  - Added optional `concept_ids` filter
- Updated `quick_session()`:
  - Removed `language_from`, `language_to` parameters
  - Added `front_key`, `back_key` parameters
- Updated database schema:
  - `words` table → `concepts` (front, back, context)
  - `lessons` table → `topics`
  - `lesson_words` table → `topic_concepts`
  - All `word_id` columns → `concept_id`
- Renamed database methods:
  - `add_word()` → `add_concept()`
  - `add_words()` → `add_concepts()`
  - `get_words()` → `get_concepts()`
  - `update_word()` → `update_concept()`
  - `delete_word()` → `delete_concept()`
  - `weak_words()` → `weak_concepts()`
  - `add_lesson()` → `add_topic()`
  - `add_lessons()` → `add_topics()`
  - `get_lessons()` → `get_topics()`
  - `get_lesson()` → `get_topic()`
  - `update_lesson()` → `update_topic()`
  - `delete_lesson()` → `delete_topic()`
  - `import_words_csv()` → `import_concepts_csv()`
- Renamed `select_words()` to `select_concepts()`.
- Removed exports:
  - `load_cloze_templates`
  - `load_exercise_config`
- Added `ExerciseType` to public exports.
- Rewrote all examples for general-purpose use.
- Rewrote `README.md` for general-purpose use.


### v3.2.2 - 17th March 2026

- Updated definition mode exercise distribution to 95% multiple
  choice / 5% self-graded: self-graded is more word discovery
  than a real memory exercise.


### v3.2.1 - 17th March 2026

- Removed `REVERSE_FLASHCARD` from definition mode exercise
  selection: synonyms made typing the exact word too difficult.
  Definition mode now uses 50/50 multiple choice / self-graded.


### v3.2.0 - 10th March 2026

- Added `ConversationStage` enum:
  - `IDLE`
  - `CHOOSING_LESSON`
  - `EXERCISING`
  - `AWAITING_ANSWER`
  - `AWAITING_SELF_GRADE`
  - `VIEWING_STATS`
- Added `ConversationState` model for tracking multi-step bot
  interactions with arbitrary context data.
- Added database methods:
  - `save_conversation_state()`
  - `get_conversation_state()`
  - `delete_conversation_state()`
- Added `conversation_states` table to both SQLite and
  PostgreSQL schemas.


### v3.1.0 - 10th March 2026

- Added `SessionSnapshot` model for serializing session state.
- Added `Session.snapshot()`: create a serializable snapshot.
- Added `Session.save()`: persist session state to the database.
- Added `Session.restore()`: restore a session from a saved
  snapshot.
- Added database methods:
  - `save_session_snapshot()`
  - `get_session_snapshot()`
  - `delete_session_snapshot()`
- Added `session_snapshots` table to both SQLite and PostgreSQL
  schemas.


### v3.0.0 - 10th March 2026

- Converted `Database` to async using `aiosqlite`:
  - `Database(path)` replaced by `await Database.connect(path)` classmethod.
  - All database methods are now `async def` with `await`.
  - Context manager protocol uses `__aenter__`/`__aexit__`.
- Converted `PostgresDatabase` to async using `psycopg.AsyncConnection`:
  - `PostgresDatabase(dsn)` replaced by `await PostgresDatabase.connect(dsn)`.
  - All database methods are now `async def` with `await`.
- Converted `Session` methods to async:
  - `next_exercise()`, `answer()`, `_track_served()` are now `async def`.
  - `hint()`, `skip()`, `summary()` remain sync (no I/O).
- Converted `select_words()` to async in `spaced_repetition.py`.
- Converted `load_lessons()` and `lesson_progress()` to async in `lessons.py`.
- Converted `quick_session()` and `import_words_csv()` to async.
- Added `aiosqlite>=0.20` to dependencies.
- Added `pytest-asyncio>=0.24` to dev dependencies.
- Updated all unit tests to async.


### v2.6.3 - 9th March 2026

- Optimised `review()` and `fsrs_review()`: return the original
  `UserProgress` for suspended cards instead of deep-copying.
- Compiled regex patterns at module level in `exercises.py`:
  `_RE_BRACKETS` and `_RE_PARENS` replace per-call `re.sub()`.


### v2.6.2 - 9th March 2026

- Optimised `Session.next_exercise()`: cache the word list instead of
  querying the database on every call.
- Added database indexes on `words(language_from, language_to)`,
  `progress(user_id, state)`, and `answer_history(user_id, word_id)`
  in both SQLite and PostgreSQL.
- Optimised `select_words()`: merged allowed-IDs and excluded-IDs
  filtering into a single list pass.


### v2.6.1 - 9th March 2026

- Added git tags for all 33 previous version releases (v0.33.2–v2.6.0).
- Updated `.claude/rules/committing.md`: added tagging step to the
  post-change workflow.


### v2.6.0 - 9th March 2026

- Added `fsrs` module: FSRS-5 spaced-repetition algorithm as an
  alternative to SM-2, with power-law forgetting curve, 19-parameter
  model, and stability/difficulty tracking.
- Added `FSRSConfig` model: algorithm weights, desired retention,
  max interval, learning and relearning steps.
- Added `stability` and `difficulty` fields to `UserProgress`.
- Updated `Session`: new `fsrs_config` parameter — when provided,
  uses FSRS instead of SM-2 for scheduling.
- Updated `Database` and `PostgresDatabase`: migrations and
  persistence for `stability`/`difficulty` fields.
- Exported `FSRSConfig` and `fsrs_review` from the package.


### v2.5.0 - 9th March 2026

- Updated `Session.hint()`: progressive reveal — each call shows
  one more letter (e.g. `"g___"` → `"ga__"` → `"gat_"`).
- Added `Hint.reveal_count` field: number of letters currently
  revealed.
- Added `Hint.example_sentence` field: a cloze sentence using the
  word (with `___` blank) when the word has gender or conjugation
  group, empty string otherwise.


### v2.4.0 - 9th March 2026

- Added `import_words_csv()` in `db`: bulk-import words from CSV
  or TSV files with auto-detected delimiters, custom column names,
  and optional metadata columns (`gender`, `conjugation_group`,
  `tags`, `cefr`).
- Exported `import_words_csv` from the package.


### v2.3.0 - 9th March 2026

- Added `ReviewForecast` model: predicted review workload per day.
- Added `Database.retention_rate()` and
  `PostgresDatabase.retention_rate()`: overall correct-answer
  percentage over a configurable time window.
- Added `Database.forecast()` and `PostgresDatabase.forecast()`:
  predict upcoming review load per day, with past-due cards
  rolled into today's count.
- Exported `ReviewForecast` from the package.


### v2.2.0 - 9th March 2026

- Added fuzzy answer matching (Levenshtein distance) to
  `evaluate_answer()`: near-misses with small typos are accepted
  as correct with a `near_miss` flag.
- Added `AnswerResult.near_miss` field: ``True`` when the answer
  was accepted via fuzzy matching, so consumers can show a
  "close enough" warning.
- Added `_levenshtein()` and `_fuzzy_threshold()` helpers in
  `exercises`: distance 1 for short words (≤5 chars), distance 2
  for longer words.


### v2.1.1 - 9th March 2026

- Self-refinement pass on Claude settings:
  - `improvements.md`: rewrote "What to Look For" section (was
    copied from a trading project, now Rembrandt-specific).
  - `optimization.md`: removed async-specific bullets (no async
    code), fixed irrelevant grouping example.
  - `committing.md`: added `-m` quoting rule, clarified test step.
  - `shell.md`: commit message quoting now consistent with
    `committing.md`.
- Removed "Pydantic v2" line from `CLAUDE.md` (discoverable from
  `pyproject.toml`).


### v2.1.0 - 6th March 2026

- Added `owner_id` field to `Word` model: `None` for shared words,
  user id for private words.
- Added `owner_id` parameter to `Database.add_word()` and
  `PostgresDatabase.add_word()`.
- Added `owner_id` filter to `Database.get_words()` and
  `PostgresDatabase.get_words()`: when provided, returns shared
  words plus the specified user's private words.
- Added auto-migration for `owner_id` column on existing databases
  (both SQLite and PostgreSQL).
- Added `SPEC_rembrandt_telegram.md`: specification document for the
  Telegram bot integration project.


### v2.0.1 - 6th March 2026

- Reorganised `examples/` into two subfolders:
  - `exercises/`: 16 examples showcasing core learning features
  - `infrastructure/`: 3 examples for database backends and auth
- Renumbered examples for logical flow within each category.
- Updated `README.md` examples section with new folder structure.


### v2.0.0 - 6th March 2026

- Changed `user_id` from `str` to `int` across all models:
  - `UserProgress`
  - `AnswerHistory`
  - `LessonProgress`
- Changed `user_id` from `str` to `int` in all method signatures:
  - `Database`: `get_progress()`, `get_all_progress()`,
    `export_progress()`, `record_answer()`,
    `get_answer_history()`, `daily_stats()`, `weak_words()`
  - `PostgresDatabase`: same methods
  - `Session.__init__()`
  - `select_words()`
  - `lesson_progress()`
- Updated `quick_session()`: `user_id` is now `int | None`
  (default `None`); auto-registers a `"default"` user when
  omitted.
- Updated `db.py` schema: `progress.user_id` and
  `answer_history.user_id` are now `INTEGER` with foreign
  keys to `users(id)`.
- Added `_migrate_user_id_to_int()` in `Database`: migrates
  existing databases from TEXT to INTEGER user_id columns.
- Updated `db_postgres.py` schema: same foreign key changes.
- Updated all examples to register users and use `user.id`.
- Updated `README.md` code snippets.


### v1.1.0 - 5th March 2026

- Added `PostgresDatabase` class in `db_postgres`: full PostgreSQL
  backend with identical public API to `Database` (SQLite).
- Added `psycopg[binary]>=3.2` to dependencies.
- Added `docker-compose.yml`: PostgreSQL 17 service for local
  development and testing.
- Added `examples/19_postgres.py`: demonstrates `PostgresDatabase`
  usage with Docker Compose.
- Added `tests/unit/test_db_postgres.py`: PostgreSQL test suite
  (auto-skipped when PG is unavailable).
- Exported `PostgresDatabase` from the package.


### v1.0.4 - 5th March 2026

- Added `examples/18_tags_and_cefr.py`: demonstrates tag and CEFR
  level metadata on words, filtering, and tag-scoped sessions.


### v1.0.3 - 5th March 2026

- Added `examples/17_word_selection.py`: demonstrates advanced
  `select_words()` usage with session modes, `max_new`/`max_review`
  caps, `prioritize_weak`, `word_ids`, and `exclude_word_ids`.


### v1.0.2 - 5th March 2026

- Added `examples/16_card_states.py`: walks through the full
  `CardState` lifecycle (NEW → LEARNING → REVIEW → RELEARNING →
  SUSPENDED) using the low-level `review()` API.


### v1.0.1 - 5th March 2026

- Added `examples/15_review_config.py`: demonstrates `ReviewConfig`
  customisation (learning steps, graduating interval, relearning,
  leech threshold, daily limits, fuzz factor).
- Fixed missing `Usage::` block in `examples/04_spaced_repetition_demo.py`.


### v1.0.0 - 4th March 2026

- Renamed `quick_session()` parameters:
  - `word_key` → `word_from_key`
  - `definition_key` → `word_to_key`


### v0.38.4 - 4th March 2026

- Consolidated test fixtures: moved `definition_db` to
  `conftest.py` and replaced `session_db` with shared
  `db_with_words` fixture.


### v0.38.3 - 4th March 2026

- Extracted `MASTERY_REPETITIONS` constant in `lessons`,
  replacing hardcoded `repetitions >= 3`.


### v0.38.2 - 4th March 2026

- Extracted magic numbers in `exercises` to module-level
  constants:
  - `_DEF_MC_THRESHOLD`
  - `_DEF_FLASHCARD_THRESHOLD`
  - `_MAX_SHUFFLE_ATTEMPTS`


### v0.38.1 - 4th March 2026

- Refactored `get_answer_history()` in `db`: deduplicated
  SQL by building the query dynamically instead of two
  near-identical branches.


### v0.38.0 - 4th March 2026

- Added `exclude_word_ids` parameter to `select_words()`:
  filters out specified word ids before selection.
- Added sibling burying to `Session`: each word is only
  served once per session, preventing the same word from
  appearing in different exercise types.


### v0.37.6 - 4th March 2026

- Extracted `_DAILY_STATS_SQL` and `_WEAK_WORDS_SQL` to
  module-level constants in `db`.


### v0.37.5 - 3rd March 2026

- Updated `db._migrate()`: wrapped ALTER TABLE statements in
  a transaction for atomic schema migration.


### v0.37.4 - 3rd March 2026

- Defined SM-2 constants in `spaced_repetition`:
  - `QUALITY_PASS_THRESHOLD`
  - `_FIRST_CORRECT_INTERVAL`
  - `_SECOND_CORRECT_INTERVAL`
- Updated `exercises`: imports `QUALITY_PASS_THRESHOLD` for
  self-graded evaluation.


### v0.37.3 - 3rd March 2026

- Extracted `_eligible_translation_types()` from
  `generate_exercise()` in `exercises`: separates pool-building
  logic from dispatch.
- Fixed flaky test
  `test_generate_exercise_returns_valid_type_with_gender`:
  added missing `SENTENCE_ORDER` to expected types.


### v0.37.2 - 3rd March 2026

- Extracted `_schedule()` helper in `spaced_repetition`:
  replaces 12 repeated `datetime.now() + timedelta(...)`
  blocks with a single-source scheduling function.


### v0.37.1 - 3rd March 2026

- Refactored `review()` in `spaced_repetition`: extracted
  per-state handlers (`_handle_new`, `_handle_learning`,
  `_handle_review`, `_handle_relearning`) reducing cyclomatic
  complexity from ~15 to ~4 per function.


### v0.37.0 - 3rd March 2026

- Added `ReviewConfig.max_new_cards`: cap on new cards per
  session (`0` = unlimited).
- Added `ReviewConfig.max_review_cards`: cap on review cards
  per session (`0` = unlimited).
- Updated `select_words()`: new `max_new` and `max_review`
  parameters to cap new/due words. In-steps cards are never
  capped.
- Updated `Session`: tracks new/review served counts and
  passes remaining limits to `select_words()`.


### v0.36.0 - 3rd March 2026

- Added `CardState.SUSPENDED`: frozen state for leech cards,
  excluded from reviews.
- Added `UserProgress.lapse_count`: cumulative count of REVIEW
  failures (does not reset on success).
- Added `ReviewConfig.leech_threshold`: number of lapses before
  suspension (default `8`, set to `0` to disable).
- Updated `review()`: increments `lapse_count` on REVIEW fail
  and suspends card when threshold is reached. Returns suspended
  cards unchanged.
- Updated `select_words()`: skips suspended cards.
- Updated `db.py`: migration, persistence, and export/import
  for `lapse_count`.


### v0.35.0 - 3rd March 2026

- Added `ReviewConfig.max_fuzz_factor`: random jitter on day-based
  intervals to prevent review clustering (default ±5%).
- Added `_fuzz_interval()` helper in `spaced_repetition`.
- Updated `review()`: applies fuzz to all day-based interval
  assignments (graduating, SM-2, and lapse intervals).


### v0.34.1 - 3rd March 2026

- Fixed v0.34.0 changelog: removed incorrect folder grouping
  for core package files.
- Updated `.claude/rules/versioning.md`: folder grouping only
  applies to auxiliary directories, not `src/rembrandt/`.


### v0.34.0 - 3rd March 2026

- Added `CardState` enum (`NEW`, `LEARNING`, `REVIEW`,
  `RELEARNING`), `ReviewConfig` model, and `state` /
  `step_index` fields to `UserProgress`.
- Rewrote `review()` with Anki-style state machine for
  learning/relearning step progression.
- Updated `select_words()`: prioritizes `LEARNING`/`RELEARNING`
  cards before regular due/new words.
- Updated `Session` and `quick_session()`: accept optional
  `review_config` parameter.
- Updated `lesson_progress()`: mastery now requires
  `state == REVIEW` in addition to `repetitions >= 3`.
- Updated `db`: added `state` and `step_index` columns with
  migration for existing databases. Updated export/import.
- Exported `CardState` and `ReviewConfig` from package.
- Updated `README.md`: added Learning Steps section.


### v0.33.3 - 2nd March 2026

- Updated `.claude/rules/shell.md`:
  - Added `uv run` reminder for Python commands.
  - Added output redirection note (Unix-style `/dev/null`).


### v0.33.2 - 2nd March 2026

- Added `.claude/rules/shell.md`: guidelines for simple shell commands,
  avoiding `cd` prefixes and compound chains.


### v0.33.1 - 27th February 2026

- Updated `examples/03_exercise_types.py`: added `ADJECTIVE_AGREEMENT` and
  `SENTENCE_ORDER` branches.
- Added example scripts:
  - `examples/12_progress_export_import.py`: progress export/import roundtrip.
  - `examples/13_answer_history.py`: answer history, daily stats, weak words.
  - `examples/14_custom_templates.py`: custom exercise config from JSON.
- Updated `README.md`: added rows for examples 12-14.
- Fixed `db.get_answer_history()`: added `id DESC` tiebreaker to ordering
  so records within the same second are returned newest-first.


### v0.33.0 - 27th February 2026

- Added `load_exercise_config()` in `exercises`: unified config loader
  that reads a single JSON file to extend both cloze templates and
  adjective pairs.
- Added `extend_adjectives()` in `exercises`: programmatically extend
  the adjective bank with custom `[masculine, feminine]` pairs.
- Added `extend_cloze_templates()` in `sentences`: dict-based core
  logic extracted from `load_cloze_templates()`.
- Exported `load_exercise_config` from the package.


### v0.32.0 - 27th February 2026

- Added `SENTENCE_ORDER` to `ExerciseType`: scrambled-word exercise
  where the user reconstructs the correct sentence order.
- Added `generate_sentence_order()` in `exercises`: builds a complete
  sentence from the cloze template system, then shuffles the words.
- Updated `generate_exercise()`: adds `SENTENCE_ORDER` to the pool
  when the word has gender or conjugation_group.


### v0.31.0 - 27th February 2026

- Expanded built-in cloze template banks from 10 to 15 templates per
  category (verb, noun_m, noun_f, adjective, en_verb, en_noun,
  en_adjective).
- Added `load_cloze_templates()` in `sentences`: reads a JSON file and
  appends custom templates to the built-in banks for extensibility.
- Exported `load_cloze_templates` from the package.


### v0.30.0 - 27th February 2026

- Added `ADJECTIVE_AGREEMENT` to `ExerciseType`: gender agreement drill
  where the user types the correctly inflected adjective for a noun.
- Added `generate_adjective_agreement()` in `exercises`: picks from 15
  common adjectives and tests masculine/feminine agreement.
- Updated `generate_exercise()`: adds `ADJECTIVE_AGREEMENT` to the pool
  when the word has gender.


### v0.29.0 - 27th February 2026

- Added irregular verbs to `conjugation` engine:
  - `conocer`: c→zc change in presente/subjuntivo
  - `dormir`: o→ue/u stem change
  - `pedir`: e→i stem change
  - `sentir`: e→ie/i stem change
  - `jugar`: u→ue stem change


### v0.28.0 - 27th February 2026

- Added tenses to `conjugation` engine:
  - `futuro`
  - `condicional`
  - `subjuntivo_presente`
- Updated all 15 irregular verbs with new tense forms where they differ
  from regular conjugation (verbs regular in a tense fall through
  automatically).
- Added `_FULL_STEM_TENSES` constant: futuro and condicional use the
  full infinitive as stem.


### v0.27.1 - 27th February 2026

- Refactored `evaluate_answer()` in `exercises.py`: merged duplicated
  resolve/match/return tail into a single path that determines `expected`
  first.
- Refactored `authenticate_user()` in `db.py`: delegates to `get_user()`
  instead of duplicating the username lookup query.
- Moved shared test fixtures to `conftest.py`:
  - `sample_words`
  - `definition_words`
  - `db_with_words`
- Extracted `_in_clause()` helper in `db.py`: replaces repeated
  `",".join("?" for _ in ids)` pattern in `get_all_progress()` and
  `get_lessons()`.
- Standardised datetime parsing in `db.py`: replaced all `strptime()`
  calls with `fromisoformat()` for reading timestamps.


### v0.27.0 - 27th February 2026

- Added `WeakWord` model in `models`: tracks words with high error rates.
- Added `Database.weak_words()`: find words the user consistently gets wrong,
  with configurable `threshold`, `min_attempts`, and `limit`.
- Updated `select_words()`: added `prioritize_weak` parameter to sort due
  words so weak words come first.
- Exported `WeakWord` from the package.


### v0.26.0 - 27th February 2026

- Added `answer_history` table in `db`: stores per-answer logs with
  exercise type, correctness, and quality score.
- Added models in `models`:
  - `AnswerHistory`
  - `DailyStats`
- Added `Database` answer history methods:
  - `record_answer()`: log a single answer.
  - `get_answer_history()`: fetch recent answers with optional
    `limit` and `since` filters.
  - `daily_stats()`: aggregate answers into per-day statistics.
- Updated `Session.answer()`: automatically records each answer
  in the history log.
- Exported `AnswerHistory` and `DailyStats` from the package.


### v0.25.0 - 27th February 2026

- Added `Database.export_progress()`: export all progress rows for a user
  as JSON-serializable dicts.
- Added `Database.import_progress()`: upsert progress records from a list
  of dicts in a single transaction.


### v0.24.13 - 27th February 2026

- Fixed `06_spanish_translation_quiz.py`: changed translation cloze prompt
  from "Translate:" to "Translate the word:" to clarify that only the
  Spanish word is expected, not the full sentence.


### v0.24.12 - 27th February 2026

- Fixed `generate_cloze_exercise()`: prompt now includes the English
  translation as a hint (e.g. `"Voy a ___ mañana (to give)"`), so the
  user knows which word to fill in.


### v0.24.11 - 26th February 2026

- Fixed `generate_translation_cloze()`: uses `_non_spanish_word()` and
  `_spanish_word()` to detect the correct sides regardless of language
  orientation (es→en or en→es).
- Fixed `generate_exercise()`: only adds `CLOZE` and `TRANSLATION_CLOZE` to
  the exercise pool when the word has `gender` or `conjugation_group`,
  avoiding nonsensical cloze sentences for adverbs and particles.
- Added `_non_spanish_word()` helper in `exercises.py`.


### v0.24.10 - 26th February 2026

- Fixed `_acceptable_answers()`: now splits on commas in addition to
  semicolons, so ``"to say"`` matches ``"to say, to tell"``.
- Fixed `06_spanish_translation_quiz.py`: handles all exercise types
  (gender match, conjugation, cloze, translation cloze) with appropriate
  prompts instead of always showing "What does X mean?".
- Fixed unused `timedelta` import in `test_db.py`.


### v0.24.9 - 26th February 2026

- Fixed input validation in interactive examples:
  - `05_definition_quiz.py`: validate quality score (0-5) with retry loop.
  - `07_spanish_vocabulary.py`: same quality validation plus
    `KeyboardInterrupt`/`EOFError` handling.
  - `06_spanish_translation_quiz.py`: added `KeyboardInterrupt`/`EOFError`
    handling.


### v0.24.8 - 26th February 2026

- Rewrote `01_quickstart.py`: uses `quick_session()` with inline word list
  instead of manual `Database` + `Word` setup.
- Updated `02_interactive_quiz.py`: uses `SessionMode.LEARN_NEW` and
  `session.summary()` instead of manual score tracking.
- Replaced `03_multiple_languages.py` with `03_exercise_types.py`: showcases
  gender match, conjugation, cloze, and translation cloze exercise types
  using words with `gender` and `conjugation_group` metadata.
- Updated `05_definition_quiz.py`: now interactive (user input) instead of
  auto-answered.
- Added `11_lessons_and_progress.py`: demonstrates `load_lessons()`,
  `lesson_progress()`, `Session` with `word_ids`, and `SessionMode`.
- Updated `README.md` examples table.


### v0.24.7 - 26th February 2026

- Added example scripts:
  - `08_user_auth.py`: user registration, authentication, session tokens.
  - `09_session_features.py`: hints, skip, session statistics.
  - `10_crud_operations.py`: word and lesson create/update/delete.
- Fixed `_row_to_user()` date parsing in `db.py`: use `fromisoformat()`
  to handle SQLite's space-separated datetime default.
- Updated `README.md` examples table.


### v0.24.6 - 26th February 2026

- Replaced lambda wrappers with `functools.partial` in the
  `generate_exercise()` dispatch dict.


### v0.24.5 - 26th February 2026

- Added section comments to `exercises.py`: grouped 15 functions into
  Helpers, Exercise Generators, and Answer Evaluation.


### v0.24.4 - 26th February 2026

- Extracted `Session._update_stats()` from `Session.answer()`: separates
  counter/streak tracking from evaluation and progress logic.


### v0.24.3 - 26th February 2026

- Fixed `type: ignore[assignment]` in `lessons.py`: guard `w.id` against
  `None` instead of suppressing the type checker.


### v0.24.2 - 26th February 2026

- Replaced `assert` with explicit `ValueError` in:
  - `session.py`: guard `word_id` in `Session.answer()`.
  - `spaced_repetition.py`: guard `word.id` in `select_words()`.


### v0.24.1 - 26th February 2026

- Extracted `Database._insert_lesson_words()` helper in `db.py`: deduplicates
  the word-linking loop shared by `add_lessons()` and `update_lesson()`.


### v0.24.0 - 25th February 2026

- Added `Hint` model in `models`: first letter, word length, and masked
  pattern for the expected answer.
- Added `Session.hint()`: returns a partial hint for the current exercise
  without consuming it.
- Exported `Hint` from the package.


### v0.23.0 - 25th February 2026

- Added `Session.skip()`: move to the next exercise without affecting
  progress or session statistics.


### v0.22.0 - 25th February 2026

- Added `Database.update_lesson()`: update metadata and replace word
  links for an existing lesson.
- Added `Database.delete_lesson()`: delete a lesson and its word links.


### v0.21.0 - 25th February 2026

- Added `Database.update_word()`: update all fields of an existing word.
- Added `Database.delete_word()`: delete a word by id.


### v0.20.0 - 25th February 2026

- Added `SessionStats` model in `models`: tracks total, correct,
  incorrect, streak, best streak, and accuracy percentage.
- Added `Session.summary()`: returns a `SessionStats` snapshot for the
  current session.
- Updated `Session.answer()`: tracks correct/incorrect counts and
  streak automatically.
- Exported `SessionStats` from the package.


### v0.19.0 - 25th February 2026

- Added `UserSession` model in `models`: session token, user
  reference, creation and expiry timestamps.
- Added `user_sessions` table in `db`: stores login sessions with
  unique tokens and foreign key to `users`.
- Added `Database` session methods:
  - `create_session()`: generate a session token with configurable TTL.
  - `get_session()`: fetch a session by token (returns `None` if expired).
  - `delete_session()`: remove a single session.
  - `delete_user_sessions()`: remove all sessions for a user.
- Exported `UserSession` from the package.


### v0.18.0 - 25th February 2026

- Added `User` model in `models`: username, display name, hashed
  password (excluded from serialization), and creation timestamp.
- Added `users` table in `db`: stores registered users with unique
  usernames and salted SHA-256 password hashes.
- Added `Database` user methods:
  - `register_user()`: create a new user with hashed password.
  - `get_user()`: look up a user by username.
  - `authenticate_user()`: verify username and password.
- Exported `User` from the package.


### v0.17.11 - 25th February 2026

- Extracted `_select_template()` helper in `sentences.py` to share
  POS-heuristic logic between `generate_cloze()` and
  `generate_translation_cloze_sentence()`.


### v0.17.10 - 25th February 2026

- Simplified `Database.add_lesson()` in `db.py`: now delegates to
  `add_lessons()` instead of duplicating the insert logic.


### v0.17.9 - 25th February 2026

- Extracted `_row_to_word()` and `_row_to_progress()` helpers in
  `db.py` to deduplicate Row→Model mapping.


### v0.17.8 - 25th February 2026

- Extracted `_resolve_option_number()` helper in `exercises.py` to
  deduplicate option-number resolution in `evaluate_answer()`.


### v0.17.7 - 25th February 2026

- Refactored `generate_exercise()` in `exercises.py`: replaced if/elif
  dispatch chain with a dispatch dict for cleaner type→generator mapping.


### v0.17.6 - 25th February 2026

- Added `TRANSLATION_CLOZE` enum value test in `test_models.py`.


### v0.17.5 - 25th February 2026

- Added `TRANSLATION_CLOZE` section to `docs/exercise-types.md` and
  updated the translation mode pool description.


### v0.17.4 - 25th February 2026

- Fixed stale `PRODUCTION` / `generate_production()` references in
  `changelog.md` v0.17.0 entry to match current names.


### v0.17.3 - 25th February 2026

- Fixed stale "production" wording in `sentences.py` module docstring
  and comment header.


### v0.17.2 - 25th February 2026

- Renamed `generate_production_cloze()` to
  `generate_translation_cloze_sentence()` in `sentences.py` for
  consistency with the `TRANSLATION_CLOZE` exercise type.


### v0.17.1 - 25th February 2026

- Renamed `PRODUCTION` to `TRANSLATION_CLOZE` in `ExerciseType` and all
  related functions/tests for clarity.


### v0.17.0 - 25th February 2026

- Added `TRANSLATION_CLOZE` to `ExerciseType` enum.
- Added `generate_translation_cloze_sentence()` in `sentences.py`:
  English template banks for verbs, nouns, and adjectives.
- Added `generate_translation_cloze()` in `exercises.py`: creates
  EN->ES fill-in-the-blank exercises with English context and
  Spanish answer.
- Added `TRANSLATION_CLOZE` to the translation mode exercise pool
  in `generate_exercise()`.


### v0.16.6 - 24th February 2026

- Updated `.claude/rules/versioning.md`: added explicit BAD/GOOD
  examples for the 3+ items sub-bullet rule to prevent inlining
  items in parentheses or comma-separated lists.


### v0.16.5 - 24th February 2026

- Cleaned up `__init__.py`: removed re-exports of internal symbols.
  Users import these from their actual modules:
  - `AnswerResult`
  - `Exercise`
  - `ExerciseType`
  - `LearningMode`
  - `LessonProgress`
  - `learning_mode`
  - `conjugate`
  - `can_conjugate`
  - `generate_cloze`
- Updated all examples to import `ExerciseType` from
  `rembrandt.models` instead of the package root.


### v0.16.4 - 24th February 2026

- Fixed `.claude/settings.json`: rewrote hooks to use correct Claude
  Code format (`PostToolUse` with `Write|Edit` matcher for auto-lint,
  `PreToolUse` with `Bash` matcher for pre-commit tests).


### v0.16.3 - 24th February 2026

- Self-refinement pass on Claude settings:
  - `backlog.md`: fixed heading, trimmed workflow rule text.
  - `committing.md`: removed manual test step, referenced `preCommit`
    hook in steps 1 and 6.
  - `testing.md`: marked integration tests as aspirational, added
    note about updating `preCommit` hook when integration tests arrive.
- Added backlog item to remove `__init__.py` re-exports.


### v0.16.2 - 24th February 2026

- Updated `.claude/rules/backlog.md`: added workflow rule to implement
  backlog items sequentially (commit each one) rather than planning
  all upfront.


### v0.16.1 - 24th February 2026

- Updated `.claude/settings.json`: added `postEdit` hook (auto-lint
  and format Python files) and `preCommit` hook (run tests before
  every commit).


### v0.16.0 - 24th February 2026

- Added `sentences` module: template-based sentence generation with
  banks for verbs, masculine/feminine nouns, and adjectives (~10
  templates each).
- Added `ExerciseType.CLOZE`: fill-in-the-blank exercise type.
- Added `generate_cloze_exercise()` in `exercises`.
- Updated `generate_exercise()`: adds `CLOZE` unconditionally to the
  translation-mode pool (works for any word type).
- Updated `docs/exercise-types.md`: added cloze section.


### v0.15.0 - 24th February 2026

- Added `conjugation` module: rule-based Spanish conjugation engine
  with regular -ar/-er/-ir endings and 15 common irregular verbs
  across presente, pretérito, and imperfecto tenses.
- Added `ExerciseType.CONJUGATION`: verb conjugation drill exercise.
- Added `generate_conjugation()` in `exercises`.
- Updated `generate_exercise()`: adds `CONJUGATION` to the pool
  when the word has a conjugation group and is conjugable.
- Updated `docs/exercise-types.md`: added conjugation section.


### v0.14.0 - 24th February 2026

- Added `ExerciseType.GENDER_MATCH`: article matching exercise
  for Spanish nouns (`el`/`la`).
- Added `Exercise.prompt` and `Exercise.expected_answer` fields:
  support display text and explicit expected answers for new
  exercise types (defaults to `""`, backward-compatible).
- Added `generate_gender_match()` in `exercises`.
- Updated `generate_exercise()`: pool-based type selection in
  translation mode; adds `GENDER_MATCH` when word has gender.
- Updated `evaluate_answer()`: uses `expected_answer` when set,
  with numeric option resolution for all exercise types.
- Added `_strip_accents()` and accent-tolerant matching in
  `_answers_match()`: `"hablo"` matches `"habló"`.
- Added `_spanish_word()` helper in `exercises`.
- Updated `docs/exercise-types.md`: added gender match section,
  pool-based selection docs, accent tolerance.


### v0.13.0 - 24th February 2026

- Added `LessonProgress` model in `models`: per-lesson progress stats
  with completion and mastery percentages.
- Added `lesson_progress()` in `lessons`: computes studied, mastered,
  and percentage stats for a user within a lesson.
- Exported `LessonProgress` and `lesson_progress` from the package.


### v0.12.0 - 24th February 2026

- Added `SessionMode` enum in `models`: `LEARN_NEW`, `REVIEW_DUE`,
  `MIXED`.
- Updated `select_words()`: accepts `mode` and `word_ids` keyword
  arguments for session mode filtering and lesson-scoped selection.
- Updated `Session.__init__()`: accepts `mode` and `word_ids` keyword
  arguments, passed through to `select_words()`.
- Exported `SessionMode` from the package.


### v0.11.0 - 24th February 2026

- Added `Lesson` model in `models`: named set of words with title,
  description, CEFR level, tags, and word ids.
- Added `Database` lesson methods:
  - `add_lesson()`: insert a lesson and link words.
  - `add_lessons()`: bulk-insert lessons in a single transaction.
  - `get_lessons()`: filter by language pair, optional CEFR/tag.
  - `get_lesson()`: fetch a single lesson by id.
- Added `lessons` module with `load_lessons()`: resolves word ranks
  from a vocabulary file to database ids and persists lessons.
- Added `scripts/build_spanish_lessons.py`: generates pre-structured
  lessons from the Spanish vocabulary data.
- Added `data/spanish_lessons.json`: 467 pre-built lessons (400 CEFR
  chunk lessons of ~25 words each, 67 topic lessons).
- Exported `Lesson` and `load_lessons` from the package.


### v0.10.0 - 24th February 2026

- Added `Word.cefr` field: optional CEFR level (`"A1"` through `"C2"`),
  `None` when not assigned.
- Updated `Database`: `cefr` column in `words` table, persisted and
  read in `add_word()`, `add_words()`, and `get_words()`.
- Updated `quick_session()`: reads `cefr` from JSON entries.
- Updated `scripts/build_spanish_vocab.py`: added `_cefr_level()` helper
  that maps frequency rank to CEFR bands (A1: 1–500, A2: 501–1500,
  B1: 1501–3500, B2: 3501–6500, C1: 6501–8500, C2: 8501–10000).
- Updated `scripts/build_spanish_definitions.py`: carries `cefr` from
  the bilingual file into monolingual output.
- Rebuilt data files with CEFR levels.


### v0.9.0 - 24th February 2026

- Added `Word.tags` field: topic tags as a list of strings (default
  empty).
- Updated `Database`: `tags` column stored as JSON text, serialized
  on insert and deserialized on read.
- Added `scripts/topic_classifier.py`: keyword-based topic classifier
  with 12 topic categories (food, travel, body, emotions, family,
  home, nature, work, time, clothing, health, education).
- Updated `scripts/build_spanish_vocab.py`: classifies each gloss
  and includes `tags` in the output JSON.
- Updated `scripts/build_spanish_definitions.py`: carries `tags`
  from the bilingual file into monolingual output.
- Updated `quick_session()`: reads `tags` from JSON entries.


### v0.8.0 - 24th February 2026

- Added `Word.gender` and `Word.conjugation_group` fields: optional
  metadata for noun gender (`"m"`/`"f"`) and verb conjugation group
  (`"ar"`/`"er"`/`"ir"`).
- Refactored `Database.add_words()`: accepts `list[Word]` instead of
  `list[tuple]` for extensibility.
- Updated `Database.add_word()`: accepts optional `gender` and
  `conjugation_group` keyword arguments.
- Updated `quick_session()`: reads `gender` and `conjugation_group`
  from JSON entries when building `Word` objects.
- Updated `scripts/build_spanish_vocab.py`:
  - `_parse_dictionary()` extracts gender from `g:` lines.
  - Added `_conjugation_group()` helper for verb endings.
  - Output JSON includes `gender` and `conjugation_group`.
- Updated `scripts/build_spanish_definitions.py`: carries over `gender`
  and `conjugation_group` from the bilingual file.
- Updated all examples, tests, README, and docs for the new
  `add_words(list[Word])` signature.


### v0.7.1 - 23rd February 2026

- Added `scripts/build_spanish_definitions.py`: downloads Spanish
  Wiktionary extract from kaikki.org, matches against the ranked 10K
  word list, and outputs monolingual Spanish definitions.
- Added `data/spanish_monolingual_10000.json`: 10,000 Spanish words
  with Spanish-Spanish definitions and multiple senses (89.7% coverage).


### v0.7.0 - 23rd February 2026

- Refactored `Database.add_words()`: batched into a single transaction
  instead of committing per word.
- Added `Database.get_all_progress()`: fetches progress for multiple
  words in a single query.
- Updated `select_words()`: uses `get_all_progress()` to eliminate
  N+1 queries.
- Added `__enter__`/`__exit__` to `Database` for context-manager
  support (`with Database(...) as db:`).
- Moved `UserProgress` import to top-level in `session`.
- Replaced `type: ignore[arg-type]` on `word.id` with runtime
  assertions in `session` and `spaced_repetition`.
- Updated tests:
  - Added `tests/unit/conftest.py` with shared `db` fixture.
  - Converted helper functions to `@pytest.fixture` in
    `test_exercises.py`.
  - Added tests for `get_all_progress()` and context manager.


### v0.6.1 - 20th February 2026

- Renamed `examples/06_load_spanish_vocab.py` →
  `06_spanish_translation_quiz.py`: updated docstring to reflect
  Spanish-English translation focus.
- Added `examples/07_spanish_vocabulary.py`: monolingual Spanish
  vocabulary quiz using definition mode with `quick_session()`.
- Updated `README.md`: renamed example 06 and added example 07 to
  the examples table.


### v0.6.0 - 20th February 2026

- Added `quick_session()` factory function in `session`: creates a
  `Session` from a JSON file or inline word list, handling database
  creation and conditional word loading in one call.
- Updated `examples/06_load_spanish_vocab.py`: simplified using
  `quick_session()`.


### v0.5.0 - 20th February 2026

- Added flexible answer matching in `evaluate_answer()`:
  - `_acceptable_answers()`: strips parenthetical `(...)` and bracket
    `[...]` content, splits semicolon-separated senses.
  - `_answers_match()`: matches against any acceptable form, handles
    optional "to " verb prefix differences.
- Updated `evaluate_answer()`: multiple-choice answers can now be given
  as option numbers (`"1"`–`"N"`) instead of full text.
- Added 8 new tests for flexible matching and numeric option selection.


### v0.4.3 - 20th February 2026

- Updated all examples to use persistent SQLite files in `data/`
  instead of in-memory databases:
  - `01_quickstart.py` → `quickstart.db`
  - `02_interactive_quiz.py` → `interactive_quiz.db`
  - `03_multiple_languages.py` → `multi_lang.db`
  - `05_definition_quiz.py` → `definition_quiz.db`
- Words are loaded only on first run; subsequent runs reuse the
  existing database and spaced-repetition progress.


### v0.4.2 - 20th February 2026

- Updated `examples/06_load_spanish_vocab.py`: use a persistent SQLite
  file (`data/spanish_vocab.db`) instead of in-memory database, so
  spaced-repetition progress survives across sessions. Vocab is loaded
  only on first run.
- Updated `.gitignore`: added `*.db` to ignore runtime databases.


### v0.4.1 - 20th February 2026

- Added `scripts/build_spanish_vocab.py`: downloads frequency and
  dictionary data from doozan/spanish_data, joins them, and outputs
  a ranked Spanish-English vocabulary JSON file.
- Added `data/spanish_top10000.json`: top 10,000 Spanish content words
  with English glosses, ranked by corpus frequency.
- Added `examples/06_load_spanish_vocab.py`: loads the pre-built
  vocabulary into a Rembrandt database and runs an interactive quiz.
- Updated `README.md`: added new example to the examples table.


### v0.4.0 - 20th February 2026

- Added `LearningMode` enum in `models`: `TRANSLATION`, `DEFINITION`.
- Added `learning_mode()` function: derives mode from a word's language
  pair.
- Added `ExerciseType` values:
  - `REVERSE_FLASHCARD`
  - `SELF_GRADED`
- Added exercise generators in `exercises`:
  - `generate_reverse_flashcard()`
  - `generate_self_graded()`
- Updated `generate_exercise()`: definition mode uses 40% multiple
  choice, 30% reverse flashcard, 30% self-graded (never regular
  flashcard).
- Updated `evaluate_answer()`: supports reverse flashcard (compares
  against `word_from`) and self-graded (requires `quality` param).
- Updated `Session.answer()`: accepts optional `quality` parameter
  for self-graded exercises, passed directly to SM-2.
- Added `examples/05_definition_quiz.py`.
- Updated `docs/exercise-types.md`: added reverse flashcard,
  self-graded, learning modes, and updated exercise selection docs.
- Updated `README.md`: added definition learning section and example.


### v0.3.1 - 19th February 2026

- Self-refinement pass on Claude settings:
  - `committing.md`: fixed step 6 (two-step: `uv sync --all-extras` for
    lock file, then `uv pip install -e ".[dev]"` for editable install),
    replaced generic commit examples with project-relevant ones.
  - `versioning.md`: fixed opening line to match commit workflow order.
  - `testing.md`: replaced naming examples from another project with
    Rembrandt ones, removed duplicate "Running Tests" section.
  - `CLAUDE.md`: added examples/ numeric-prefix naming convention.


### v0.3.0 - 19th February 2026

- Added `docs/` folder with theory documentation:
  - `spaced-repetition.md`: forgetting curve, SM-2 algorithm,
    easiness factor, quality scores, worked example.
  - `exercise-types.md`: active recall, flashcard vs. multiple
    choice, answer evaluation.
- Updated `README.md`: added Documentation section.


### v0.2.5 - 19th February 2026

- Fixed double backticks in docstrings across `db.py`, `models.py`,
  and `session.py` to use single backticks per code style rules.


### v0.2.4 - 19th February 2026

- Updated `CLAUDE.md`: added rule to never use
  `from __future__ import annotations`.


### v0.2.3 - 19th February 2026

- Removed `from __future__ import annotations` from all source modules
  (unnecessary with Python >= 3.13).


### v0.2.2 - 19th February 2026

- Updated `.claude/rules/committing.md`: moved reinstall step before commit
  so `uv.lock` changes are always captured in the commit.


### v0.2.1 - 19th February 2026

- Renamed example scripts with numeric prefixes for ordered difficulty:
  - `01_quickstart.py`
  - `02_interactive_quiz.py`
  - `03_multiple_languages.py`
  - `04_spaced_repetition_demo.py`
- Updated `README.md`: updated example file names.


### v0.2.0 - 19th February 2026

- Added `examples/` folder with runnable scripts:
  - `quickstart.py`: minimal self-contained demo.
  - `interactive_quiz.py`: CLI quiz loop with score tracking.
  - `spaced_repetition_demo.py`: SM-2 algorithm visualisation.
  - `multiple_languages.py`: multiple language pairs in one database.
- Updated `README.md`: added Examples section.


### v0.1.0 - 18th February 2026

- Added `models` module with core data models:
  - `Word`
  - `ExerciseType`
  - `Exercise`
  - `AnswerResult`
  - `UserProgress`
- Added `db` module: SQLite database layer for words and progress tracking.
- Added `spaced_repetition` module: SM-2 algorithm with `review()` and `select_words()`.
- Added `exercises` module: flashcard and multiple-choice generation, answer evaluation.
- Added `session` module: `Session` class as the main entry point for chat consumers.
- Added unit tests for all modules (48 tests).
