"""Tests for rembrandt.session."""

import pytest

from rembrandt.db import Database
from rembrandt.models import ExerciseType
from rembrandt.session import Session


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    database.add_words([
        ("en", "es", "cat", "gato"),
        ("en", "es", "dog", "perro"),
        ("en", "es", "house", "casa"),
        ("en", "es", "book", "libro"),
    ])
    yield database
    database.close()


@pytest.fixture
def session(db):
    return Session(db, user_id="u1", language_from="en",
                   language_to="es")


# --- Session Tests ---


def test_next_exercise_returns_exercise(session):
    ex = session.next_exercise()
    assert ex is not None
    assert ex.exercise_type in (
        ExerciseType.FLASHCARD,
        ExerciseType.MULTIPLE_CHOICE,
    )


def test_next_exercise_no_words(tmp_path):
    db = Database(tmp_path / "empty.db")
    s = Session(db, "u1", "en", "es")
    assert s.next_exercise() is None
    db.close()


def test_answer_correct(session):
    ex = session.next_exercise()
    assert ex is not None
    result = session.answer(ex.word.word_to)
    assert result.correct is True


def test_answer_incorrect(session):
    ex = session.next_exercise()
    assert ex is not None
    result = session.answer("wrong_answer_xyz")
    assert result.correct is False


def test_answer_updates_progress(session):
    ex = session.next_exercise()
    assert ex is not None
    word_id = ex.word.id
    session.answer(ex.word.word_to)

    progress = session.db.get_progress("u1", word_id)
    assert progress is not None
    assert progress.repetitions == 1


def test_answer_without_exercise_raises(session):
    with pytest.raises(RuntimeError, match="No active exercise"):
        session.answer("gato")


def test_full_session_flow(session):
    ex1 = session.next_exercise()
    assert ex1 is not None
    r1 = session.answer(ex1.word.word_to)
    assert r1.correct is True

    ex2 = session.next_exercise()
    assert ex2 is not None
    r2 = session.answer("definitely_wrong")
    assert r2.correct is False
