"""Tests for rembrandt.session."""

import json

import pytest

from datetime import datetime

from rembrandt.db import Database
from rembrandt.models import (
    ExerciseType,
    SessionMode,
    UserProgress,
    Word,
)
from rembrandt.session import Session, quick_session


@pytest.fixture
def session_db(tmp_path):
    database = Database(tmp_path / "test.db")
    database.add_words([
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
    ])
    yield database
    database.close()


@pytest.fixture
def session(session_db):
    return Session(
        session_db, user_id="u1",
        language_from="en", language_to="es",
    )


@pytest.fixture
def definition_db(tmp_path):
    database = Database(tmp_path / "def.db")
    database.add_words([
        Word(
            language_from="en", language_to="en",
            word_from="ephemeral",
            word_to="lasting for a very short time",
        ),
        Word(
            language_from="en", language_to="en",
            word_from="ubiquitous",
            word_to="present everywhere",
        ),
        Word(
            language_from="en", language_to="en",
            word_from="candid",
            word_to="truthful and straightforward",
        ),
        Word(
            language_from="en", language_to="en",
            word_from="pragmatic",
            word_to="dealing with things practically",
        ),
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
        ExerciseType.CLOZE,
        ExerciseType.TRANSLATION_CLOZE,
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


# --- Session Stats Tests ---


def test_summary_initial(session):
    stats = session.summary()
    assert stats.total == 0
    assert stats.correct == 0
    assert stats.incorrect == 0
    assert stats.streak == 0
    assert stats.best_streak == 0
    assert stats.accuracy_pct == 0.0


def test_summary_after_correct(session):
    ex = session.next_exercise()
    assert ex is not None
    session.answer(ex.word.word_to)
    stats = session.summary()
    assert stats.total == 1
    assert stats.correct == 1
    assert stats.incorrect == 0
    assert stats.streak == 1
    assert stats.best_streak == 1
    assert stats.accuracy_pct == 100.0


def test_summary_after_incorrect(session):
    ex = session.next_exercise()
    assert ex is not None
    session.answer("wrong_answer_xyz")
    stats = session.summary()
    assert stats.total == 1
    assert stats.correct == 0
    assert stats.incorrect == 1
    assert stats.streak == 0


def test_summary_streak_resets(session):
    # correct
    ex = session.next_exercise()
    session.answer(ex.word.word_to)
    # correct
    ex = session.next_exercise()
    session.answer(ex.word.word_to)
    # incorrect — resets streak
    ex = session.next_exercise()
    session.answer("wrong_answer_xyz")

    stats = session.summary()
    assert stats.streak == 0
    assert stats.best_streak == 2
    assert stats.total == 3
    assert stats.correct == 2
    assert stats.incorrect == 1


def test_summary_accuracy_pct(session):
    ex = session.next_exercise()
    session.answer(ex.word.word_to)
    ex = session.next_exercise()
    session.answer("wrong_answer_xyz")
    stats = session.summary()
    assert stats.accuracy_pct == 50.0


# --- Hint Tests ---


def test_hint_returns_first_letter_and_length(session):
    ex = session.next_exercise()
    assert ex is not None
    h = session.hint()
    expected = ex.word.word_to
    if ex.expected_answer:
        expected = ex.expected_answer
    assert h.first_letter == expected[0]
    assert h.word_length == len(expected)


def test_hint_pattern_format(session):
    ex = session.next_exercise()
    assert ex is not None
    h = session.hint()
    assert h.pattern[0] == h.first_letter
    assert h.pattern.count("_") == h.word_length - 1
    assert len(h.pattern) == h.word_length


def test_hint_without_exercise_raises(session):
    with pytest.raises(RuntimeError, match="No active exercise"):
        session.hint()


def test_hint_does_not_consume_exercise(session):
    ex = session.next_exercise()
    assert ex is not None
    session.hint()
    # Can still answer after getting a hint
    result = session.answer(ex.word.word_to)
    assert result is not None


# --- Skip Tests ---


def test_skip_returns_exercise(session):
    ex = session.next_exercise()
    assert ex is not None
    skipped = session.skip()
    assert skipped is ex


def test_skip_does_not_affect_progress(session):
    ex = session.next_exercise()
    assert ex is not None
    word_id = ex.word.id
    session.skip()
    assert session.db.get_progress("u1", word_id) is None


def test_skip_does_not_affect_stats(session):
    ex = session.next_exercise()
    assert ex is not None
    session.skip()
    stats = session.summary()
    assert stats.total == 0
    assert stats.correct == 0
    assert stats.incorrect == 0


def test_skip_without_exercise_raises(session):
    with pytest.raises(RuntimeError, match="No active exercise"):
        session.skip()


def test_skip_allows_next_exercise(session):
    ex1 = session.next_exercise()
    assert ex1 is not None
    session.skip()
    ex2 = session.next_exercise()
    assert ex2 is not None


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


# --- quick_session Tests ---

_SAMPLE_WORDS = [
    {"word": "cat", "definition": "gato"},
    {"word": "dog", "definition": "perro"},
    {"word": "house", "definition": "casa"},
    {"word": "book", "definition": "libro"},
    {"word": "tree", "definition": "árbol"},
]


def test_quick_session_from_json(tmp_path):
    vocab_file = tmp_path / "words.json"
    vocab_file.write_text(
        json.dumps(_SAMPLE_WORDS), encoding="utf-8",
    )
    s = quick_session(
        vocab_file,
        language_from="en",
        language_to="es",
    )
    words = s.db.get_words("en", "es")
    assert len(words) == 5
    assert isinstance(s, Session)
    s.db.close()


def test_quick_session_from_list(tmp_path):
    s = quick_session(
        _SAMPLE_WORDS,
        db_path=tmp_path / "inline.db",
        language_from="en",
        language_to="es",
    )
    words = s.db.get_words("en", "es")
    assert len(words) == 5
    assert isinstance(s, Session)
    s.db.close()


def test_quick_session_skips_reload(tmp_path):
    vocab_file = tmp_path / "words.json"
    vocab_file.write_text(
        json.dumps(_SAMPLE_WORDS), encoding="utf-8",
    )
    db_path = tmp_path / "shared.db"

    s1 = quick_session(
        vocab_file,
        db_path=db_path,
        language_from="en",
        language_to="es",
    )
    s1.db.close()

    s2 = quick_session(
        vocab_file,
        db_path=db_path,
        language_from="en",
        language_to="es",
    )
    words = s2.db.get_words("en", "es")
    assert len(words) == 5
    s2.db.close()


def test_quick_session_limit(tmp_path):
    vocab_file = tmp_path / "words.json"
    vocab_file.write_text(
        json.dumps(_SAMPLE_WORDS), encoding="utf-8",
    )
    s = quick_session(
        vocab_file,
        language_from="en",
        language_to="es",
        limit=3,
    )
    words = s.db.get_words("en", "es")
    assert len(words) == 3
    s.db.close()


# --- Session Mode Tests ---


def test_session_learn_new_mode(session_db):
    all_words = session_db.get_words("en", "es")
    due_word = all_words[0]
    session_db.upsert_progress(UserProgress(
        user_id="u1",
        word_id=due_word.id,
        next_review=datetime(2020, 1, 1),
    ))

    s = Session(
        session_db, "u1", "en", "es",
        mode=SessionMode.LEARN_NEW,
    )
    ex = s.next_exercise()
    assert ex is not None
    assert ex.word.id != due_word.id


def test_session_review_due_mode(session_db):
    all_words = session_db.get_words("en", "es")
    due_word = all_words[0]
    session_db.upsert_progress(UserProgress(
        user_id="u1",
        word_id=due_word.id,
        next_review=datetime(2020, 1, 1),
    ))

    s = Session(
        session_db, "u1", "en", "es",
        mode=SessionMode.REVIEW_DUE,
    )
    ex = s.next_exercise()
    assert ex is not None
    assert ex.word.id == due_word.id


def test_session_word_ids_filter(session_db):
    all_words = session_db.get_words("en", "es")
    subset = [all_words[0].id, all_words[1].id]

    s = Session(
        session_db, "u1", "en", "es",
        word_ids=subset,
    )
    seen_ids = set()
    for _ in range(10):
        ex = s.next_exercise()
        if ex is None:
            break
        seen_ids.add(ex.word.id)
        s.answer(ex.word.word_to)
    assert seen_ids <= set(subset)


def test_quick_session_list_requires_db_path():
    with pytest.raises(ValueError, match="db_path is required"):
        quick_session(
            _SAMPLE_WORDS,
            language_from="en",
            language_to="es",
        )


# --- Answer History Recording Tests ---


def test_answer_records_history(session):
    ex = session.next_exercise()
    assert ex is not None
    session.answer(ex.word.word_to)
    history = session.db.get_answer_history("u1")
    assert len(history) == 1
    assert history[0].word_id == ex.word.id
    assert history[0].correct is True


def test_answer_incorrect_records_history(session):
    ex = session.next_exercise()
    assert ex is not None
    session.answer("wrong_answer_xyz")
    history = session.db.get_answer_history("u1")
    assert len(history) == 1
    assert history[0].correct is False


def test_answer_records_exercise_type(session):
    ex = session.next_exercise()
    assert ex is not None
    session.answer(ex.word.word_to)
    history = session.db.get_answer_history("u1")
    assert history[0].exercise_type == ex.exercise_type.value


def test_answer_records_quality(session):
    ex = session.next_exercise()
    assert ex is not None
    session.answer(ex.word.word_to)
    history = session.db.get_answer_history("u1")
    assert history[0].quality == 5  # correct -> quality 5


def test_multiple_answers_recorded(session):
    for _ in range(3):
        ex = session.next_exercise()
        if ex is None:
            break
        session.answer(ex.word.word_to)
    history = session.db.get_answer_history("u1")
    assert len(history) == 3


def test_quick_session_custom_keys(tmp_path):
    custom_words = [
        {"term": "cat", "meaning": "gato"},
        {"term": "dog", "meaning": "perro"},
    ]
    vocab_file = tmp_path / "custom.json"
    vocab_file.write_text(
        json.dumps(custom_words), encoding="utf-8",
    )
    s = quick_session(
        vocab_file,
        language_from="en",
        language_to="es",
        word_key="term",
        definition_key="meaning",
    )
    words = s.db.get_words("en", "es")
    assert len(words) == 2
    assert words[0].word_from == "cat"
    s.db.close()
