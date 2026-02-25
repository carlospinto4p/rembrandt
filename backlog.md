
# Backlog - Rembrandt

### 2026.02.20

- [ ] Add `users` table and user management (registration, lookup)
- [ ] Add user session management (session tokens, expiry, login/logout)

### 2026.02.25 (v0.17.1 refactor review)

- [x] Rename `generate_production_cloze()` → `generate_translation_cloze_sentence()` in `sentences.py` and update import in `exercises.py`
- [x] Fix stale "production" wording in `sentences.py` module docstring
- [ ] Fix stale `PRODUCTION` / `generate_production()` references in `changelog.md` v0.17.0 entry
- [ ] Add `TRANSLATION_CLOZE` section to `docs/exercise-types.md` and update the pool description
- [ ] Add `TRANSLATION_CLOZE` enum value test in `test_models.py`
- [ ] Extract dispatch dict in `generate_exercise()` to replace if/elif chain (`exercises.py`)
- [ ] Extract `_resolve_option_number()` helper to deduplicate option-number resolution in `evaluate_answer()` (`exercises.py`)
- [ ] Extract `_row_to_word()` / `_row_to_progress()` helpers in `db.py` to deduplicate Row→Model mapping
- [ ] DRY `add_lesson()` by delegating to `add_lessons()` in `db.py`
- [ ] Extract `_select_templates()` helper in `sentences.py` to share POS-heuristic logic between `generate_cloze()` and `generate_translation_cloze_sentence()`
