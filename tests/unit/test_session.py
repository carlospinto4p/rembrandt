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


@pytest.fixture
def definition_db(tmp_path):
    database = Database(tmp_path / "def.db")
    database.add_words([
        ("en", "en", "ephemeral",
         "lasting for a very short time"),
        ("en", "en", "ubiquitous", "present everywhere"),
        ("en", "en", "candid",
         "truthful and straightforward"),
        ("en", "en", "pragmatic",
         "dealing with things practically"),
    ])
    yield database
    database.close()


@pytest.fixture
def definition_session(definition_db):
    return Session(
        definition_db, user_id="u1",
        language_from="en", language_to="en",
    )


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


# --- Definition Mode Tests ---


def test_definition_next_exercise_valid_type(
    definition_session,
):
    ex = definition_session.next_exercise()
    assert ex is not None
    assert ex.exercise_type in (
        ExerciseType.MULTIPLE_CHOICE,
        ExerciseType.REVERSE_FLASHCARD,
        ExerciseType.SELF_GRADED,
    )


def test_definition_reverse_flashcard_answer(
    definition_db,
):
    session = Session(
        definition_db, "u1", "en", "en",
    )
    # Keep generating until we get a reverse flashcard
    for _ in range(100):
        ex = session.next_exercise()
        if (
            ex is not None
            and ex.exercise_type
            == ExerciseType.REVERSE_FLASHCARD
        ):
            result = session.answer(ex.word.word_from)
            assert result.correct is True
            return
    pytest.skip("Did not get a reverse flashcard exercise")


def test_definition_self_graded_answer(definition_db):
    session = Session(
        definition_db, "u1", "en", "en",
    )
    for _ in range(100):
        ex = session.next_exercise()
        if (
            ex is not None
            and ex.exercise_type
            == ExerciseType.SELF_GRADED
        ):
            result = session.answer(quality=4)
            assert result.correct is True
            return
    pytest.skip("Did not get a self-graded exercise")


def test_definition_self_graded_updates_progress(
    definition_db,
):
    session = Session(
        definition_db, "u1", "en", "en",
    )
    for _ in range(100):
        ex = session.next_exercise()
        if (
            ex is not None
            and ex.exercise_type
            == ExerciseType.SELF_GRADED
        ):
            word_id = ex.word.id
            session.answer(quality=4)
            progress = definition_db.get_progress(
                "u1", word_id,
            )
            assert progress is not None
            assert progress.repetitions == 1
            return
    pytest.skip("Did not get a self-graded exercise")
