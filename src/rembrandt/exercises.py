"""Exercise generation and answer evaluation."""

from __future__ import annotations

import random

from rembrandt.models import (
    AnswerResult,
    Exercise,
    ExerciseType,
    Word,
)


def generate_flashcard(word: Word) -> Exercise:
    """Create a simple flashcard exercise.

    :param word: The word to test.
    :return: A flashcard `Exercise`.
    """
    return Exercise(
        word=word,
        exercise_type=ExerciseType.FLASHCARD,
    )


def generate_multiple_choice(
    word: Word,
    all_words: list[Word],
    num_options: int = 4,
) -> Exercise:
    """Create a multiple-choice exercise with distractors.

    :param word: The word to test (correct answer).
    :param all_words: Pool of words to draw distractors from.
    :param num_options: Total number of options including the
        correct answer.
    :return: A multiple-choice `Exercise`.
    """
    distractors = [
        w for w in all_words
        if w.id != word.id
    ]
    num_distractors = min(
        num_options - 1, len(distractors)
    )
    chosen = random.sample(distractors, num_distractors)
    options = [word.word_to] + [w.word_to for w in chosen]
    random.shuffle(options)

    return Exercise(
        word=word,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=options,
    )


def generate_exercise(
    word: Word,
    all_words: list[Word],
) -> Exercise:
    """Randomly generate a flashcard or multiple-choice exercise.

    Falls back to flashcard when there aren't enough words for
    multiple choice (fewer than 2 total words).

    :param word: The word to test.
    :param all_words: Pool of words for multiple-choice
        distractors.
    :return: A generated `Exercise`.
    """
    if len(all_words) < 2:
        return generate_flashcard(word)

    if random.choice([True, False]):
        return generate_flashcard(word)
    return generate_multiple_choice(word, all_words)


def evaluate_answer(
    exercise: Exercise,
    answer_text: str,
) -> AnswerResult:
    """Evaluate a user's answer against the expected translation.

    Comparison is case-insensitive and strips whitespace.

    :param exercise: The exercise being answered.
    :param answer_text: The user's answer text.
    :return: An `AnswerResult` indicating correctness.
    """
    expected = exercise.word.word_to
    given = answer_text.strip()
    correct = given.lower() == expected.lower()

    return AnswerResult(
        correct=correct,
        expected=expected,
        given=given,
        word=exercise.word,
    )
