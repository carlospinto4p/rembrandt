"""Tests for rembrandt.spaced_repetition."""

from datetime import datetime, timedelta

import pytest

from rembrandt.db import Database
from rembrandt.models import (
    CardState,
    ReviewConfig,
    SessionMode,
    UserProgress,
)
from rembrandt.spaced_repetition import (
    _fuzz_interval,
    review,
    select_words,
)


# --- SM-2 Review Tests (REVIEW state) ---


def _review_progress(**kwargs) -> UserProgress:
    """Create a REVIEW-state progress for SM-2 tests."""
    defaults = dict(
        user_id="u1",
        word_id=1,
        state=CardState.REVIEW,
        next_review=datetime(2026, 1, 1),
    )
    defaults.update(kwargs)
    return UserProgress(**defaults)


def test_review_first_correct():
    progress = _review_progress(repetitions=0, interval=0)
    updated = review(progress, quality=5)
    assert updated.interval == 1
    assert updated.repetitions == 1
    assert updated.easiness_factor >= 2.5
    assert updated.state == CardState.REVIEW


def test_review_second_correct():
    config = ReviewConfig(max_fuzz_factor=0)
    progress = _review_progress(
        repetitions=1, interval=1,
    )
    updated = review(progress, quality=5, config=config)
    assert updated.interval == 6
    assert updated.repetitions == 2


def test_review_third_correct():
    config = ReviewConfig(max_fuzz_factor=0)
    progress = _review_progress(
        repetitions=2, interval=6, easiness_factor=2.5,
    )
    updated = review(progress, quality=5, config=config)
    assert updated.interval == 15
    assert updated.repetitions == 3


def test_review_incorrect_enters_relearning():
    progress = _review_progress(
        repetitions=5, interval=30,
    )
    updated = review(progress, quality=1)
    assert updated.state == CardState.RELEARNING
    assert updated.step_index == 0
    assert updated.repetitions == 0


def test_review_incorrect_no_relearning_steps():
    config = ReviewConfig(relearning_steps=[])
    progress = _review_progress(
        repetitions=5, interval=30,
    )
    updated = review(progress, quality=1, config=config)
    assert updated.state == CardState.REVIEW
    assert updated.repetitions == 0
    assert updated.interval >= 1


def test_review_easiness_factor_decreases_on_low_quality():
    progress = _review_progress(easiness_factor=2.5)
    updated = review(progress, quality=3)
    assert updated.easiness_factor < 2.5


def test_review_easiness_factor_minimum():
    progress = _review_progress(easiness_factor=1.3)
    updated = review(progress, quality=0)
    assert updated.easiness_factor >= 1.3


def test_review_invalid_quality():
    progress = _review_progress()
    with pytest.raises(
        ValueError, match="quality must be 0-5",
    ):
        review(progress, quality=6)

    with pytest.raises(
        ValueError, match="quality must be 0-5",
    ):
        review(progress, quality=-1)


def test_review_next_review_in_future():
    progress = _review_progress()
    updated = review(progress, quality=5)
    assert updated.next_review > datetime.now()


# --- Learning Step Tests ---


def test_new_card_enters_learning():
    progress = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.NEW,
    )
    updated = review(progress, quality=5)
    assert updated.state == CardState.LEARNING
    assert updated.step_index == 0


def test_new_card_fail_enters_learning():
    progress = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.NEW,
    )
    updated = review(progress, quality=1)
    assert updated.state == CardState.LEARNING
    assert updated.step_index == 0


def test_new_card_no_learning_steps_graduates():
    config = ReviewConfig(
        learning_steps=[], graduating_interval=3,
        max_fuzz_factor=0,
    )
    progress = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.NEW,
    )
    updated = review(progress, quality=5, config=config)
    assert updated.state == CardState.REVIEW
    assert updated.interval == 3
    assert updated.repetitions == 1


def test_learning_step_advancement():
    config = ReviewConfig(learning_steps=[1, 10])
    progress = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.LEARNING,
        step_index=0,
    )
    updated = review(progress, quality=5, config=config)
    assert updated.state == CardState.LEARNING
    assert updated.step_index == 1
    expected_delta = timedelta(minutes=10)
    actual_delta = updated.next_review - datetime.now()
    assert abs(
        actual_delta.total_seconds()
        - expected_delta.total_seconds()
    ) < 5


def test_learning_graduation():
    config = ReviewConfig(
        learning_steps=[1, 10],
        graduating_interval=1,
    )
    progress = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.LEARNING,
        step_index=1,
    )
    updated = review(progress, quality=5, config=config)
    assert updated.state == CardState.REVIEW
    assert updated.interval == 1
    assert updated.repetitions == 1
    assert updated.step_index == 0


def test_learning_fail_resets_to_step_zero():
    config = ReviewConfig(learning_steps=[1, 10])
    progress = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.LEARNING,
        step_index=1,
    )
    updated = review(progress, quality=1, config=config)
    assert updated.state == CardState.LEARNING
    assert updated.step_index == 0
    expected_delta = timedelta(minutes=1)
    actual_delta = updated.next_review - datetime.now()
    assert abs(
        actual_delta.total_seconds()
        - expected_delta.total_seconds()
    ) < 5


def test_learning_ef_always_updated():
    progress = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.NEW,
        easiness_factor=2.5,
    )
    updated = review(progress, quality=3)
    assert updated.easiness_factor < 2.5


# --- Relearning Step Tests ---


def test_lapse_enters_relearning():
    progress = _review_progress(
        repetitions=5, interval=30,
    )
    updated = review(progress, quality=1)
    assert updated.state == CardState.RELEARNING
    assert updated.step_index == 0
    assert updated.repetitions == 0


def test_relearning_step_advancement():
    config = ReviewConfig(relearning_steps=[5, 20])
    progress = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.RELEARNING,
        step_index=0,
        interval=30,
    )
    updated = review(progress, quality=5, config=config)
    assert updated.state == CardState.RELEARNING
    assert updated.step_index == 1


def test_relearning_returns_to_review():
    config = ReviewConfig(
        relearning_steps=[10],
        lapse_new_interval_factor=0.7,
        lapse_min_interval=1,
        max_fuzz_factor=0,
    )
    progress = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.RELEARNING,
        step_index=0,
        interval=30,
    )
    updated = review(progress, quality=5, config=config)
    assert updated.state == CardState.REVIEW
    assert updated.repetitions == 1
    assert updated.interval == 21  # round(30 * 0.7)


def test_relearning_min_interval():
    config = ReviewConfig(
        relearning_steps=[10],
        lapse_new_interval_factor=0.1,
        lapse_min_interval=5,
        max_fuzz_factor=0,
    )
    progress = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.RELEARNING,
        step_index=0,
        interval=10,
    )
    updated = review(progress, quality=5, config=config)
    assert updated.state == CardState.REVIEW
    assert updated.interval == 5  # min_interval wins


def test_relearning_fail_resets_to_step_zero():
    config = ReviewConfig(relearning_steps=[5, 20])
    progress = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.RELEARNING,
        step_index=1,
        interval=30,
    )
    updated = review(progress, quality=1, config=config)
    assert updated.state == CardState.RELEARNING
    assert updated.step_index == 0


# --- Config Tests ---


def test_custom_learning_steps():
    config = ReviewConfig(
        learning_steps=[1, 5, 15],
        graduating_interval=2,
    )
    p = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.NEW,
    )
    p = review(p, quality=5, config=config)
    assert p.state == CardState.LEARNING
    assert p.step_index == 0

    p = review(p, quality=5, config=config)
    assert p.state == CardState.LEARNING
    assert p.step_index == 1

    p = review(p, quality=5, config=config)
    assert p.state == CardState.LEARNING
    assert p.step_index == 2

    p = review(p, quality=5, config=config)
    assert p.state == CardState.REVIEW
    assert p.interval == 2


def test_single_learning_step():
    config = ReviewConfig(
        learning_steps=[5],
        graduating_interval=1,
    )
    p = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.NEW,
    )
    p = review(p, quality=5, config=config)
    assert p.state == CardState.LEARNING
    assert p.step_index == 0

    p = review(p, quality=5, config=config)
    assert p.state == CardState.REVIEW
    assert p.interval == 1


def test_empty_learning_and_relearning_steps():
    config = ReviewConfig(
        learning_steps=[],
        relearning_steps=[],
        graduating_interval=1,
    )
    p = UserProgress(
        user_id="u1", word_id=1,
        state=CardState.NEW,
    )
    # Graduates immediately
    p = review(p, quality=5, config=config)
    assert p.state == CardState.REVIEW

    # Lapse stays in REVIEW (no relearning steps)
    p = review(p, quality=1, config=config)
    assert p.state == CardState.REVIEW


# --- Word Selection Tests ---


def test_select_words_returns_new_words(db_with_words):
    words = select_words(
        db_with_words, "u1", "en", "es", count=3,
    )
    assert len(words) == 3


def test_select_words_empty_db(tmp_path):
    db = Database(tmp_path / "empty.db")
    words = select_words(db, "u1", "en", "es", count=5)
    assert words == []
    db.close()


def test_select_words_due_before_new(db_with_words):
    all_words = db_with_words.get_words("en", "es")
    due_word = all_words[0]

    progress = UserProgress(
        user_id="u1",
        word_id=due_word.id,
        state=CardState.REVIEW,
        next_review=datetime(2020, 1, 1),
    )
    db_with_words.upsert_progress(progress)

    words = select_words(
        db_with_words, "u1", "en", "es", count=1,
    )
    assert len(words) == 1
    assert words[0].id == due_word.id


def test_select_words_learning_before_due(db_with_words):
    all_words = db_with_words.get_words("en", "es")
    learning_word = all_words[0]
    review_word = all_words[1]

    db_with_words.upsert_progress(UserProgress(
        user_id="u1",
        word_id=learning_word.id,
        state=CardState.LEARNING,
        next_review=datetime(2020, 1, 1),
    ))
    db_with_words.upsert_progress(UserProgress(
        user_id="u1",
        word_id=review_word.id,
        state=CardState.REVIEW,
        next_review=datetime(2020, 1, 1),
    ))

    words = select_words(
        db_with_words, "u1", "en", "es", count=1,
    )
    assert len(words) == 1
    assert words[0].id == learning_word.id


def test_select_words_respects_count(db_with_words):
    words = select_words(
        db_with_words, "u1", "en", "es", count=2,
    )
    assert len(words) == 2


# --- Session Mode Tests ---


def test_select_words_learn_new_only(db_with_words):
    all_words = db_with_words.get_words("en", "es")
    due_word = all_words[0]
    progress = UserProgress(
        user_id="u1",
        word_id=due_word.id,
        state=CardState.REVIEW,
        next_review=datetime(2020, 1, 1),
    )
    db_with_words.upsert_progress(progress)

    words = select_words(
        db_with_words, "u1", "en", "es", count=5,
        mode=SessionMode.LEARN_NEW,
    )
    ids = [w.id for w in words]
    assert due_word.id not in ids
    assert len(words) == 4


def test_select_words_review_due_only(db_with_words):
    all_words = db_with_words.get_words("en", "es")
    due_word = all_words[0]
    progress = UserProgress(
        user_id="u1",
        word_id=due_word.id,
        state=CardState.REVIEW,
        next_review=datetime(2020, 1, 1),
    )
    db_with_words.upsert_progress(progress)

    words = select_words(
        db_with_words, "u1", "en", "es", count=5,
        mode=SessionMode.REVIEW_DUE,
    )
    assert len(words) == 1
    assert words[0].id == due_word.id


def test_select_words_mixed_default(db_with_words):
    all_words = db_with_words.get_words("en", "es")
    due_word = all_words[0]
    progress = UserProgress(
        user_id="u1",
        word_id=due_word.id,
        state=CardState.REVIEW,
        next_review=datetime(2020, 1, 1),
    )
    db_with_words.upsert_progress(progress)

    words = select_words(
        db_with_words, "u1", "en", "es", count=3,
    )
    assert len(words) == 3
    assert words[0].id == due_word.id


def test_select_words_word_ids_filter(db_with_words):
    all_words = db_with_words.get_words("en", "es")
    subset_ids = [all_words[0].id, all_words[1].id]

    words = select_words(
        db_with_words, "u1", "en", "es", count=5,
        word_ids=subset_ids,
    )
    assert len(words) == 2
    result_ids = {w.id for w in words}
    assert result_ids == set(subset_ids)


# --- Prioritize Weak Tests ---


def test_select_words_prioritize_weak(db_with_words):
    all_words = db_with_words.get_words("en", "es")
    strong_word = all_words[0]
    weak_word = all_words[1]

    # Make both due for review
    for w in [strong_word, weak_word]:
        db_with_words.upsert_progress(UserProgress(
            user_id="u1",
            word_id=w.id,
            state=CardState.REVIEW,
            next_review=datetime(2020, 1, 1),
        ))

    # Record history: strong_word correct, weak_word wrong
    for _ in range(4):
        db_with_words.record_answer(
            "u1", strong_word.id, "flashcard", True, 5,
        )
        db_with_words.record_answer(
            "u1", weak_word.id, "flashcard", False, 1,
        )

    words = select_words(
        db_with_words, "u1", "en", "es", count=2,
        mode=SessionMode.REVIEW_DUE,
        prioritize_weak=True,
    )
    assert len(words) == 2
    assert words[0].id == weak_word.id


def test_select_words_no_prioritize_by_default(
    db_with_words,
):
    # Without prioritize_weak, order is unchanged
    words = select_words(
        db_with_words, "u1", "en", "es", count=5,
    )
    assert len(words) > 0


# --- Fuzz Factor Tests ---


def test_fuzz_interval_no_fuzz_small_interval():
    assert _fuzz_interval(1, 0.05) == 1
    assert _fuzz_interval(2, 0.05) == 2


def test_fuzz_interval_disabled():
    assert _fuzz_interval(10, 0) == 10
    assert _fuzz_interval(30, 0) == 30
    assert _fuzz_interval(10, -0.1) == 10


def test_fuzz_interval_applied(monkeypatch):
    # fuzz_days = max(1, round(20 * 0.05)) = 1
    # randint(19, 21) -> mock returns 19
    monkeypatch.setattr(
        "rembrandt.spaced_repetition.random.randint",
        lambda lo, hi: lo,
    )
    assert _fuzz_interval(20, 0.05) == 19

    monkeypatch.setattr(
        "rembrandt.spaced_repetition.random.randint",
        lambda lo, hi: hi,
    )
    assert _fuzz_interval(20, 0.05) == 21


def test_fuzz_interval_minimum_one(monkeypatch):
    # With a large negative fuzz, result is clamped to 1
    monkeypatch.setattr(
        "rembrandt.spaced_repetition.random.randint",
        lambda lo, hi: lo,
    )
    assert _fuzz_interval(3, 1.0) >= 1


def test_review_fuzz_applied_to_sm2_interval(
    monkeypatch,
):
    # Verify fuzz is applied in the REVIEW pass path
    monkeypatch.setattr(
        "rembrandt.spaced_repetition.random.randint",
        lambda lo, hi: hi,
    )
    progress = _review_progress(
        repetitions=2, interval=6, easiness_factor=2.5,
    )
    updated = review(progress, quality=5)
    # Base: round(6 * 2.5) = 15
    # fuzz_days = max(1, round(15 * 0.05)) = 1
    # randint(14, 16) -> hi = 16
    assert updated.interval == 16


# --- Leech Detection Tests ---


def test_review_fail_increments_lapse_count():
    progress = _review_progress(
        repetitions=3, interval=10, lapse_count=0,
    )
    updated = review(progress, quality=1)
    assert updated.lapse_count == 1


def test_lapse_count_not_reset_on_pass():
    progress = _review_progress(
        repetitions=3, interval=10, lapse_count=5,
    )
    updated = review(progress, quality=5)
    assert updated.lapse_count == 5


def test_leech_threshold_suspends_card():
    config = ReviewConfig(leech_threshold=3)
    progress = _review_progress(
        repetitions=3, interval=10, lapse_count=2,
    )
    updated = review(progress, quality=1, config=config)
    assert updated.lapse_count == 3
    assert updated.state == CardState.SUSPENDED


def test_leech_detection_disabled():
    config = ReviewConfig(leech_threshold=0)
    progress = _review_progress(
        repetitions=3, interval=10, lapse_count=100,
    )
    updated = review(progress, quality=1, config=config)
    assert updated.state != CardState.SUSPENDED
    assert updated.lapse_count == 101


def test_suspended_card_skipped_in_select(
    db_with_words,
):
    all_words = db_with_words.get_words("en", "es")
    suspended_word = all_words[0]

    db_with_words.upsert_progress(UserProgress(
        user_id="u1",
        word_id=suspended_word.id,
        state=CardState.SUSPENDED,
        next_review=datetime(2020, 1, 1),
    ))

    words = select_words(
        db_with_words, "u1", "en", "es", count=5,
    )
    ids = [w.id for w in words]
    assert suspended_word.id not in ids


def test_review_suspended_card_unchanged():
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        state=CardState.SUSPENDED,
        lapse_count=8,
        interval=10,
        easiness_factor=2.0,
        next_review=datetime(2026, 1, 1),
    )
    updated = review(progress, quality=5)
    assert updated.state == CardState.SUSPENDED
    assert updated.lapse_count == 8
    assert updated.interval == 10
    assert updated.easiness_factor == 2.0


# --- Daily Limit Tests ---


def test_select_words_max_new_limits_new_words(
    db_with_words,
):
    words = select_words(
        db_with_words, "u1", "en", "es", count=5,
        max_new=2,
    )
    assert len(words) == 2


def test_select_words_max_review_limits_due_words(
    db_with_words,
):
    all_words = db_with_words.get_words("en", "es")
    for w in all_words[:3]:
        db_with_words.upsert_progress(UserProgress(
            user_id="u1",
            word_id=w.id,
            state=CardState.REVIEW,
            next_review=datetime(2020, 1, 1),
        ))

    words = select_words(
        db_with_words, "u1", "en", "es", count=5,
        max_review=1,
    )
    # 1 due + 2 new = 3
    due_ids = {all_words[i].id for i in range(3)}
    due_in_result = [
        w for w in words if w.id in due_ids
    ]
    assert len(due_in_result) == 1


def test_select_words_in_steps_not_capped(
    db_with_words,
):
    all_words = db_with_words.get_words("en", "es")
    for w in all_words[:2]:
        db_with_words.upsert_progress(UserProgress(
            user_id="u1",
            word_id=w.id,
            state=CardState.LEARNING,
            next_review=datetime(2020, 1, 1),
        ))

    words = select_words(
        db_with_words, "u1", "en", "es", count=5,
        max_new=0, max_review=0,
    )
    # in_steps are not capped, new=0, review=0
    assert len(words) == 2
    ids = {w.id for w in words}
    assert ids == {all_words[0].id, all_words[1].id}


def test_select_words_limits_none_means_unlimited(
    db_with_words,
):
    words = select_words(
        db_with_words, "u1", "en", "es", count=5,
        max_new=None, max_review=None,
    )
    assert len(words) == 5
