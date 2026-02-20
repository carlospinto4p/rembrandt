
## Changelog - Rembrandt

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
