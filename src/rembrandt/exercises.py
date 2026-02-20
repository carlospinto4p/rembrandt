"""Exercise generation and answer evaluation."""

import random

from rembrandt.models import (
    AnswerResult,
    Exercise,
    ExerciseType,
    LearningMode,
    Word,
    learning_mode,
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


def generate_reverse_flashcard(word: Word) -> Exercise:
    """Create a reverse flashcard exercise.

    Shows the definition/translation; the user types the word.

    :param word: The word to test.
    :return: A reverse-flashcard `Exercise`.
    """
    return Exercise(
        word=word,
        exercise_type=ExerciseType.REVERSE_FLASHCARD,
    )


def generate_self_graded(word: Word) -> Exercise:
    """Create a self-graded flashcard exercise.

    The user sees the word, mentally recalls the definition,
    then reveals it and self-assesses with a quality score.

    :param word: The word to test.
    :return: A self-graded `Exercise`.
    """
    return Exercise(
        word=word,
        exercise_type=ExerciseType.SELF_GRADED,
    )


def generate_exercise(
    word: Word,
    all_words: list[Word],
) -> Exercise:
    """Generate an exercise appropriate for the word's mode.

    **Translation mode** (`language_from != language_to`):
    50/50 flashcard vs. multiple choice. Falls back to
    flashcard when fewer than 2 words are available.

    **Definition mode** (`language_from == language_to`):
    40% multiple choice, 30% reverse flashcard, 30%
    self-graded. Falls back to reverse flashcard when fewer
    than 2 words are available. Never uses regular flashcard
    (typing exact definitions is bad UX).

    :param word: The word to test.
    :param all_words: Pool of words for multiple-choice
        distractors.
    :return: A generated `Exercise`.
    """
    mode = learning_mode(word)

    if mode == LearningMode.TRANSLATION:
        if len(all_words) < 2:
            return generate_flashcard(word)
        if random.choice([True, False]):
            return generate_flashcard(word)
        return generate_multiple_choice(word, all_words)

    # Definition mode
    if len(all_words) < 2:
        return generate_reverse_flashcard(word)

    roll = random.random()
    if roll < 0.4:
        return generate_multiple_choice(word, all_words)
    if roll < 0.7:
        return generate_reverse_flashcard(word)
    return generate_self_graded(word)


def evaluate_answer(
    exercise: Exercise,
    answer_text: str = "",
    quality: int | None = None,
) -> AnswerResult:
    """Evaluate a user's answer against the expected value.

    Comparison is case-insensitive and strips whitespace.

    For `REVERSE_FLASHCARD` exercises the expected answer is
    `word_from` (the term) instead of `word_to`.

    For `SELF_GRADED` exercises the `quality` parameter (0-5)
    is required; `correct` is `True` when `quality >= 3`.

    :param exercise: The exercise being answered.
    :param answer_text: The user's answer text (ignored for
        self-graded exercises).
    :param quality: Self-assessment score 0-5 (required for
        `SELF_GRADED`, ignored otherwise).
    :return: An `AnswerResult` indicating correctness.
    :raises ValueError: If `quality` is missing or out of
        range for a `SELF_GRADED` exercise.
    """
    etype = exercise.exercise_type

    if etype == ExerciseType.SELF_GRADED:
        if quality is None:
            raise ValueError(
                "quality is required for SELF_GRADED "
                "exercises"
            )
        if not 0 <= quality <= 5:
            raise ValueError(
                f"quality must be 0-5, got {quality}"
            )
        expected = exercise.word.word_to
        return AnswerResult(
            correct=quality >= 3,
            expected=expected,
            given=str(quality),
            word=exercise.word,
        )

    if etype == ExerciseType.REVERSE_FLASHCARD:
        expected = exercise.word.word_from
    else:
        expected = exercise.word.word_to

    given = answer_text.strip()
    correct = given.lower() == expected.lower()

    return AnswerResult(
        correct=correct,
        expected=expected,
        given=given,
        word=exercise.word,
    )
