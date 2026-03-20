"""Pydantic models for spaced-repetition exercises."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Concept(BaseModel):
    """A study concept with a prompt and answer.

    :param id: Unique identifier (assigned by the database).
    :param front: The prompt shown to the learner (e.g. a
        question, term, or formula).
    :param back: The expected answer or definition.
    :param context: Optional explanation or notes shown after
        answering.
    :param tags: Arbitrary grouping tags (e.g.
        `["math", "calculus"]`).
    :param owner_id: User who created this concept. `None`
        means the concept is shared (visible to all users).
    """

    id: int | None = None
    front: str
    back: str
    context: str = ""
    tags: list[str] = Field(default_factory=list)
    owner_id: int | None = None


class Topic(BaseModel):
    """A named set of concepts.

    :param id: Unique identifier (assigned by the database).
    :param title: Topic title (e.g. `"Linear Algebra Basics"`).
    :param description: Brief description of the topic.
    :param tags: Grouping tags (e.g. `["math", "beginner"]`).
    :param concept_count: Number of concepts in the topic.
    :param concept_ids: List of concept database ids (populated
        after loading into a database).
    """

    id: int | None = None
    title: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    concept_count: int = 0
    concept_ids: list[int] = Field(default_factory=list)


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


class TopicProgress(BaseModel):
    """Progress statistics for a user within a topic.

    :param topic_id: Topic identifier.
    :param user_id: The user's database id.
    :param concepts_total: Total concepts in the topic.
    :param concepts_studied: Concepts with at least one review.
    :param concepts_mastered: Concepts with
        `repetitions >= 3`.
    :param completion_pct: `concepts_studied / concepts_total
        * 100`.
    :param mastery_pct: `concepts_mastered / concepts_total
        * 100`.
    """

    topic_id: int
    user_id: int
    concepts_total: int
    concepts_studied: int
    concepts_mastered: int
    completion_pct: float
    mastery_pct: float


class SessionMode(str, Enum):
    """How a session selects concepts.

    :cvar LEARN_NEW: Only present new (unreviewed) concepts.
    :cvar REVIEW_DUE: Only present concepts due for review.
    :cvar MIXED: Due concepts first, then new concepts to fill.
    """

    LEARN_NEW = "learn_new"
    REVIEW_DUE = "review_due"
    MIXED = "mixed"


class CardState(str, Enum):
    """State of a card in the learning pipeline.

    :cvar NEW: Never reviewed — will enter learning steps on
        first answer.
    :cvar LEARNING: Working through initial learning steps.
    :cvar REVIEW: Graduated — uses SM-2 intervals.
    :cvar RELEARNING: Lapsed from review — working through
        relearning steps before returning to review.
    :cvar SUSPENDED: Frozen — card is a leech and will not
        appear in reviews until manually unsuspended.
    """

    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"
    RELEARNING = "relearning"
    SUSPENDED = "suspended"


class ReviewConfig(BaseModel):
    """Configuration for Anki-style learning and relearning steps.

    :param learning_steps: Minutes between learning steps for
        new cards (e.g. `[1, 10]`). Empty list graduates
        immediately.
    :param graduating_interval: Days for the first review
        interval after graduating from learning steps.
    :param relearning_steps: Minutes between relearning steps
        for lapsed cards (e.g. `[10]`). Empty list returns to
        review immediately.
    :param lapse_new_interval_factor: Multiplier applied to the
        pre-lapse interval when returning to review (e.g. `0.7`
        means 70% of the old interval).
    :param lapse_min_interval: Minimum interval in days after a
        lapse, regardless of the factor calculation.
    :param max_fuzz_factor: Maximum random jitter applied to
        day-based intervals (e.g. `0.05` means +/-5%). Set to
        `0` to disable. Intervals below 3 days are never fuzzed.
    :param leech_threshold: Number of lapses before a card is
        suspended as a leech. Set to `0` to disable leech
        detection. Default `8` matches Anki.
    :param max_new_cards: Maximum new cards per session. `0`
        means unlimited.
    :param max_review_cards: Maximum review cards per session.
        `0` means unlimited.
    """

    learning_steps: list[int] = Field(
        default_factory=lambda: [1, 10],
    )
    graduating_interval: int = 1
    relearning_steps: list[int] = Field(
        default_factory=lambda: [10],
    )
    lapse_new_interval_factor: float = 0.7
    lapse_min_interval: int = 1
    max_fuzz_factor: float = 0.05
    leech_threshold: int = 8
    max_new_cards: int = 0
    max_review_cards: int = 0


class ExerciseType(str, Enum):
    """Type of exercise."""

    FLASHCARD = "flashcard"
    MULTIPLE_CHOICE = "multiple_choice"


class Exercise(BaseModel):
    """A generated exercise for a concept.

    :param concept: The concept being tested.
    :param exercise_type: The type of exercise.
    :param options: Answer options (for multiple choice).
    :param prompt: Display text.
    :param expected_answer: Correct answer when not derivable
        from the `Concept` fields.
    """

    concept: Concept
    exercise_type: ExerciseType
    options: list[str] = Field(default_factory=list)
    prompt: str = ""
    expected_answer: str = ""


class AnswerResult(BaseModel):
    """Result of evaluating a user's answer.

    :param correct: Whether the answer was correct.
    :param expected: The expected answer.
    :param given: The answer the user gave.
    :param concept: The concept that was tested.
    :param near_miss: ``True`` when the answer was accepted
        via fuzzy matching (small typo). Consumers can use
        this to show a "close enough" warning.
    """

    correct: bool
    expected: str
    given: str
    concept: Concept
    near_miss: bool = False


class Hint(BaseModel):
    """A partial hint for the current exercise.

    Calling `Session.hint()` multiple times progressively
    reveals more letters (e.g. `"g___"` → `"ga__"` → `"gat_"`).

    :param first_letter: The first character of the expected
        answer.
    :param word_length: The number of characters in the
        expected answer.
    :param pattern: A masked pattern revealing `reveal_count`
        letters from the start (e.g. `"ga__"`).
    :param reveal_count: Number of letters currently revealed.
    :param context: The concept's context field, or empty
        string when not available.
    """

    first_letter: str
    word_length: int
    pattern: str
    reveal_count: int = 1
    context: str = ""


class SessionStats(BaseModel):
    """Statistics for an exercise session.

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


class FSRSConfig(BaseModel):
    """Configuration for the FSRS spaced-repetition algorithm.

    :param weights: FSRS-5 parameter weights (19 values).
        Uses sensible defaults when not provided.
    :param desired_retention: Target recall probability when
        scheduling the next review (0.0-1.0, default 0.9).
    :param max_interval: Maximum interval in days
        (default 36500).
    :param learning_steps: Minutes between learning steps for
        new cards (e.g. `[1, 10]`). Empty list graduates
        immediately.
    :param relearning_steps: Minutes between relearning steps
        for lapsed cards (e.g. `[10]`). Empty list returns to
        review immediately.
    """

    weights: tuple[float, ...] = (
        0.40255, 1.18385, 3.173, 15.69105,
        7.1949, 0.5345, 1.4604, 0.0046,
        1.54575, 0.1192, 1.01925,
        1.9395, 0.11, 0.29605, 2.2698,
        0.2315, 2.9898,
        0.51655, 0.6621,
    )
    desired_retention: float = 0.9
    max_interval: int = 36500
    learning_steps: list[int] = Field(
        default_factory=lambda: [1, 10],
    )
    relearning_steps: list[int] = Field(
        default_factory=lambda: [10],
    )


class SessionSnapshot(BaseModel):
    """Serializable snapshot of a `Session`'s in-memory state.

    Used to persist and restore sessions across process
    restarts (e.g. for a Telegram bot).

    :param user_id: The user's database id.
    :param mode: Session mode.
    :param tags: Tag filter, or `None`.
    :param concept_ids: Restricted concept ids, or `None`.
    :param review_config: SM-2 configuration, or `None`.
    :param fsrs_config: FSRS configuration, or `None`.
    :param current_exercise: The active exercise, or `None`.
    :param hint_count: Number of hints given for the current
        exercise.
    :param buried_concept_ids: Concept ids already shown this
        session.
    :param correct: Number of correct answers.
    :param incorrect: Number of incorrect answers.
    :param streak: Current consecutive correct streak.
    :param best_streak: Best streak in this session.
    :param new_served: New cards served so far.
    :param review_served: Review cards served so far.
    :param saved_at: Timestamp when the snapshot was saved.
    """

    user_id: int
    mode: SessionMode = SessionMode.MIXED
    tags: list[str] | None = None
    concept_ids: list[int] | None = None
    review_config: ReviewConfig | None = None
    fsrs_config: FSRSConfig | None = None
    current_exercise: Exercise | None = None
    hint_count: int = 0
    buried_concept_ids: list[int] = Field(
        default_factory=list,
    )
    correct: int = 0
    incorrect: int = 0
    streak: int = 0
    best_streak: int = 0
    new_served: int = 0
    review_served: int = 0
    saved_at: datetime = Field(
        default_factory=datetime.now,
    )


class UserProgress(BaseModel):
    """Spaced-repetition progress for a user-concept pair.

    :param user_id: The user's database id.
    :param concept_id: Identifier for the concept.
    :param easiness_factor: SM-2 easiness factor (>= 1.3).
    :param interval: Days until next review.
    :param repetitions: Number of consecutive correct reviews.
    :param next_review: Datetime of the next scheduled review.
    :param state: Current card state in the learning pipeline.
    :param step_index: Current position within learning or
        relearning steps.
    :param lapse_count: Cumulative number of lapses (REVIEW
        failures). Does not reset on success.
    :param stability: FSRS stability in days (how long until
        recall drops to `desired_retention`). `None` when
        using SM-2.
    :param difficulty: FSRS difficulty (1.0-10.0). `None`
        when using SM-2.
    """

    user_id: int
    concept_id: int
    easiness_factor: float = 2.5
    interval: int = 0
    repetitions: int = 0
    next_review: datetime = Field(
        default_factory=datetime.now
    )
    state: CardState = CardState.NEW
    step_index: int = 0
    lapse_count: int = 0
    stability: float | None = None
    difficulty: float | None = None


class WeakConcept(BaseModel):
    """A concept the user consistently gets wrong.

    :param concept: The study concept.
    :param attempts: Total number of attempts.
    :param errors: Number of incorrect attempts.
    :param error_rate: `errors / attempts`.
    :param last_attempt: Timestamp of the most recent attempt.
    """

    concept: Concept
    attempts: int
    errors: int
    error_rate: float
    last_attempt: datetime


class AnswerHistory(BaseModel):
    """A single recorded answer in the history log.

    :param id: Unique identifier (assigned by the database).
    :param user_id: The user's database id.
    :param concept_id: Identifier for the concept.
    :param exercise_type: The exercise type used.
    :param correct: Whether the answer was correct.
    :param quality: SM-2 quality score (0-5).
    :param answered_at: Timestamp of the answer.
    """

    id: int | None = None
    user_id: int
    concept_id: int
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


class ReviewForecast(BaseModel):
    """Predicted review workload for a single day.

    :param date: The date (YYYY-MM-DD string).
    :param due_count: Number of cards due for review on that day.
    """

    date: str
    due_count: int


class ConversationStage(str, Enum):
    """Stage in a multi-step bot conversation.

    :cvar IDLE: No active interaction.
    :cvar CHOOSING_TOPIC: Browsing or selecting a topic.
    :cvar EXERCISING: Session active, ready for next exercise.
    :cvar AWAITING_ANSWER: Exercise displayed, waiting for the
        user's answer.
    :cvar AWAITING_SELF_GRADE: Self-graded exercise shown,
        waiting for a 0-5 rating.
    :cvar VIEWING_STATS: Reviewing session or progress
        statistics.
    """

    IDLE = "idle"
    CHOOSING_TOPIC = "choosing_topic"
    EXERCISING = "exercising"
    AWAITING_ANSWER = "awaiting_answer"
    AWAITING_SELF_GRADE = "awaiting_self_grade"
    VIEWING_STATS = "viewing_stats"


class ConversationState(BaseModel):
    """Persistent state for a bot conversation.

    Tracks which stage the user is in and carries arbitrary
    context data needed by that stage (e.g. the current page
    of topics, the session snapshot key).

    :param user_id: The user's database id.
    :param key: Conversation key (e.g. a chat id) to
        distinguish multiple conversations per user.
    :param stage: Current conversation stage.
    :param data: Arbitrary context data for the current stage.
    :param updated_at: Timestamp of the last state change.
    """

    user_id: int
    key: str = ""
    stage: ConversationStage = ConversationStage.IDLE
    data: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(
        default_factory=datetime.now,
    )
