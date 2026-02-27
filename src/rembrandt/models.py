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
    :param gender: Noun gender (`"m"` or `"f"`), `None` for
        non-nouns.
    :param conjugation_group: Verb conjugation group
        (`"ar"`, `"er"`, or `"ir"`), `None` for non-verbs.
    :param tags: Topic tags (e.g. `["food", "travel"]`).
    :param cefr: CEFR level (`"A1"` through `"C2"`), `None`
        when not assigned.
    """

    id: int | None = None
    language_from: str
    language_to: str
    word_from: str
    word_to: str
    gender: str | None = None
    conjugation_group: str | None = None
    tags: list[str] = Field(default_factory=list)
    cefr: str | None = None


class Lesson(BaseModel):
    """A named set of words with a learning goal.

    :param id: Unique identifier (assigned by the database).
    :param title: Lesson title (e.g. `"A1 - Lesson 1"`).
    :param description: Brief description of the lesson content.
    :param language_from: Source language code (e.g. `"en"`).
    :param language_to: Target language code (e.g. `"es"`).
    :param cefr: CEFR level (`"A1"` through `"C2"`), `None`
        when not assigned.
    :param tags: Topic tags (e.g. `["food", "travel"]`).
    :param word_count: Number of words in the lesson.
    :param word_ids: List of word database ids (populated after
        loading into a database).
    """

    id: int | None = None
    title: str
    description: str = ""
    language_from: str
    language_to: str
    cefr: str | None = None
    tags: list[str] = Field(default_factory=list)
    word_count: int = 0
    word_ids: list[int] = Field(default_factory=list)


class User(BaseModel):
    """A registered user.

    :param id: Unique identifier (assigned by the database).
    :param username: Unique login name.
    :param display_name: Optional display name.
    :param password_hash: Hashed password (excluded from
        serialization).
    :param created_at: Account creation timestamp.
    """

    id: int | None = None
    username: str
    display_name: str | None = None
    password_hash: str = Field(exclude=True, default="")
    created_at: datetime = Field(default_factory=datetime.now)


class UserSession(BaseModel):
    """An active login session for a user.

    :param id: Unique identifier (assigned by the database).
    :param user_id: References `User.id`.
    :param token: Unique session token.
    :param created_at: Session creation timestamp.
    :param expires_at: Session expiry timestamp.
    """

    id: int | None = None
    user_id: int
    token: str
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime


class LessonProgress(BaseModel):
    """Progress statistics for a user within a lesson.

    :param lesson_id: Lesson identifier.
    :param user_id: User identifier.
    :param words_total: Total words in the lesson.
    :param words_studied: Words with at least one review.
    :param words_mastered: Words with `repetitions >= 3`.
    :param completion_pct: `words_studied / words_total * 100`.
    :param mastery_pct: `words_mastered / words_total * 100`.
    """

    lesson_id: int
    user_id: str
    words_total: int
    words_studied: int
    words_mastered: int
    completion_pct: float
    mastery_pct: float


class LearningMode(str, Enum):
    """How a word is being learned.

    :cvar TRANSLATION: Bilingual — source and target languages
        differ (e.g. EN -> ES).
    :cvar DEFINITION: Monolingual — same language, word paired
        with its definition (e.g. EN -> EN).
    """

    TRANSLATION = "translation"
    DEFINITION = "definition"


class SessionMode(str, Enum):
    """How a session selects words.

    :cvar LEARN_NEW: Only present new (unreviewed) words.
    :cvar REVIEW_DUE: Only present words due for review.
    :cvar MIXED: Due words first, then new words to fill.
    """

    LEARN_NEW = "learn_new"
    REVIEW_DUE = "review_due"
    MIXED = "mixed"


class ExerciseType(str, Enum):
    """Type of vocabulary exercise."""

    FLASHCARD = "flashcard"
    MULTIPLE_CHOICE = "multiple_choice"
    REVERSE_FLASHCARD = "reverse_flashcard"
    SELF_GRADED = "self_graded"
    GENDER_MATCH = "gender_match"
    CONJUGATION = "conjugation"
    CLOZE = "cloze"
    TRANSLATION_CLOZE = "translation_cloze"


class Exercise(BaseModel):
    """A generated exercise for a word.

    :param word: The word being tested.
    :param exercise_type: The type of exercise.
    :param options: Answer options (for multiple choice).
    :param prompt: Display text (sentence, tense/person label).
    :param expected_answer: Correct answer when not derivable
        from the `Word` fields.
    """

    word: Word
    exercise_type: ExerciseType
    options: list[str] = Field(default_factory=list)
    prompt: str = ""
    expected_answer: str = ""


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


class Hint(BaseModel):
    """A partial hint for the current exercise.

    :param first_letter: The first character of the expected
        answer.
    :param word_length: The number of characters in the
        expected answer.
    :param pattern: A masked pattern where only the first
        letter is revealed (e.g. `"g___"`).
    """

    first_letter: str
    word_length: int
    pattern: str


class SessionStats(BaseModel):
    """Statistics for a vocabulary exercise session.

    :param total: Total number of answers given.
    :param correct: Number of correct answers.
    :param incorrect: Number of incorrect answers.
    :param streak: Current consecutive correct streak.
    :param best_streak: Best consecutive correct streak in
        the session.
    :param accuracy_pct: `correct / total * 100` (0.0 when
        no answers have been given).
    """

    total: int = 0
    correct: int = 0
    incorrect: int = 0
    streak: int = 0
    best_streak: int = 0
    accuracy_pct: float = 0.0


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


class AnswerHistory(BaseModel):
    """A single recorded answer in the history log.

    :param id: Unique identifier (assigned by the database).
    :param user_id: Identifier for the user.
    :param word_id: Identifier for the word.
    :param exercise_type: The exercise type used.
    :param correct: Whether the answer was correct.
    :param quality: SM-2 quality score (0-5).
    :param answered_at: Timestamp of the answer.
    """

    id: int | None = None
    user_id: str
    word_id: int
    exercise_type: str
    correct: bool
    quality: int
    answered_at: datetime = Field(
        default_factory=datetime.now
    )


class DailyStats(BaseModel):
    """Aggregated statistics for a single day.

    :param date: The date (YYYY-MM-DD string).
    :param answers: Total answers given that day.
    :param correct: Number of correct answers.
    :param accuracy_pct: `correct / answers * 100`.
    """

    date: str
    answers: int
    correct: int
    accuracy_pct: float


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
