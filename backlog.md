
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

### 2026.02.23 — Spanish vocabulary: Layer 1 (data)

- [ ] Source Spanish-Spanish definitions (Wiktionary or RAE-based) and build a monolingual dataset
- [ ] Add multiple senses per word (not just one gloss)
- [ ] Add noun gender (`m`/`f`) and verb conjugation group to word metadata
- [ ] Add CEFR-level tagging (A1–C2) based on frequency bands
- [ ] Add topic tags (food, travel, body, emotions, etc.)
- [ ] Update `build_spanish_vocab.py` (or add a new script) to produce the enriched dataset

### 2026.02.23 — Spanish vocabulary: Layer 2 (structured lessons)

- [ ] Add a `Lesson` model: named set of words with a learning goal
- [ ] Pre-build lessons by CEFR level and topic
- [ ] Add session modes: "learn new", "review due", "mixed"
- [ ] Track progress per lesson (completion %, words mastered)

### 2026.02.23 — Spanish vocabulary: Layer 3 (Spanish-specific exercises)

- [ ] Verb conjugation drills (present, preterite, imperfect, subjunctive, etc.)
- [ ] Gender/article matching exercises ("el/la ___")
- [ ] Cloze / fill-in-the-blank with example sentences
- [ ] Production mode (en→es) — expand after monolingual Spanish is solid
