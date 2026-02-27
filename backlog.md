
# Backlog - Rembrandt

### 2026.02.20

- [x] Add `users` table and user management (registration, lookup)
- [x] Add user session management (session tokens, expiry, login/logout)

### 2026.02.25 — Client readiness

- [x] Add session statistics: track correct/incorrect counts, streak, and provide a session summary
- [x] Add `Database.update_word()` and `Database.delete_word()` for word CRUD
- [x] Add `Database.update_lesson()` and `Database.delete_lesson()` for lesson CRUD
- [x] Add `Session.skip()`: move to next exercise without affecting progress
- [x] Add hint system: request partial hints (first letter, word length) before answering

### 2026.02.26 (v0.24.0 refactor review)

- [x] Extract `_insert_lesson_words()` helper in `db.py` — identical loop in `add_lessons()` and `update_lesson()`
- [x] Replace `assert` with explicit `ValueError` in `session.py` and `spaced_repetition.py` — assertions can be disabled with `-O`
- [x] Fix `type: ignore[assignment]` in `lessons.py:52` — guard `w.id` against `None` instead of suppressing
- [x] Extract `_update_stats()` helper from `Session.answer()` — method is ~54 lines mixing evaluation, progress, and stats
- [x] Add section comments to `exercises.py` — 15 functions with no grouping (generators vs evaluation vs helpers)
- [x] Remove lambda wrappers in `generate_exercise()` dispatch dict — use `functools.partial` for callables that need extra args
- [x] Add examples for newer features: user registration/auth, session tokens, hints, skip, session stats, word/lesson update/delete

### 2026.02.27 — Improvement proposals

**Conjugation & Grammar**
- [x] Add more tenses: futuro simple, condicional, subjuntivo presente
- [x] Add more irregular verbs: `conocer`, `dormir`, `pedir`, `sentir`, `jugar`, etc.
- [x] Add adjective agreement exercise type (gender/number matching)

**Exercise Variety**
- [x] Add more cloze templates (and/or load from JSON for extensibility)
- [x] Add sentence ordering exercise type (scrambled words)
- [ ] Add listening/spelling exercise type

**Data & Progress**
- [x] Add progress export/import (JSON export of progress table)
- [x] Add historical stats tracking (accuracy trends, words learned per day)
- [x] Add weak word detection (surface consistently wrong words more often)

**Architecture**
- [ ] Add LLM integration (dynamic sentences, explanations, contextual examples)
- [x] Add pluggable template system (load templates from config files)

### 2026.02.27 (v0.27.0 refactor review)

- [x] Deduplicate tail of `evaluate_answer()` in `exercises.py` — the `expected_answer` branch and the default branch share identical resolve/match/return logic; merge into a single path that first determines `expected`
- [x] Use `authenticate_user()` to call `get_user()` internally in `db.py` — duplicate `SELECT * FROM users WHERE username = ?` query in both methods
- [x] Move shared test fixtures to `conftest.py` — `sample_words` (in `test_exercises.py`) and `db_with_words` (in `test_spaced_repetition.py`) create the same EN-ES word list; `definition_words` is also reusable
- [x] Extract `_in_clause()` helper in `db.py` — the `",".join("?" for _ in ids)` + parameter list pattern repeats in `get_all_progress()` and `get_lessons()`
- [x] Collapse `_row_to_user_session()` datetime parsing — uses `strptime` with `_ISO_FMT` while `_row_to_user()` uses `fromisoformat()`; standardise on `fromisoformat()` for all converters
