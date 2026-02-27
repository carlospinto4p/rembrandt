"""Tests for rembrandt.models."""

from datetime import datetime

import pytest

from rembrandt.models import (
    AnswerHistory,
    AnswerResult,
    DailyStats,
    Exercise,
    ExerciseType,
    Hint,
    LearningMode,
    Lesson,
    LessonProgress,
    SessionStats,
    User,
    UserProgress,
    UserSession,
    Word,
    learning_mode,
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


# --- Word Tests ---


def test_word_creation():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="hello",
        word_to="hola",
    )
    assert word.word_from == "hello"
    assert word.word_to == "hola"
    assert word.id is None


def test_word_with_id():
    word = Word(
        id=1,
        language_from="en",
        language_to="es",
        word_from="cat",
        word_to="gato",
    )
    assert word.id == 1


def test_word_tags_default_empty():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="cat",
        word_to="gato",
    )
    assert word.tags == []


def test_word_tags_explicit():
    word = Word(
        language_from="es",
        language_to="en",
        word_from="pan",
        word_to="bread",
        tags=["food"],
    )
    assert word.tags == ["food"]


def test_word_cefr_default_none():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="cat",
        word_to="gato",
    )
    assert word.cefr is None


def test_word_cefr_explicit():
    word = Word(
        language_from="es",
        language_to="en",
        word_from="ser",
        word_to="to be",
        cefr="A1",
    )
    assert word.cefr == "A1"


def test_word_gender_and_conjugation_defaults():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="cat",
        word_to="gato",
    )
    assert word.gender is None
    assert word.conjugation_group is None


def test_word_gender_and_conjugation_explicit():
    word = Word(
        language_from="es",
        language_to="en",
        word_from="casa",
        word_to="house",
        gender="f",
        conjugation_group=None,
    )
    assert word.gender == "f"
    assert word.conjugation_group is None

    verb = Word(
        language_from="es",
        language_to="en",
        word_from="hablar",
        word_to="to speak",
        conjugation_group="ar",
    )
    assert verb.conjugation_group == "ar"
    assert verb.gender is None


# --- LearningMode Tests ---


def test_learning_mode_translation():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="cat",
        word_to="gato",
    )
    assert learning_mode(word) == LearningMode.TRANSLATION


def test_learning_mode_definition():
    word = Word(
        language_from="en",
        language_to="en",
        word_from="ephemeral",
        word_to="lasting for a very short time",
    )
    assert learning_mode(word) == LearningMode.DEFINITION


def test_learning_mode_values():
    assert LearningMode.TRANSLATION == "translation"
    assert LearningMode.DEFINITION == "definition"


# --- ExerciseType Tests ---


def test_exercise_type_values():
    assert ExerciseType.FLASHCARD == "flashcard"
    assert ExerciseType.MULTIPLE_CHOICE == "multiple_choice"
    assert ExerciseType.REVERSE_FLASHCARD == "reverse_flashcard"
    assert ExerciseType.SELF_GRADED == "self_graded"


def test_exercise_type_gender_match():
    assert ExerciseType.GENDER_MATCH == "gender_match"


def test_exercise_type_conjugation():
    assert ExerciseType.CONJUGATION == "conjugation"


def test_exercise_type_cloze():
    assert ExerciseType.CLOZE == "cloze"


def test_exercise_type_translation_cloze():
    assert ExerciseType.TRANSLATION_CLOZE == "translation_cloze"


# --- Exercise Tests ---


def test_exercise_flashcard():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="dog",
        word_to="perro",
    )
    ex = Exercise(
        word=word,
        exercise_type=ExerciseType.FLASHCARD,
    )
    assert ex.exercise_type == ExerciseType.FLASHCARD
    assert ex.options == []


def test_exercise_multiple_choice():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="dog",
        word_to="perro",
    )
    ex = Exercise(
        word=word,
        exercise_type=ExerciseType.MULTIPLE_CHOICE,
        options=["perro", "gato", "casa", "libro"],
    )
    assert len(ex.options) == 4
    assert "perro" in ex.options


def test_exercise_prompt_and_expected_defaults():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="cat",
        word_to="gato",
    )
    ex = Exercise(
        word=word,
        exercise_type=ExerciseType.FLASHCARD,
    )
    assert ex.prompt == ""
    assert ex.expected_answer == ""


def test_exercise_prompt_and_expected_set():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="house",
        word_to="casa",
        gender="f",
    )
    ex = Exercise(
        word=word,
        exercise_type=ExerciseType.GENDER_MATCH,
        options=["el", "la"],
        prompt="___ casa",
        expected_answer="la",
    )
    assert ex.prompt == "___ casa"
    assert ex.expected_answer == "la"


# --- AnswerResult Tests ---


def test_answer_result_correct():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="dog",
        word_to="perro",
    )
    result = AnswerResult(
        correct=True,
        expected="perro",
        given="perro",
        word=word,
    )
    assert result.correct is True


def test_answer_result_incorrect():
    word = Word(
        language_from="en",
        language_to="es",
        word_from="dog",
        word_to="perro",
    )
    result = AnswerResult(
        correct=False,
        expected="perro",
        given="gato",
        word=word,
    )
    assert result.correct is False
    assert result.given == "gato"


# --- UserProgress Tests ---


def test_user_progress_defaults():
    progress = UserProgress(user_id="u1", word_id=1)
    assert progress.easiness_factor == 2.5
    assert progress.interval == 0
    assert progress.repetitions == 0
    assert isinstance(progress.next_review, datetime)


def test_user_progress_custom_values():
    dt = datetime(2026, 3, 1, 12, 0, 0)
    progress = UserProgress(
        user_id="u1",
        word_id=1,
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
            user_id="u1",
            word_id="not_an_int",  # type: ignore[arg-type]
        )


# --- Lesson Tests ---


def test_lesson_creation_defaults():
    lesson = Lesson(
        title="A1 - Lesson 1",
        language_from="en",
        language_to="es",
    )
    assert lesson.id is None
    assert lesson.title == "A1 - Lesson 1"
    assert lesson.description == ""
    assert lesson.cefr is None
    assert lesson.tags == []
    assert lesson.word_count == 0
    assert lesson.word_ids == []


def test_lesson_all_fields():
    lesson = Lesson(
        id=5,
        title="A1 Food",
        description="A1 words related to food",
        language_from="en",
        language_to="es",
        cefr="A1",
        tags=["food"],
        word_count=10,
        word_ids=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    )
    assert lesson.id == 5
    assert lesson.cefr == "A1"
    assert lesson.tags == ["food"]
    assert lesson.word_count == 10
    assert len(lesson.word_ids) == 10


# --- LessonProgress Tests ---


def test_lesson_progress_creation():
    lp = LessonProgress(
        lesson_id=1,
        user_id="u1",
        words_total=10,
        words_studied=5,
        words_mastered=2,
        completion_pct=50.0,
        mastery_pct=20.0,
    )
    assert lp.lesson_id == 1
    assert lp.user_id == "u1"
    assert lp.words_total == 10
    assert lp.words_studied == 5
    assert lp.words_mastered == 2
    assert lp.completion_pct == 50.0
    assert lp.mastery_pct == 20.0


# --- Hint Tests ---


def test_hint_creation():
    h = Hint(
        first_letter="g", word_length=4, pattern="g___",
    )
    assert h.first_letter == "g"
    assert h.word_length == 4
    assert h.pattern == "g___"


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
        user_id="u1",
        word_id=1,
        exercise_type="flashcard",
        correct=True,
        quality=5,
    )
    assert ah.id is None
    assert ah.user_id == "u1"
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
