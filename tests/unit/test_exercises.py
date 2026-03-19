"""Tests for rembrandt.exercises."""

import pytest

from rembrandt.exercises import (
    evaluate_answer,
    generate_exercise,
    generate_flashcard,
    generate_multiple_choice,
    generate_self_graded,
)
from rembrandt.models import (
    Concept,
    Exercise,
    ExerciseType,
)


# --- Flashcard Tests ---


def test_generate_flashcard(short_concepts):
    ex = generate_flashcard(short_concepts[0])
    assert ex.exercise_type == ExerciseType.FLASHCARD
    assert ex.concept.front == "cat"
    assert ex.options == []


# --- Multiple Choice Tests ---


def test_generate_multiple_choice_has_correct_answer(
    short_concepts,
):
    ex = generate_multiple_choice(
        short_concepts[0], short_concepts,
    )
    assert "gato" in ex.options
    assert (
        ex.exercise_type
        == ExerciseType.MULTIPLE_CHOICE
    )


def test_generate_multiple_choice_option_count(
    short_concepts,
):
    ex = generate_multiple_choice(
        short_concepts[0], short_concepts,
        num_options=4,
    )
    assert len(ex.options) == 4


def test_generate_multiple_choice_fewer_concepts(
    short_concepts,
):
    concepts = short_concepts[:2]
    ex = generate_multiple_choice(
        concepts[0], concepts, num_options=4,
    )
    assert len(ex.options) == 2
    assert "gato" in ex.options


# --- Self-Graded Tests ---


def test_generate_self_graded(sample_concepts):
    ex = generate_self_graded(sample_concepts[0])
    assert (
        ex.exercise_type == ExerciseType.SELF_GRADED
    )
    assert (
        ex.concept.front == "What is a p-value?"
    )
    assert ex.options == []


# --- Random Exercise Tests ---


def test_generate_exercise_single_concept(
    short_concepts,
):
    concepts = short_concepts[:1]
    ex = generate_exercise(concepts[0], concepts)
    assert ex.exercise_type in (
        ExerciseType.FLASHCARD,
        ExerciseType.SELF_GRADED,
    )


def test_generate_exercise_returns_valid_type(
    short_concepts,
):
    ex = generate_exercise(
        short_concepts[0], short_concepts,
    )
    assert ex.exercise_type in (
        ExerciseType.FLASHCARD,
        ExerciseType.MULTIPLE_CHOICE,
        ExerciseType.SELF_GRADED,
    )


def test_generate_exercise_all_types(
    short_concepts,
):
    types = set()
    for _ in range(500):
        ex = generate_exercise(
            short_concepts[0], short_concepts,
        )
        types.add(ex.exercise_type)
    assert types == {
        ExerciseType.FLASHCARD,
        ExerciseType.MULTIPLE_CHOICE,
        ExerciseType.SELF_GRADED,
    }


# --- Answer Evaluation Tests ---


def test_evaluate_answer_correct(short_concepts):
    ex = generate_flashcard(short_concepts[0])
    result = evaluate_answer(ex, "gato")
    assert result.correct is True
    assert result.expected == "gato"
    assert result.given == "gato"


def test_evaluate_answer_correct_case_insensitive(
    short_concepts,
):
    ex = generate_flashcard(short_concepts[0])
    result = evaluate_answer(ex, "Gato")
    assert result.correct is True


def test_evaluate_answer_correct_with_whitespace(
    short_concepts,
):
    ex = generate_flashcard(short_concepts[0])
    result = evaluate_answer(ex, "  gato  ")
    assert result.correct is True


def test_evaluate_answer_incorrect(short_concepts):
    ex = generate_flashcard(short_concepts[0])
    result = evaluate_answer(ex, "perro")
    assert result.correct is False
    assert result.expected == "gato"
    assert result.given == "perro"


# --- Self-Graded Evaluation Tests ---


def test_evaluate_self_graded_quality_high(
    sample_concepts,
):
    ex = generate_self_graded(sample_concepts[0])
    result = evaluate_answer(ex, quality=5)
    assert result.correct is True
    assert result.given == "5"


def test_evaluate_self_graded_quality_threshold(
    sample_concepts,
):
    ex = generate_self_graded(sample_concepts[0])
    result = evaluate_answer(ex, quality=3)
    assert result.correct is True


def test_evaluate_self_graded_quality_low(
    sample_concepts,
):
    ex = generate_self_graded(sample_concepts[0])
    result = evaluate_answer(ex, quality=2)
    assert result.correct is False


def test_evaluate_self_graded_missing_quality(
    sample_concepts,
):
    ex = generate_self_graded(sample_concepts[0])
    with pytest.raises(
        ValueError, match="quality is required",
    ):
        evaluate_answer(ex, "anything")


def test_evaluate_self_graded_invalid_quality(
    sample_concepts,
):
    ex = generate_self_graded(sample_concepts[0])
    with pytest.raises(
        ValueError, match="quality must be 0-5",
    ):
        evaluate_answer(ex, quality=6)


# --- Flexible Answer Matching Tests ---


def test_evaluate_answer_strips_parenthetical():
    concept = Concept(
        id=1,
        front="to be",
        back="ser (essentially or identified as)",
    )
    ex = generate_flashcard(concept)
    result = evaluate_answer(ex, "ser")
    assert result.correct is True


def test_evaluate_answer_strips_brackets():
    concept = Concept(
        id=1,
        front="have",
        back=(
            "have; forms the perfect aspect "
            "[+masculine singular past participle]"
        ),
    )
    ex = generate_flashcard(concept)
    result = evaluate_answer(ex, "have")
    assert result.correct is True


def test_evaluate_answer_semicolon_segment():
    concept = Concept(
        id=1,
        front="to have",
        back="tener; poseer",
    )
    ex = generate_flashcard(concept)
    result = evaluate_answer(ex, "poseer")
    assert result.correct is True


def test_evaluate_answer_comma_segment():
    concept = Concept(
        id=1,
        front="to say",
        back="decir, contar",
    )
    ex = generate_flashcard(concept)
    assert evaluate_answer(
        ex, "decir",
    ).correct is True
    assert evaluate_answer(
        ex, "contar",
    ).correct is True
    assert evaluate_answer(
        ex, "decir, contar",
    ).correct is True


def test_evaluate_answer_to_prefix():
    concept = Concept(
        id=1, front="ser", back="to be",
    )
    ex = generate_flashcard(concept)
    assert evaluate_answer(
        ex, "be",
    ).correct is True

    concept2 = Concept(
        id=2, front="tener", back="have",
    )
    ex2 = generate_flashcard(concept2)
    assert evaluate_answer(
        ex2, "to have",
    ).correct is True


def test_evaluate_multiple_choice_by_number():
    concept = Concept(
        id=1, front="cat", back="gato",
    )
    ex = Exercise(
        concept=concept,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=["perro", "gato", "casa", "libro"],
    )
    result = evaluate_answer(ex, "2")
    assert result.correct is True
    assert result.given == "gato"


def test_evaluate_multiple_choice_by_number_wrong():
    concept = Concept(
        id=1, front="cat", back="gato",
    )
    ex = Exercise(
        concept=concept,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=["perro", "gato", "casa", "libro"],
    )
    result = evaluate_answer(ex, "1")
    assert result.correct is False
    assert result.given == "perro"


def test_evaluate_multiple_choice_out_of_range():
    concept = Concept(
        id=1, front="cat", back="gato",
    )
    ex = Exercise(
        concept=concept,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=["perro", "gato", "casa", "libro"],
    )
    result = evaluate_answer(ex, "9")
    assert result.correct is False
    assert result.given == "9"


def test_evaluate_multiple_choice_by_text():
    concept = Concept(
        id=1, front="cat", back="gato",
    )
    ex = Exercise(
        concept=concept,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=["perro", "gato", "casa", "libro"],
    )
    result = evaluate_answer(ex, "gato")
    assert result.correct is True


# --- Accent Tolerance Tests ---


def test_evaluate_accent_tolerant():
    concept = Concept(
        id=1, front="speak", back="habló",
    )
    ex = generate_flashcard(concept)
    result = evaluate_answer(ex, "hablo")
    assert result.correct is True


# --- Fuzzy Answer Matching Tests ---


def test_evaluate_answer_fuzzy_single_typo():
    concept = Concept(
        id=1, front="cat", back="gato",
    )
    ex = generate_flashcard(concept)
    result = evaluate_answer(ex, "gat")
    assert result.correct is True
    assert result.near_miss is True


def test_evaluate_answer_fuzzy_long_word():
    concept = Concept(
        id=1,
        front="to understand",
        back="comprender",
    )
    ex = generate_flashcard(concept)
    result = evaluate_answer(ex, "comprendr")
    assert result.correct is True
    assert result.near_miss is True


def test_evaluate_answer_fuzzy_too_far():
    concept = Concept(
        id=1, front="cat", back="gato",
    )
    ex = generate_flashcard(concept)
    result = evaluate_answer(ex, "ga")
    assert result.correct is False
    assert result.near_miss is False


def test_evaluate_answer_exact_not_near_miss():
    concept = Concept(
        id=1, front="cat", back="gato",
    )
    ex = generate_flashcard(concept)
    result = evaluate_answer(ex, "gato")
    assert result.correct is True
    assert result.near_miss is False


def test_evaluate_answer_fuzzy_swapped_letters():
    concept = Concept(
        id=1, front="to speak", back="hablar",
    )
    ex = generate_flashcard(concept)
    result = evaluate_answer(ex, "hablra")
    assert result.correct is True
    assert result.near_miss is True
