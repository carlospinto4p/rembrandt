"""Tests for rembrandt.exercises."""

from rembrandt.exercises import (
    evaluate_answer,
    generate_exercise,
    generate_flashcard,
    generate_multiple_choice,
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


# --- Random Exercise Tests ---


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
