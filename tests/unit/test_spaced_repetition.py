"""Tests for rembrandt.spaced_repetition."""

from datetime import datetime

import pytest

from rembrandt.db import Database
from rembrandt.models import UserProgress
from rembrandt.spaced_repetition import review, select_words


# --- SM-2 Review Tests ---


def test_review_first_correct():
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        next_review=datetime(2026, 1, 1),
    )
    updated = review(progress, quality=5)
    assert updated.interval == 1
    assert updated.repetitions == 1
    assert updated.easiness_factor >= 2.5


def test_review_second_correct():
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        repetitions=1,
        interval=1,
        next_review=datetime(2026, 1, 1),
    )
    updated = review(progress, quality=5)
    assert updated.interval == 6
    assert updated.repetitions == 2


def test_review_third_correct():
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        repetitions=2,
        interval=6,
        easiness_factor=2.5,
        next_review=datetime(2026, 1, 1),
    )
    updated = review(progress, quality=5)
    assert updated.interval == 15
    assert updated.repetitions == 3


def test_review_incorrect_resets_repetitions():
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        repetitions=5,
        interval=30,
        next_review=datetime(2026, 1, 1),
    )
    updated = review(progress, quality=1)
    assert updated.repetitions == 0
    assert updated.interval == 1


def test_review_easiness_factor_decreases_on_low_quality():
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        easiness_factor=2.5,
        next_review=datetime(2026, 1, 1),
    )
    updated = review(progress, quality=3)
    assert updated.easiness_factor < 2.5


def test_review_easiness_factor_minimum():
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        easiness_factor=1.3,
        next_review=datetime(2026, 1, 1),
    )
    updated = review(progress, quality=0)
    assert updated.easiness_factor >= 1.3


def test_review_invalid_quality():
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        next_review=datetime(2026, 1, 1),
    )
    with pytest.raises(ValueError, match="quality must be 0-5"):
        review(progress, quality=6)

    with pytest.raises(ValueError, match="quality must be 0-5"):
        review(progress, quality=-1)


def test_review_next_review_in_future():
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        next_review=datetime(2026, 1, 1),
    )
    updated = review(progress, quality=5)
    assert updated.next_review > datetime.now()


# --- Word Selection Tests ---


@pytest.fixture
def db_with_words(tmp_path):
    db = Database(tmp_path / "test.db")
    db.add_words([
        ("en", "es", "cat", "gato"),
        ("en", "es", "dog", "perro"),
        ("en", "es", "house", "casa"),
        ("en", "es", "book", "libro"),
        ("en", "es", "water", "agua"),
    ])
    yield db
    db.close()


def test_select_words_returns_new_words(db_with_words):
    words = select_words(
        db_with_words, "u1", "en", "es", count=3
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
        next_review=datetime(2020, 1, 1),
    )
    db_with_words.upsert_progress(progress)

    words = select_words(
        db_with_words, "u1", "en", "es", count=1
    )
    assert len(words) == 1
    assert words[0].id == due_word.id


def test_select_words_respects_count(db_with_words):
    words = select_words(
        db_with_words, "u1", "en", "es", count=2
    )
    assert len(words) == 2
