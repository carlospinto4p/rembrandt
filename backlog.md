
# Backlog - Rembrandt

### 2026.02.20

- [ ] Add `users` table and user management (registration, lookup)
- [ ] Add user session management (session tokens, expiry, login/logout)

### 2026.02.23 — Spanish vocabulary: Layer 1 (data)

- [x] Source Spanish-Spanish definitions (Wiktionary or RAE-based) and build a monolingual dataset
- [x] Add multiple senses per word (not just one gloss)
- [x] Add noun gender (`m`/`f`) and verb conjugation group to word metadata
- [ ] Add CEFR-level tagging (A1–C2) based on frequency bands
- [ ] Add topic tags (food, travel, body, emotions, etc.)
- [x] Update `build_spanish_vocab.py` (or add a new script) to produce the enriched dataset

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
