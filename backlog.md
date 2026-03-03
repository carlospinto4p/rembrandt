
# Backlog - Rembrandt

### 2026.02.27 — Improvement proposals

- [ ] Add listening/spelling exercise type
- [ ] Add LLM integration (dynamic sentences, explanations, contextual examples)

### 2026.03.02 — Anki-style scheduling improvements

- [x] Add learning steps for new cards (short-interval steps before entering SM-2 review queue)
- [x] Add lapse/relearning steps (forgotten mature cards re-enter learning steps instead of hard reset)
- [x] Add fuzz factor to intervals (small randomization to prevent review clustering)
- [x] Add leech detection (flag/suspend cards that repeatedly fail)
- [x] Add daily limits (separate caps for new cards and review cards per session)
- [ ] Add sibling burying (avoid showing the same word in different exercise types in one session)

### 2026.03.03 — Refactoring review (v0.37.0)

- [x] Break `review()` into per-state handler functions (`_handle_new`, `_handle_learning`, `_handle_review`, `_handle_relearning`) — 200+ lines, cyclomatic complexity ~15
- [ ] Extract `_schedule_review(minutes=..., days=...)` helper in `spaced_repetition.py` — 11 repeated `datetime.now() + timedelta(...)` blocks
- [ ] Extract `_get_eligible_exercise_types()` from `generate_exercise()` in `exercises.py` — simplifies 95-line dispatch function
- [ ] Define SM-2 constants (`QUALITY_PASS_THRESHOLD = 3`, `SECOND_CORRECT_INTERVAL = 6`) in `spaced_repetition.py` — replaces magic numbers
- [ ] Wrap `db.py::_migrate()` ALTER TABLE statements in a transaction for schema consistency
- [ ] Extract complex SQL queries (`weak_words`, `daily_stats`) to module-level constants in `db.py`
