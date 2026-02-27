"""Tests for rembrandt.spaced_repetition."""

from datetime import datetime

import pytest

from rembrandt.db import Database
from rembrandt.models import SessionMode, UserProgress, Word
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
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="dog", word_to="perro",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="house", word_to="casa",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="book", word_to="libro",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="water", word_to="agua",
        ),
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


# --- Session Mode Tests ---


def test_select_words_learn_new_only(db_with_words):
    all_words = db_with_words.get_words("en", "es")
    due_word = all_words[0]
    progress = UserProgress(
        user_id="u1",
        word_id=due_word.id,
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
    all_words = db_with_words.get_words("en", "es")
    # Without prioritize_weak, order is unchanged
    words = select_words(
        db_with_words, "u1", "en", "es", count=5,
    )
    assert len(words) > 0
