"""Tests for rembrandt.models."""

from datetime import datetime

import pytest

from rembrandt.models import (
    AnswerHistory,
    AnswerResult,
    CardState,
    Concept,
    ConversationStage,
    ConversationState,
    DailyStats,
    Exercise,
    ExerciseType,
    FSRSConfig,
    Hint,
    ReviewConfig,
    ReviewForecast,
    SessionMode,
    SessionSnapshot,
    SessionStats,
    Topic,
    TopicProgress,
    User,
    UserProgress,
    UserSession,
    WeakConcept,
)


# --- User Tests ---


def test_user_creation_defaults():
    user = User(username="alice")
    assert user.id is None
    assert user.username == "alice"
    assert user.display_name is None
    assert user.password_hash == ""
    assert isinstance(user.created_at, datetime)


def test_user_password_hash_excluded_from_dump():
    user = User(
        username="alice", password_hash="salt$hash",
    )
    data = user.model_dump()
    assert "password_hash" not in data


# --- UserSession Tests ---


def test_user_session_creation():
    expires = datetime(2026, 3, 2, 12, 0, 0)
    session = UserSession(
        user_id=1, token="abc123", expires_at=expires,
    )
    assert session.id is None
    assert session.user_id == 1
    assert session.token == "abc123"
    assert isinstance(session.created_at, datetime)
    assert session.expires_at == expires


# --- Concept Tests ---


def test_concept_creation():
    concept = Concept(
        front="What is a p-value?",
        back="Probability under H0",
    )
    assert concept.front == "What is a p-value?"
    assert concept.back == "Probability under H0"
    assert concept.id is None


def test_concept_with_id():
    concept = Concept(
        id=1,
        front="What is overfitting?",
        back="Model learns noise",
    )
    assert concept.id == 1


def test_concept_tags_default_empty():
    concept = Concept(front="cat", back="gato")
    assert concept.tags == []


def test_concept_tags_explicit():
    concept = Concept(
        front="gradient descent",
        back="optimization algorithm",
        tags=["ml"],
    )
    assert concept.tags == ["ml"]


def test_concept_context_default_empty():
    concept = Concept(front="cat", back="gato")
    assert concept.context == ""


def test_concept_context_explicit():
    concept = Concept(
        front="cat",
        back="gato",
        context="A common household pet",
    )
    assert concept.context == "A common household pet"


def test_concept_owner_id_default_none():
    concept = Concept(front="cat", back="gato")
    assert concept.owner_id is None


def test_concept_owner_id_explicit():
    concept = Concept(
        front="cat", back="gato", owner_id=42,
    )
    assert concept.owner_id == 42


# --- ExerciseType Tests ---


def test_exercise_type_values():
    assert ExerciseType.FLASHCARD == "flashcard"
    assert (
        ExerciseType.MULTIPLE_CHOICE
        == "multiple_choice"
    )


def test_exercise_type_count():
    assert len(ExerciseType) == 2


# --- Exercise Tests ---


def test_exercise_flashcard():
    concept = Concept(front="cat", back="gato")
    ex = Exercise(
        concept=concept,
        exercise_type=ExerciseType.FLASHCARD,
    )
    assert ex.exercise_type == ExerciseType.FLASHCARD
    assert ex.options == []


def test_exercise_multiple_choice():
    concept = Concept(front="cat", back="gato")
    ex = Exercise(
        concept=concept,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=["gato", "perro", "casa", "libro"],
    )
    assert len(ex.options) == 4
    assert "gato" in ex.options


def test_exercise_prompt_and_expected_defaults():
    concept = Concept(front="cat", back="gato")
    ex = Exercise(
        concept=concept,
        exercise_type=ExerciseType.FLASHCARD,
    )
    assert ex.prompt == ""
    assert ex.expected_answer == ""


# --- AnswerResult Tests ---


def test_answer_result_correct():
    concept = Concept(front="cat", back="gato")
    result = AnswerResult(
        correct=True,
        expected="gato",
        given="gato",
        concept=concept,
    )
    assert result.correct is True


def test_answer_result_incorrect():
    concept = Concept(front="cat", back="gato")
    result = AnswerResult(
        correct=False,
        expected="gato",
        given="perro",
        concept=concept,
    )
    assert result.correct is False
    assert result.given == "perro"


def test_answer_result_near_miss_default():
    concept = Concept(front="cat", back="gato")
    result = AnswerResult(
        correct=True,
        expected="gato",
        given="gato",
        concept=concept,
    )
    assert result.near_miss is False


# --- UserProgress Tests ---


def test_user_progress_defaults():
    progress = UserProgress(
        user_id=1, concept_id=1,
    )
    assert progress.easiness_factor == 2.5
    assert progress.interval == 0
    assert progress.repetitions == 0
    assert isinstance(progress.next_review, datetime)
    assert progress.state == CardState.NEW


def test_user_progress_custom_values():
    dt = datetime(2026, 3, 1, 12, 0, 0)
    progress = UserProgress(
        user_id=1,
        concept_id=1,
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
            user_id=1,
            concept_id="not_int",  # type: ignore[arg-type]
        )


# --- Topic Tests ---


def test_topic_creation_defaults():
    topic = Topic(title="Linear Algebra")
    assert topic.id is None
    assert topic.title == "Linear Algebra"
    assert topic.description == ""
    assert topic.tags == []
    assert topic.concept_count == 0
    assert topic.concept_ids == []


def test_topic_all_fields():
    topic = Topic(
        id=5,
        title="Data Science Basics",
        description="Intro to DS concepts",
        tags=["data-science"],
        concept_count=10,
        concept_ids=list(range(1, 11)),
    )
    assert topic.id == 5
    assert topic.tags == ["data-science"]
    assert topic.concept_count == 10
    assert len(topic.concept_ids) == 10


# --- TopicProgress Tests ---


def test_topic_progress_creation():
    tp = TopicProgress(
        topic_id=1,
        user_id=1,
        concepts_total=10,
        concepts_studied=5,
        concepts_mastered=2,
        completion_pct=50.0,
        mastery_pct=20.0,
    )
    assert tp.topic_id == 1
    assert tp.user_id == 1
    assert tp.concepts_total == 10
    assert tp.concepts_studied == 5
    assert tp.concepts_mastered == 2
    assert tp.completion_pct == 50.0
    assert tp.mastery_pct == 20.0


# --- Hint Tests ---


def test_hint_creation():
    h = Hint(
        first_letter="g",
        word_length=4,
        pattern="g___",
    )
    assert h.first_letter == "g"
    assert h.word_length == 4
    assert h.pattern == "g___"


def test_hint_context_default_empty():
    h = Hint(
        first_letter="g",
        word_length=4,
        pattern="g___",
    )
    assert h.context == ""


def test_hint_context_explicit():
    h = Hint(
        first_letter="g",
        word_length=4,
        pattern="g___",
        context="A small animal",
    )
    assert h.context == "A small animal"


# --- SessionStats Tests ---


def test_session_stats_defaults():
    stats = SessionStats()
    assert stats.total == 0
    assert stats.correct == 0
    assert stats.incorrect == 0
    assert stats.streak == 0
    assert stats.best_streak == 0
    assert stats.accuracy_pct == 0.0


def test_session_stats_custom():
    stats = SessionStats(
        total=10,
        correct=7,
        incorrect=3,
        streak=2,
        best_streak=4,
        accuracy_pct=70.0,
    )
    assert stats.total == 10
    assert stats.accuracy_pct == 70.0


# --- AnswerHistory Tests ---


def test_answer_history_creation():
    ah = AnswerHistory(
        user_id=1,
        concept_id=1,
        exercise_type="flashcard",
        correct=True,
        quality=5,
    )
    assert ah.id is None
    assert ah.user_id == 1
    assert ah.concept_id == 1
    assert ah.correct is True
    assert ah.quality == 5
    assert isinstance(ah.answered_at, datetime)


# --- DailyStats Tests ---


def test_daily_stats_creation():
    ds = DailyStats(
        date="2026-02-27",
        answers=10,
        correct=7,
        accuracy_pct=70.0,
    )
    assert ds.date == "2026-02-27"
    assert ds.answers == 10
    assert ds.correct == 7
    assert ds.accuracy_pct == 70.0


# --- WeakConcept Tests ---


def test_weak_concept_creation():
    concept = Concept(
        id=1, front="cat", back="gato",
    )
    wc = WeakConcept(
        concept=concept,
        attempts=10,
        errors=7,
        error_rate=0.7,
        last_attempt=datetime(2026, 2, 27, 10, 0, 0),
    )
    assert wc.concept.id == 1
    assert wc.attempts == 10
    assert wc.errors == 7
    assert wc.error_rate == 0.7


# --- SessionSnapshot Tests ---


def test_session_snapshot_defaults():
    snap = SessionSnapshot(user_id=1)
    assert snap.user_id == 1
    assert snap.mode == SessionMode.MIXED
    assert snap.tags is None
    assert snap.concept_ids is None
    assert snap.review_config is None
    assert snap.fsrs_config is None
    assert snap.current_exercise is None
    assert snap.hint_count == 0
    assert snap.buried_concept_ids == []
    assert snap.correct == 0
    assert snap.incorrect == 0
    assert snap.streak == 0
    assert snap.best_streak == 0
    assert snap.new_served == 0
    assert snap.review_served == 0
    assert isinstance(snap.saved_at, datetime)


def test_session_snapshot_with_data():
    concept = Concept(
        id=1, front="cat", back="gato",
    )
    ex = Exercise(
        concept=concept,
        exercise_type=ExerciseType.FLASHCARD,
    )
    snap = SessionSnapshot(
        user_id=1,
        mode=SessionMode.LEARN_NEW,
        tags=["math"],
        concept_ids=[1, 2, 3],
        current_exercise=ex,
        buried_concept_ids=[1],
        correct=3,
        incorrect=1,
    )
    assert snap.mode == SessionMode.LEARN_NEW
    assert snap.tags == ["math"]
    assert snap.concept_ids == [1, 2, 3]
    assert snap.current_exercise is not None
    assert snap.buried_concept_ids == [1]
    assert snap.correct == 3


# --- ReviewForecast Tests ---


def test_review_forecast_creation():
    rf = ReviewForecast(
        date="2026-03-01", due_count=5,
    )
    assert rf.date == "2026-03-01"
    assert rf.due_count == 5


# --- ConversationStage Tests ---


def test_conversation_stage_values():
    assert (
        ConversationStage.CHOOSING_TOPIC
        == "choosing_topic"
    )
    assert ConversationStage.IDLE == "idle"
    assert (
        ConversationStage.EXERCISING == "exercising"
    )
    assert (
        ConversationStage.AWAITING_ANSWER
        == "awaiting_answer"
    )
    assert (
        ConversationStage.AWAITING_SELF_GRADE
        == "awaiting_self_grade"
    )
    assert (
        ConversationStage.VIEWING_STATS
        == "viewing_stats"
    )


# --- ConversationState Tests ---


def test_conversation_state_defaults():
    cs = ConversationState(user_id=1)
    assert cs.user_id == 1
    assert cs.key == ""
    assert cs.stage == ConversationStage.IDLE
    assert cs.data == {}
    assert isinstance(cs.updated_at, datetime)


# --- SessionMode Tests ---


def test_session_mode_values():
    assert SessionMode.LEARN_NEW == "learn_new"
    assert SessionMode.REVIEW_DUE == "review_due"
    assert SessionMode.MIXED == "mixed"


# --- CardState Tests ---


def test_card_state_values():
    assert CardState.NEW == "new"
    assert CardState.LEARNING == "learning"
    assert CardState.REVIEW == "review"
    assert CardState.RELEARNING == "relearning"
    assert CardState.SUSPENDED == "suspended"


# --- ReviewConfig Tests ---


def test_review_config_defaults():
    cfg = ReviewConfig()
    assert cfg.learning_steps == [1, 10]
    assert cfg.graduating_interval == 1
    assert cfg.relearning_steps == [10]
    assert cfg.lapse_new_interval_factor == 0.7
    assert cfg.lapse_min_interval == 1
    assert cfg.leech_threshold == 8
    assert cfg.max_new_cards == 0
    assert cfg.max_review_cards == 0


# --- FSRSConfig Tests ---


def test_fsrs_config_defaults():
    cfg = FSRSConfig()
    assert len(cfg.weights) == 19
    assert cfg.desired_retention == 0.9
    assert cfg.max_interval == 36500
    assert cfg.learning_steps == [1, 10]
    assert cfg.relearning_steps == [10]
