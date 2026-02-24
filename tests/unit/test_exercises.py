"""Tests for rembrandt.exercises."""

import pytest

from rembrandt.exercises import (
    evaluate_answer,
    generate_exercise,
    generate_flashcard,
    generate_gender_match,
    generate_multiple_choice,
    generate_reverse_flashcard,
    generate_self_graded,
)
from rembrandt.models import Exercise, ExerciseType, Word


# --- Fixtures ---


@pytest.fixture
def sample_words():
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


@pytest.fixture
def definition_words():
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


def test_generate_flashcard(sample_words):
    ex = generate_flashcard(sample_words[0])
    assert ex.exercise_type == ExerciseType.FLASHCARD
    assert ex.word.word_from == "cat"
    assert ex.options == []


# --- Multiple Choice Tests ---


def test_generate_multiple_choice_has_correct_answer(
    sample_words,
):
    ex = generate_multiple_choice(
        sample_words[0], sample_words,
    )
    assert "gato" in ex.options
    assert ex.exercise_type == ExerciseType.MULTIPLE_CHOICE


def test_generate_multiple_choice_option_count(sample_words):
    ex = generate_multiple_choice(
        sample_words[0], sample_words, num_options=4,
    )
    assert len(ex.options) == 4


def test_generate_multiple_choice_fewer_words(sample_words):
    words = sample_words[:2]
    ex = generate_multiple_choice(
        words[0], words, num_options=4
    )
    assert len(ex.options) == 2
    assert "gato" in ex.options


# --- Reverse Flashcard Tests ---


def test_generate_reverse_flashcard(definition_words):
    ex = generate_reverse_flashcard(definition_words[0])
    assert ex.exercise_type == ExerciseType.REVERSE_FLASHCARD
    assert ex.word.word_from == "ephemeral"
    assert ex.options == []


# --- Self-Graded Tests ---


def test_generate_self_graded(definition_words):
    ex = generate_self_graded(definition_words[0])
    assert ex.exercise_type == ExerciseType.SELF_GRADED
    assert ex.word.word_from == "ephemeral"
    assert ex.options == []


# --- Random Exercise Tests (Translation Mode) ---


def test_generate_exercise_single_word(sample_words):
    words = sample_words[:1]
    ex = generate_exercise(words[0], words)
    assert ex.exercise_type == ExerciseType.FLASHCARD


def test_generate_exercise_returns_valid_type(sample_words):
    ex = generate_exercise(sample_words[0], sample_words)
    assert ex.exercise_type in (
        ExerciseType.FLASHCARD,
        ExerciseType.MULTIPLE_CHOICE,
    )


# --- Random Exercise Tests (Definition Mode) ---


def test_generate_exercise_definition_mode_single_word(
    definition_words,
):
    words = definition_words[:1]
    ex = generate_exercise(words[0], words)
    assert ex.exercise_type == ExerciseType.REVERSE_FLASHCARD


def test_generate_exercise_definition_mode_returns_valid_type(
    definition_words,
):
    ex = generate_exercise(
        definition_words[0], definition_words,
    )
    assert ex.exercise_type in (
        ExerciseType.MULTIPLE_CHOICE,
        ExerciseType.REVERSE_FLASHCARD,
        ExerciseType.SELF_GRADED,
    )


def test_generate_exercise_definition_mode_never_flashcard(
    definition_words,
):
    types = set()
    for _ in range(200):
        ex = generate_exercise(
            definition_words[0], definition_words,
        )
        types.add(ex.exercise_type)
    assert ExerciseType.FLASHCARD not in types


# --- Answer Evaluation Tests ---


def test_evaluate_answer_correct(sample_words):
    ex = generate_flashcard(sample_words[0])
    result = evaluate_answer(ex, "gato")
    assert result.correct is True
    assert result.expected == "gato"
    assert result.given == "gato"


def test_evaluate_answer_correct_case_insensitive(
    sample_words,
):
    ex = generate_flashcard(sample_words[0])
    result = evaluate_answer(ex, "Gato")
    assert result.correct is True


def test_evaluate_answer_correct_with_whitespace(
    sample_words,
):
    ex = generate_flashcard(sample_words[0])
    result = evaluate_answer(ex, "  gato  ")
    assert result.correct is True


def test_evaluate_answer_incorrect(sample_words):
    ex = generate_flashcard(sample_words[0])
    result = evaluate_answer(ex, "perro")
    assert result.correct is False
    assert result.expected == "gato"
    assert result.given == "perro"


# --- Reverse Flashcard Evaluation Tests ---


def test_evaluate_reverse_flashcard_correct(definition_words):
    ex = generate_reverse_flashcard(definition_words[0])
    result = evaluate_answer(ex, "ephemeral")
    assert result.correct is True
    assert result.expected == "ephemeral"


def test_evaluate_reverse_flashcard_incorrect(
    definition_words,
):
    ex = generate_reverse_flashcard(definition_words[0])
    result = evaluate_answer(ex, "ubiquitous")
    assert result.correct is False
    assert result.expected == "ephemeral"


def test_evaluate_reverse_flashcard_case_insensitive(
    definition_words,
):
    ex = generate_reverse_flashcard(definition_words[0])
    result = evaluate_answer(ex, "Ephemeral")
    assert result.correct is True


# --- Self-Graded Evaluation Tests ---


def test_evaluate_self_graded_quality_high(definition_words):
    ex = generate_self_graded(definition_words[0])
    result = evaluate_answer(ex, quality=5)
    assert result.correct is True
    assert result.expected == "lasting for a very short time"
    assert result.given == "5"


def test_evaluate_self_graded_quality_threshold(
    definition_words,
):
    ex = generate_self_graded(definition_words[0])
    result = evaluate_answer(ex, quality=3)
    assert result.correct is True


def test_evaluate_self_graded_quality_low(definition_words):
    ex = generate_self_graded(definition_words[0])
    result = evaluate_answer(ex, quality=2)
    assert result.correct is False


def test_evaluate_self_graded_missing_quality(
    definition_words,
):
    ex = generate_self_graded(definition_words[0])
    with pytest.raises(ValueError, match="quality is required"):
        evaluate_answer(ex, "anything")


def test_evaluate_self_graded_invalid_quality(
    definition_words,
):
    ex = generate_self_graded(definition_words[0])
    with pytest.raises(ValueError, match="quality must be 0-5"):
        evaluate_answer(ex, quality=6)


# --- Flexible Answer Matching Tests ---


def test_evaluate_answer_strips_parenthetical():
    word = Word(
        id=1,
        language_from="es",
        language_to="en",
        word_from="ser",
        word_to="to be (essentially or identified as)",
    )
    ex = generate_flashcard(word)
    result = evaluate_answer(ex, "to be")
    assert result.correct is True


def test_evaluate_answer_strips_brackets():
    word = Word(
        id=1,
        language_from="es",
        language_to="en",
        word_from="haber",
        word_to=(
            "have; forms the perfect aspect "
            "[+masculine singular past participle]"
        ),
    )
    ex = generate_flashcard(word)
    result = evaluate_answer(ex, "have")
    assert result.correct is True


def test_evaluate_answer_semicolon_segment():
    word = Word(
        id=1,
        language_from="es",
        language_to="en",
        word_from="tener",
        word_to="to have; to possess",
    )
    ex = generate_flashcard(word)
    result = evaluate_answer(ex, "to possess")
    assert result.correct is True


def test_evaluate_answer_to_prefix():
    word = Word(
        id=1,
        language_from="es",
        language_to="en",
        word_from="ser",
        word_to="to be",
    )
    ex = generate_flashcard(word)
    # "be" matches "to be"
    assert evaluate_answer(ex, "be").correct is True

    word2 = Word(
        id=2,
        language_from="es",
        language_to="en",
        word_from="tener",
        word_to="have",
    )
    ex2 = generate_flashcard(word2)
    # "to have" matches "have"
    assert evaluate_answer(ex2, "to have").correct is True


def test_evaluate_multiple_choice_by_number():
    word = Word(
        id=1,
        language_from="en",
        language_to="es",
        word_from="cat",
        word_to="gato",
    )
    ex = Exercise(
        word=word,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=["perro", "gato", "casa", "libro"],
    )
    result = evaluate_answer(ex, "2")
    assert result.correct is True
    assert result.given == "gato"


def test_evaluate_multiple_choice_by_number_wrong():
    word = Word(
        id=1,
        language_from="en",
        language_to="es",
        word_from="cat",
        word_to="gato",
    )
    ex = Exercise(
        word=word,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=["perro", "gato", "casa", "libro"],
    )
    result = evaluate_answer(ex, "1")
    assert result.correct is False
    assert result.given == "perro"


def test_evaluate_multiple_choice_out_of_range():
    word = Word(
        id=1,
        language_from="en",
        language_to="es",
        word_from="cat",
        word_to="gato",
    )
    ex = Exercise(
        word=word,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=["perro", "gato", "casa", "libro"],
    )
    result = evaluate_answer(ex, "9")
    assert result.correct is False
    assert result.given == "9"


def test_evaluate_multiple_choice_by_text_still_works():
    word = Word(
        id=1,
        language_from="en",
        language_to="es",
        word_from="cat",
        word_to="gato",
    )
    ex = Exercise(
        word=word,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=["perro", "gato", "casa", "libro"],
    )
    result = evaluate_answer(ex, "gato")
    assert result.correct is True


# --- Gender Match Tests ---


@pytest.fixture
def masculine_word():
    return Word(
        id=10,
        language_from="en",
        language_to="es",
        word_from="book",
        word_to="libro",
        gender="m",
    )


@pytest.fixture
def feminine_word():
    return Word(
        id=11,
        language_from="en",
        language_to="es",
        word_from="house",
        word_to="casa",
        gender="f",
    )


def test_generate_gender_match_masculine(masculine_word):
    ex = generate_gender_match(masculine_word)
    assert ex.exercise_type == ExerciseType.GENDER_MATCH
    assert ex.expected_answer == "el"
    assert ex.prompt == "___ libro"
    assert ex.options == ["el", "la"]


def test_generate_gender_match_feminine(feminine_word):
    ex = generate_gender_match(feminine_word)
    assert ex.exercise_type == ExerciseType.GENDER_MATCH
    assert ex.expected_answer == "la"
    assert ex.prompt == "___ casa"


def test_generate_gender_match_no_gender_raises():
    word = Word(
        id=1,
        language_from="en",
        language_to="es",
        word_from="speak",
        word_to="hablar",
    )
    with pytest.raises(
        ValueError, match="gender_match requires"
    ):
        generate_gender_match(word)


def test_evaluate_gender_match_correct(feminine_word):
    ex = generate_gender_match(feminine_word)
    result = evaluate_answer(ex, "la")
    assert result.correct is True
    assert result.expected == "la"


def test_evaluate_gender_match_incorrect(feminine_word):
    ex = generate_gender_match(feminine_word)
    result = evaluate_answer(ex, "el")
    assert result.correct is False
    assert result.expected == "la"


def test_evaluate_gender_match_by_number(feminine_word):
    ex = generate_gender_match(feminine_word)
    # options are ["el", "la"], so "2" → "la"
    result = evaluate_answer(ex, "2")
    assert result.correct is True
    assert result.given == "la"


# --- Accent Tolerance Tests ---


def test_evaluate_accent_tolerant():
    word = Word(
        id=1,
        language_from="en",
        language_to="es",
        word_from="speak",
        word_to="habló",
    )
    ex = generate_flashcard(word)
    result = evaluate_answer(ex, "hablo")
    assert result.correct is True


# --- Pool-based Exercise Selection Tests ---


def test_generate_exercise_includes_gender_match():
    words = [
        Word(
            id=i,
            language_from="en",
            language_to="es",
            word_from=w[0],
            word_to=w[1],
            gender=w[2],
        )
        for i, w in enumerate(
            [
                ("book", "libro", "m"),
                ("house", "casa", "f"),
                ("water", "agua", "f"),
                ("cat", "gato", "m"),
            ],
            start=1,
        )
    ]
    types = set()
    for _ in range(200):
        ex = generate_exercise(words[0], words)
        types.add(ex.exercise_type)
    assert ExerciseType.GENDER_MATCH in types


def test_generate_exercise_returns_valid_type_with_gender():
    words = [
        Word(
            id=1,
            language_from="en",
            language_to="es",
            word_from="book",
            word_to="libro",
            gender="m",
        ),
        Word(
            id=2,
            language_from="en",
            language_to="es",
            word_from="house",
            word_to="casa",
            gender="f",
        ),
    ]
    ex = generate_exercise(words[0], words)
    assert ex.exercise_type in (
        ExerciseType.FLASHCARD,
        ExerciseType.MULTIPLE_CHOICE,
        ExerciseType.GENDER_MATCH,
    )
