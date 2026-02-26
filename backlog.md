
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
