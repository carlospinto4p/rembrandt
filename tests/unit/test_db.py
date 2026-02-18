"""Tests for rembrandt.db."""

from datetime import datetime

import pytest

from rembrandt.db import Database
from rembrandt.models import UserProgress


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


# --- Word CRUD Tests ---


def test_add_word(db):
    word = db.add_word("en", "es", "hello", "hola")
    assert word.id is not None
    assert word.word_from == "hello"
    assert word.word_to == "hola"


def test_add_words_bulk(db):
    words = db.add_words([
        ("en", "es", "cat", "gato"),
        ("en", "es", "dog", "perro"),
        ("en", "es", "house", "casa"),
    ])
    assert len(words) == 3
    assert all(w.id is not None for w in words)
    assert words[0].word_from == "cat"
    assert words[2].word_to == "casa"


def test_get_words_empty(db):
    result = db.get_words("en", "es")
    assert result == []


def test_get_words_filters_by_language(db):
    db.add_word("en", "es", "hello", "hola")
    db.add_word("en", "fr", "hello", "bonjour")

    es_words = db.get_words("en", "es")
    assert len(es_words) == 1
    assert es_words[0].word_to == "hola"

    fr_words = db.get_words("en", "fr")
    assert len(fr_words) == 1
    assert fr_words[0].word_to == "bonjour"


def test_add_word_auto_increments_id(db):
    w1 = db.add_word("en", "es", "cat", "gato")
    w2 = db.add_word("en", "es", "dog", "perro")
    assert w2.id == w1.id + 1


# --- Progress CRUD Tests ---


def test_get_progress_nonexistent(db):
    result = db.get_progress("u1", 999)
    assert result is None


def test_upsert_progress_insert(db):
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        easiness_factor=2.5,
        interval=1,
        repetitions=1,
        next_review=datetime(2026, 3, 1, 12, 0, 0),
    )
    db.upsert_progress(progress)

    loaded = db.get_progress("u1", 1)
    assert loaded is not None
    assert loaded.easiness_factor == 2.5
    assert loaded.interval == 1
    assert loaded.repetitions == 1


def test_upsert_progress_update(db):
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        next_review=datetime(2026, 3, 1, 12, 0, 0),
    )
    db.upsert_progress(progress)

    progress.easiness_factor = 2.1
    progress.interval = 6
    progress.repetitions = 3
    db.upsert_progress(progress)

    loaded = db.get_progress("u1", 1)
    assert loaded is not None
    assert loaded.easiness_factor == 2.1
    assert loaded.interval == 6
    assert loaded.repetitions == 3


def test_progress_roundtrip_datetime(db):
    dt = datetime(2026, 6, 15, 10, 30, 0)
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        next_review=dt,
    )
    db.upsert_progress(progress)

    loaded = db.get_progress("u1", 1)
    assert loaded is not None
    assert loaded.next_review == dt
