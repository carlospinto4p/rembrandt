"""Tests for rembrandt.models."""

from datetime import datetime

import pytest

from rembrandt.models import (
    AnswerResult,
    Exercise,
    ExerciseType,
    UserProgress,
    Word,
)


# --- Word Tests ---


def test_word_creation():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="hello",
        word_to="hola",
    )
    assert word.word_from == "hello"
    assert word.word_to == "hola"
    assert word.id is None


def test_word_with_id():
    word = Word(
        id=1,
        language_from="en",
        language_to="es",
        word_from="cat",
        word_to="gato",
    )
    assert word.id == 1


# --- ExerciseType Tests ---


def test_exercise_type_values():
    assert ExerciseType.FLASHCARD == "flashcard"
    assert ExerciseType.MULTIPLE_CHOICE == "multiple_choice"


# --- Exercise Tests ---


def test_exercise_flashcard():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="dog",
        word_to="perro",
    )
    ex = Exercise(
        word=word,
        exercise_type=ExerciseType.FLASHCARD,
    )
    assert ex.exercise_type == ExerciseType.FLASHCARD
    assert ex.options == []


def test_exercise_multiple_choice():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="dog",
        word_to="perro",
    )
    ex = Exercise(
        word=word,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=["perro", "gato", "casa", "libro"],
    )
    assert len(ex.options) == 4
    assert "perro" in ex.options


# --- AnswerResult Tests ---


def test_answer_result_correct():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="dog",
        word_to="perro",
    )
    result = AnswerResult(
        correct=True,
        expected="perro",
        given="perro",
        word=word,
    )
    assert result.correct is True


def test_answer_result_incorrect():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="dog",
        word_to="perro",
    )
    result = AnswerResult(
        correct=False,
        expected="perro",
        given="gato",
        word=word,
    )
    assert result.correct is False
    assert result.given == "gato"


# --- UserProgress Tests ---


def test_user_progress_defaults():
    progress = UserProgress(user_id="u1", word_id=1)
    assert progress.easiness_factor == 2.5
    assert progress.interval == 0
    assert progress.repetitions == 0
    assert isinstance(progress.next_review, datetime)


def test_user_progress_custom_values():
    dt = datetime(2026, 3, 1, 12, 0, 0)
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        easiness_factor=2.1,
        interval=6,
        repetitions=3,
        next_review=dt,
    )
    assert progress.easiness_factor == 2.1
    assert progress.interval == 6
    assert progress.next_review == dt


def test_user_progress_validates_types():
    with pytest.raises(Exception):
        UserProgress(
            user_id="u1",
            word_id="not_an_int",  # type: ignore[arg-type]
        )
