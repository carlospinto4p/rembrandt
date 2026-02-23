
# Backlog - Rembrandt

### 2026.02.20

- [ ] Add `users` table and user management (registration, lookup)
- [ ] Add user session management (session tokens, expiry, login/logout)

### 2026.02.23 (v0.6.1 refactor review)

- [x] Batch `add_words()` in a single transaction instead of committing per word (N+1 commits)
- [x] Add bulk `get_progress_for_words()` method and use it in `select_words()` to eliminate N+1 queries
- [x] Add `__enter__`/`__exit__` to `Database` for context-manager support
- [x] Move `UserProgress` import in `session.py:95` to top-level (no circular dependency)
- [x] Replace `type: ignore[arg-type]` on `word.id` with runtime assertions or narrow the type after DB load
- [x] Move shared `db` fixture to `tests/unit/conftest.py` (duplicated in `test_db.py` and `test_session.py`)
- [x] Convert `_sample_words()` / `_definition_words()` in `test_exercises.py` to proper `@pytest.fixture`s
