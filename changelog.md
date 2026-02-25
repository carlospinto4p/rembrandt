
## Changelog - Rembrandt

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
