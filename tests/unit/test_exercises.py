"""Tests for rembrandt.exercises."""

import pytest

from rembrandt.exercises import (
    evaluate_answer,
    generate_exercise,
    generate_flashcard,
    generate_multiple_choice,
    generate_reverse_flashcard,
    generate_self_graded,
)
from rembrandt.models import ExerciseType, Word


# --- Fixtures ---


def _sample_words():
    return [
        Word(
            id=i,
            language_from="en",
            language_to="es",
            word_from=w[0],
            word_to=w[1],
        )
        for i, w in enumerate(
            [
                ("cat", "gato"),
                ("dog", "perro"),
                ("house", "casa"),
                ("book", "libro"),
                ("water", "agua"),
            ],
            start=1,
        )
    ]


def _definition_words():
    return [
        Word(
            id=i,
            language_from="en",
            language_to="en",
            word_from=w[0],
            word_to=w[1],
        )
        for i, w in enumerate(
            [
                ("ephemeral", "lasting for a very short time"),
                ("ubiquitous", "present everywhere"),
                ("candid", "truthful and straightforward"),
                ("pragmatic", "dealing with things practically"),
                ("verbose", "using more words than needed"),
            ],
            start=1,
        )
    ]


# --- Flashcard Tests ---


def test_generate_flashcard():
    words = _sample_words()
    ex = generate_flashcard(words[0])
    assert ex.exercise_type == ExerciseType.FLASHCARD
    assert ex.word.word_from == "cat"
    assert ex.options == []


# --- Multiple Choice Tests ---


def test_generate_multiple_choice_has_correct_answer():
    words = _sample_words()
    ex = generate_multiple_choice(words[0], words)
    assert "gato" in ex.options
    assert ex.exercise_type == ExerciseType.MULTIPLE_CHOICE


def test_generate_multiple_choice_option_count():
    words = _sample_words()
    ex = generate_multiple_choice(words[0], words, num_options=4)
    assert len(ex.options) == 4


def test_generate_multiple_choice_fewer_words():
    words = _sample_words()[:2]
    ex = generate_multiple_choice(
        words[0], words, num_options=4
    )
    assert len(ex.options) == 2
    assert "gato" in ex.options


# --- Reverse Flashcard Tests ---


def test_generate_reverse_flashcard():
    words = _definition_words()
    ex = generate_reverse_flashcard(words[0])
    assert ex.exercise_type == ExerciseType.REVERSE_FLASHCARD
    assert ex.word.word_from == "ephemeral"
    assert ex.options == []


# --- Self-Graded Tests ---


def test_generate_self_graded():
    words = _definition_words()
    ex = generate_self_graded(words[0])
    assert ex.exercise_type == ExerciseType.SELF_GRADED
    assert ex.word.word_from == "ephemeral"
    assert ex.options == []


# --- Random Exercise Tests (Translation Mode) ---


def test_generate_exercise_single_word():
    words = _sample_words()[:1]
    ex = generate_exercise(words[0], words)
    assert ex.exercise_type == ExerciseType.FLASHCARD


def test_generate_exercise_returns_valid_type():
    words = _sample_words()
    ex = generate_exercise(words[0], words)
    assert ex.exercise_type in (
        ExerciseType.FLASHCARD,
        ExerciseType.MULTIPLE_CHOICE,
    )


# --- Random Exercise Tests (Definition Mode) ---


def test_generate_exercise_definition_mode_single_word():
    words = _definition_words()[:1]
    ex = generate_exercise(words[0], words)
    assert ex.exercise_type == ExerciseType.REVERSE_FLASHCARD


def test_generate_exercise_definition_mode_returns_valid_type():
    words = _definition_words()
    ex = generate_exercise(words[0], words)
    assert ex.exercise_type in (
        ExerciseType.MULTIPLE_CHOICE,
        ExerciseType.REVERSE_FLASHCARD,
        ExerciseType.SELF_GRADED,
    )


def test_generate_exercise_definition_mode_never_flashcard():
    words = _definition_words()
    types = set()
    for _ in range(200):
        ex = generate_exercise(words[0], words)
        types.add(ex.exercise_type)
    assert ExerciseType.FLASHCARD not in types


# --- Answer Evaluation Tests ---


def test_evaluate_answer_correct():
    words = _sample_words()
    ex = generate_flashcard(words[0])
    result = evaluate_answer(ex, "gato")
    assert result.correct is True
    assert result.expected == "gato"
    assert result.given == "gato"


def test_evaluate_answer_correct_case_insensitive():
    words = _sample_words()
    ex = generate_flashcard(words[0])
    result = evaluate_answer(ex, "Gato")
    assert result.correct is True


def test_evaluate_answer_correct_with_whitespace():
    words = _sample_words()
    ex = generate_flashcard(words[0])
    result = evaluate_answer(ex, "  gato  ")
    assert result.correct is True


def test_evaluate_answer_incorrect():
    words = _sample_words()
    ex = generate_flashcard(words[0])
    result = evaluate_answer(ex, "perro")
    assert result.correct is False
    assert result.expected == "gato"
    assert result.given == "perro"


# --- Reverse Flashcard Evaluation Tests ---


def test_evaluate_reverse_flashcard_correct():
    words = _definition_words()
    ex = generate_reverse_flashcard(words[0])
    result = evaluate_answer(ex, "ephemeral")
    assert result.correct is True
    assert result.expected == "ephemeral"


def test_evaluate_reverse_flashcard_incorrect():
    words = _definition_words()
    ex = generate_reverse_flashcard(words[0])
    result = evaluate_answer(ex, "ubiquitous")
    assert result.correct is False
    assert result.expected == "ephemeral"


def test_evaluate_reverse_flashcard_case_insensitive():
    words = _definition_words()
    ex = generate_reverse_flashcard(words[0])
    result = evaluate_answer(ex, "Ephemeral")
    assert result.correct is True


# --- Self-Graded Evaluation Tests ---


def test_evaluate_self_graded_quality_high():
    words = _definition_words()
    ex = generate_self_graded(words[0])
    result = evaluate_answer(ex, quality=5)
    assert result.correct is True
    assert result.expected == "lasting for a very short time"
    assert result.given == "5"


def test_evaluate_self_graded_quality_threshold():
    words = _definition_words()
    ex = generate_self_graded(words[0])
    result = evaluate_answer(ex, quality=3)
    assert result.correct is True


def test_evaluate_self_graded_quality_low():
    words = _definition_words()
    ex = generate_self_graded(words[0])
    result = evaluate_answer(ex, quality=2)
    assert result.correct is False


def test_evaluate_self_graded_missing_quality():
    words = _definition_words()
    ex = generate_self_graded(words[0])
    with pytest.raises(ValueError, match="quality is required"):
        evaluate_answer(ex, "anything")


def test_evaluate_self_graded_invalid_quality():
    words = _definition_words()
    ex = generate_self_graded(words[0])
    with pytest.raises(ValueError, match="quality must be 0-5"):
        evaluate_answer(ex, quality=6)
