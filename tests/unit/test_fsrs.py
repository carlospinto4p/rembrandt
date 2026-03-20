"""Tests for rembrandt.fsrs."""

from datetime import datetime, timedelta

import pytest

from rembrandt.fsrs import (
    AGAIN,
    EASY,
    GOOD,
    HARD,
    _init_difficulty,
    _init_stability,
    _interval,
    _next_difficulty,
    _quality_to_grade,
    fsrs_review,
    retrievability,
)
from rembrandt.models import (
    CardState,
    FSRSConfig,
    UserProgress,
)

pytestmark = pytest.mark.asyncio


# --- Retrievability Tests ---


def test_retrievability_at_stability():
    r = retrievability(3.0, 3.0)
    assert abs(r - 0.9) < 0.001


def test_retrievability_at_zero():
    assert retrievability(0.0, 5.0) == 1.0


def test_retrievability_decreases_over_time():
    r1 = retrievability(1.0, 5.0)
    r2 = retrievability(10.0, 5.0)
    assert r1 > r2


def test_retrievability_zero_stability():
    assert retrievability(1.0, 0.0) == 0.0


# --- Interval Tests ---


def test_interval_at_default_retention():
    cfg = FSRSConfig()
    iv = _interval(3.0, 0.9, cfg.max_interval)
    assert iv == 3


def test_interval_minimum_one():
    iv = _interval(0.001, 0.9, 36500)
    assert iv >= 1


def test_interval_capped_at_max():
    iv = _interval(100000.0, 0.9, 365)
    assert iv == 365


# --- Init Stability Tests ---


def test_init_stability_again():
    w = FSRSConfig().weights
    s = _init_stability(AGAIN, w)
    assert s == w[0]


def test_init_stability_easy():
    w = FSRSConfig().weights
    s = _init_stability(EASY, w)
    assert s == w[3]


# --- Init Difficulty Tests ---


def test_init_difficulty_range():
    w = FSRSConfig().weights
    for grade in (AGAIN, HARD, GOOD, EASY):
        d = _init_difficulty(grade, w)
        assert 1.0 <= d <= 10.0


def test_init_difficulty_decreases_with_grade():
    w = FSRSConfig().weights
    d_again = _init_difficulty(AGAIN, w)
    d_easy = _init_difficulty(EASY, w)
    assert d_again > d_easy


# --- Difficulty Update Tests ---


def test_next_difficulty_easy_decreases():
    w = FSRSConfig().weights
    d = 5.0
    d2 = _next_difficulty(d, EASY, w)
    assert d2 < d


def test_next_difficulty_again_increases():
    w = FSRSConfig().weights
    d = 5.0
    d2 = _next_difficulty(d, AGAIN, w)
    assert d2 > d


def test_next_difficulty_clamped():
    w = FSRSConfig().weights
    d_low = _next_difficulty(1.0, EASY, w)
    d_high = _next_difficulty(10.0, AGAIN, w)
    assert d_low >= 1.0
    assert d_high <= 10.0


# --- Quality to Grade Mapping ---


def test_quality_to_grade_mapping():
    assert _quality_to_grade(0) == AGAIN
    assert _quality_to_grade(1) == AGAIN
    assert _quality_to_grade(2) == AGAIN
    assert _quality_to_grade(3) == HARD
    assert _quality_to_grade(4) == GOOD
    assert _quality_to_grade(5) == EASY


# --- fsrs_review: NEW State Tests ---


def test_fsrs_review_new_good():
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.NEW,
    )
    updated = fsrs_review(p, 4)
    assert updated.stability is not None
    assert updated.stability > 0
    assert updated.difficulty is not None
    assert 1.0 <= updated.difficulty <= 10.0


def test_fsrs_review_new_again_enters_learning():
    cfg = FSRSConfig(learning_steps=[1, 10])
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.NEW,
    )
    updated = fsrs_review(p, 1, config=cfg)
    assert updated.state == CardState.LEARNING
    assert updated.step_index == 0


def test_fsrs_review_new_easy_graduates():
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.NEW,
    )
    updated = fsrs_review(p, 5)
    assert updated.state == CardState.REVIEW
    assert updated.stability is not None


def test_fsrs_review_new_no_steps_graduates():
    cfg = FSRSConfig(learning_steps=[])
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.NEW,
    )
    updated = fsrs_review(p, 4, config=cfg)
    assert updated.state == CardState.REVIEW


# --- fsrs_review: REVIEW State Tests ---


def test_fsrs_review_review_good():
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.REVIEW,
        stability=5.0,
        difficulty=5.0,
        interval=5,
        next_review=(
            datetime.now() - timedelta(days=5)
        ),
    )
    updated = fsrs_review(p, 4)
    assert updated.state == CardState.REVIEW
    assert updated.stability > p.stability
    assert updated.interval >= 1


def test_fsrs_review_review_again_relearning():
    cfg = FSRSConfig(relearning_steps=[10])
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.REVIEW,
        stability=10.0,
        difficulty=5.0,
        interval=10,
        next_review=(
            datetime.now() - timedelta(days=10)
        ),
    )
    updated = fsrs_review(p, 1, config=cfg)
    assert updated.state == CardState.RELEARNING
    assert updated.lapse_count == 1
    assert updated.stability < p.stability


def test_fsrs_review_review_easy_bonus():
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.REVIEW,
        stability=5.0,
        difficulty=5.0,
        interval=5,
        next_review=(
            datetime.now() - timedelta(days=5)
        ),
    )
    good = fsrs_review(p, 4)
    easy = fsrs_review(p, 5)
    assert easy.stability > good.stability


# --- fsrs_review: LEARNING State Tests ---


def test_fsrs_review_learning_good_advances():
    cfg = FSRSConfig(learning_steps=[1, 10])
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.LEARNING,
        step_index=0,
        stability=1.0,
        difficulty=5.0,
    )
    updated = fsrs_review(p, 4, config=cfg)
    assert updated.step_index == 1
    assert updated.state == CardState.LEARNING


def test_fsrs_review_learning_last_step_graduates():
    cfg = FSRSConfig(learning_steps=[1, 10])
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.LEARNING,
        step_index=1,
        stability=3.0,
        difficulty=5.0,
    )
    updated = fsrs_review(p, 4, config=cfg)
    assert updated.state == CardState.REVIEW


def test_fsrs_review_learning_easy_graduates():
    cfg = FSRSConfig(learning_steps=[1, 10])
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.LEARNING,
        step_index=0,
        stability=3.0,
        difficulty=5.0,
    )
    updated = fsrs_review(p, 5, config=cfg)
    assert updated.state == CardState.REVIEW


def test_fsrs_review_learning_again_resets_step():
    cfg = FSRSConfig(learning_steps=[1, 10])
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.LEARNING,
        step_index=1,
        stability=1.0,
        difficulty=5.0,
    )
    updated = fsrs_review(p, 1, config=cfg)
    assert updated.step_index == 0
    assert updated.state == CardState.LEARNING


# --- fsrs_review: SUSPENDED State Tests ---


def test_fsrs_review_suspended_unchanged():
    p = UserProgress(
        user_id=1, concept_id=1,
        state=CardState.SUSPENDED,
        stability=5.0,
        difficulty=5.0,
    )
    updated = fsrs_review(p, 4)
    assert updated.state == CardState.SUSPENDED


# --- Session Integration Tests ---


async def test_session_with_fsrs(db_with_concepts):
    from rembrandt.models import ExerciseType
    from rembrandt.session import Session

    s = Session(
        db_with_concepts, user_id=1,
        fsrs_config=FSRSConfig(),
    )
    ex = await s.next_exercise()
    assert ex is not None
    if ex.exercise_type == ExerciseType.SELF_GRADED:
        result = await s.answer(quality=5)
    else:
        result = await s.answer(ex.concept.back)
    assert result.correct is True

    progress = await db_with_concepts.get_progress(
        1, ex.concept.id,
    )
    assert progress is not None
    assert progress.stability is not None
    assert progress.difficulty is not None
