
## Changelog - Rembrandt

### v6.3.28 - 19th April 2026

- Added `scripts/pre-commit.sh`: canonical pre-commit check from programme. Auto-detects `tests/unit/` vs `tests/` and no-ops if neither exists.


### v6.3.27 - 17th April 2026

- `.gitattributes`: Added LF line ending normalization.

### v6.3.26 - 15th April 2026

- `.claude/`: cross-project migration landed today:
  - Removed `.claude/hooks/block-raw-python.sh`; now provided globally at `~/.claude/hooks/` (PreToolUse Bash guard).
  - Removed `.claude/hooks/block-chained-commands.sh` and `.claude/skills/{refactor,improvements,optimize,self-refinement,backlog}/`; the hook and the five periodic-review skills are now provided globally under `~/.claude/`.
  - Removed `.claude/hooks/format-python.sh`; the ruff auto-format PostToolUse hook is now provided globally at `~/.claude/hooks/`.
  - Removed `.claude/hooks/pre-commit-tests.sh`; replaced by a global dispatcher at `~/.claude/hooks/pre-commit-tests.sh` that invokes `scripts/pre-commit.sh` on `git commit`. Added `scripts/pre-commit.sh` with the project-local test command.


### v6.3.25 - 12th April 2026

- Updated `.claude/hooks/block-chained-commands.sh`:
  propagated newline-chaining block from the
  programme canonical.


### v6.3.24 - 11th April 2026

- `.claude/rules/`:
  - Decoupled `/refactor` rule: canonical
    `refactoring.md` is now procedural only.
  - Added `refactoring-areas.md` with
    project-specific code smells to watch.
- `.claude/skills/refactor/`:
  - Updated `SKILL.md` to read both canonical
    procedure and per-project areas.


### v6.3.23 - 11th April 2026

- `.claude/rules/`:
  - Decoupled `/optimize` rule: canonical
    `optimization.md` is now procedural only.
  - Added `optimization-areas.md` with
    project-specific performance areas.
- `.claude/skills/optimize/`:
  - Updated `SKILL.md` to read both canonical
    procedure and per-project areas.


### v6.3.22 - 10th April 2026

- `.claude/rules/`:
  - Decoupled `/improvements` rule: canonical
    `improvements.md` is now procedural only.
  - Added `improvement-areas.md` with
    project-specific areas to watch.
- `.claude/skills/improvements/`:
  - Updated `SKILL.md` to read both canonical
    procedure and per-project areas.


### v6.3.21 - 5th April 2026

- `.claude/rules/`:
  - Updated `versioning.md`: added changelog
    rotation section (30-version limit, yearly
    archives in `changelog/YYYY.md`).


### v6.3.20 - 5th April 2026

- `.claude/rules/`:
  - Updated `versioning.md`: added changelog
    rotation section (30-version limit, yearly
    archives in `changelog/YYYY.md`).


### v6.3.19 - 5th April 2026

- Rotated changelog: archived 115 old
  entries to `changelog/` yearly files.


### v6.3.18 - 5th April 2026

- `.claude/`:
  - Updated `backlog` skill (v1.4.0): tables now
    always include Priority and Effort columns.


### v6.3.17 - 5th April 2026

- `.claude/hooks/`:
  - Fixed stdin consumption: all hooks now
    capture stdin before piping to python.


### v6.3.16 - 5th April 2026

- `.claude/`:
  - Updated `backlog` skill (v1.3.0): auto-cleans
    completed items before display, shows per-section
    tables when backlog has multiple sections.
  - Updated `backlog` rule: added auto-cleanup
    section.


### v6.3.15 - 5th April 2026

- `.claude/`:
  - Updated `backlog` skill (v1.1.0): auto-cleans
    completed items when 5+ accumulate.
  - Updated `backlog` rule: added auto-cleanup
    section.


### v6.3.14 - 4th April 2026

- `.claude/hooks/`:
  - Added `block-raw-python.sh`: enforces `uv run python`
    over bare `python`.


### v6.3.13 - 4th April 2026

- `.claude/rules/`:
  - Normalized `versioning.md` to enhanced canonical
    with detailed sub-bullet guidance.


### v6.3.12 - 3rd April 2026

- `.claude/rules/`:
  - Normalized `committing.md` to canonical template.


### v6.3.11 - 3rd April 2026

- `.claude/rules/`:
  - Updated `committing.md`: added one-cmd-per-bash.


### v6.3.10 - 3rd April 2026

- `CLAUDE.md`:
  - Normalized to canonical template: added missing
    shared sections, removed low-value sections.


### v6.3.9 - 3rd April 2026

- `.claude/`:
  - Removed empty `commands/` directory (all commands migrated to skills).


### v6.3.8 - 3rd April 2026

- `.claude/`:
  - Migrated `/self-refinement` from command to skill
    (v1.0.0) for version tracking.


### v6.3.7 - 3rd April 2026

- `.claude/`:
  - Migrated `/improvements` from command to skill (v1.0.0)
    for version tracking.


### v6.3.6 - 3rd April 2026

- `.claude/`:
  - Migrated `/optimize` from command to skill (v1.0.0)
    for version tracking.


### v6.3.5 - 3rd April 2026

- `.claude/`:
  - Migrated `/refactor` from command to skill (v1.0.0)
    for version tracking.


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


