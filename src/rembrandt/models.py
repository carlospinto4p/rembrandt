"""Pydantic models for vocabulary exercises."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Word(BaseModel):
    """A vocabulary word with its translation.

    :param id: Unique identifier (assigned by the database).
    :param language_from: Source language code (e.g. `"en"`).
    :param language_to: Target language code (e.g. `"es"`).
    :param word_from: Word in the source language.
    :param word_to: Translation in the target language.
    """

    id: int | None = None
    language_from: str
    language_to: str
    word_from: str
    word_to: str


class LearningMode(str, Enum):
    """How a word is being learned.

    :cvar TRANSLATION: Bilingual — source and target languages
        differ (e.g. EN -> ES).
    :cvar DEFINITION: Monolingual — same language, word paired
        with its definition (e.g. EN -> EN).
    """

    TRANSLATION = "translation"
    DEFINITION = "definition"


class ExerciseType(str, Enum):
    """Type of vocabulary exercise."""

    FLASHCARD = "flashcard"
    MULTIPLE_CHOICE = "multiple_choice"
    REVERSE_FLASHCARD = "reverse_flashcard"
    SELF_GRADED = "self_graded"


class Exercise(BaseModel):
    """A generated exercise for a word.

    :param word: The word being tested.
    :param exercise_type: The type of exercise.
    :param options: Answer options (for multiple choice).
    """

    word: Word
    exercise_type: ExerciseType
    options: list[str] = Field(default_factory=list)


class AnswerResult(BaseModel):
    """Result of evaluating a user's answer.

    :param correct: Whether the answer was correct.
    :param expected: The expected answer.
    :param given: The answer the user gave.
    :param word: The word that was tested.
    """

    correct: bool
    expected: str
    given: str
    word: Word


class UserProgress(BaseModel):
    """Spaced-repetition progress for a user-word pair.

    :param user_id: Identifier for the user.
    :param word_id: Identifier for the word.
    :param easiness_factor: SM-2 easiness factor (>= 1.3).
    :param interval: Days until next review.
    :param repetitions: Number of consecutive correct reviews.
    :param next_review: Datetime of the next scheduled review.
    """

    user_id: str
    word_id: int
    easiness_factor: float = 2.5
    interval: int = 0
    repetitions: int = 0
    next_review: datetime = Field(
        default_factory=datetime.now
    )


def learning_mode(word: Word) -> LearningMode:
    """Derive the learning mode from a word's language pair.

    :param word: The word to check.
    :return: `LearningMode.DEFINITION` when source and target
        languages are the same, `LearningMode.TRANSLATION`
        otherwise.
    """
    if word.language_from == word.language_to:
        return LearningMode.DEFINITION
    return LearningMode.TRANSLATION
