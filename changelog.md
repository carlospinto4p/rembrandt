
## Changelog - Rembrandt

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
