"""Tests for rembrandt.session."""

import json

import pytest
import pytest_asyncio

from datetime import datetime

from rembrandt.db import Database
from rembrandt.models import (
    CardState,
    ExerciseType,
    ReviewConfig,
    SessionMode,
    UserProgress,
    Word,
)
from rembrandt.session import Session, quick_session

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session(db_with_words):
    return Session(
        db_with_words, user_id=1,
        language_from="en", language_to="es",
    )


@pytest_asyncio.fixture
async def definition_session(definition_db):
    return Session(
        definition_db, user_id=1,
        language_from="en", language_to="en",
    )


# --- Session Tests ---


async def test_next_exercise_returns_exercise(session):
    ex = await session.next_exercise()
    assert ex is not None
    assert ex.exercise_type in (
        ExerciseType.FLASHCARD,
        ExerciseType.MULTIPLE_CHOICE,
        ExerciseType.CLOZE,
        ExerciseType.TRANSLATION_CLOZE,
    )


async def test_next_exercise_no_words(tmp_path):
    db = await Database.connect(tmp_path / "empty.db")
    u = await db.register_user("u1", "pass")
    s = Session(db, u.id, "en", "es")
    assert await s.next_exercise() is None
    await db.close()


async def test_answer_correct(session):
    ex = await session.next_exercise()
    assert ex is not None
    result = await session.answer(ex.word.word_to)
    assert result.correct is True


async def test_answer_incorrect(session):
    ex = await session.next_exercise()
    assert ex is not None
    result = await session.answer("wrong_answer_xyz")
    assert result.correct is False


async def test_answer_updates_progress(session):
    ex = await session.next_exercise()
    assert ex is not None
    word_id = ex.word.id
    await session.answer(ex.word.word_to)

    progress = await session.db.get_progress(1, word_id)
    assert progress is not None
    assert progress.state == CardState.LEARNING


async def test_answer_without_exercise_raises(session):
    with pytest.raises(RuntimeError, match="No active exercise"):
        await session.answer("gato")


async def test_full_session_flow(session):
    ex1 = await session.next_exercise()
    assert ex1 is not None
    r1 = await session.answer(ex1.word.word_to)
    assert r1.correct is True

    ex2 = await session.next_exercise()
    assert ex2 is not None
    r2 = await session.answer("definitely_wrong")
    assert r2.correct is False


# --- Session Stats Tests ---


async def test_summary_initial(session):
    stats = session.summary()
    assert stats.total == 0
    assert stats.correct == 0
    assert stats.incorrect == 0
    assert stats.streak == 0
    assert stats.best_streak == 0
    assert stats.accuracy_pct == 0.0


async def test_summary_after_correct(session):
    ex = await session.next_exercise()
    assert ex is not None
    await session.answer(ex.word.word_to)
    stats = session.summary()
    assert stats.total == 1
    assert stats.correct == 1
    assert stats.incorrect == 0
    assert stats.streak == 1
    assert stats.best_streak == 1
    assert stats.accuracy_pct == 100.0


async def test_summary_after_incorrect(session):
    ex = await session.next_exercise()
    assert ex is not None
    await session.answer("wrong_answer_xyz")
    stats = session.summary()
    assert stats.total == 1
    assert stats.correct == 0
    assert stats.incorrect == 1
    assert stats.streak == 0


async def test_summary_streak_resets(session):
    # correct
    ex = await session.next_exercise()
    await session.answer(ex.word.word_to)
    # correct
    ex = await session.next_exercise()
    await session.answer(ex.word.word_to)
    # incorrect — resets streak
    ex = await session.next_exercise()
    await session.answer("wrong_answer_xyz")

    stats = session.summary()
    assert stats.streak == 0
    assert stats.best_streak == 2
    assert stats.total == 3
    assert stats.correct == 2
    assert stats.incorrect == 1


async def test_summary_accuracy_pct(session):
    ex = await session.next_exercise()
    await session.answer(ex.word.word_to)
    ex = await session.next_exercise()
    await session.answer("wrong_answer_xyz")
    stats = session.summary()
    assert stats.accuracy_pct == 50.0


# --- Hint Tests ---


async def test_hint_returns_first_letter_and_length(session):
    ex = await session.next_exercise()
    assert ex is not None
    h = session.hint()
    expected = ex.word.word_to
    if ex.expected_answer:
        expected = ex.expected_answer
    assert h.first_letter == expected[0]
    assert h.word_length == len(expected)


async def test_hint_pattern_format(session):
    ex = await session.next_exercise()
    assert ex is not None
    h = session.hint()
    assert h.pattern[0] == h.first_letter
    assert h.pattern.count("_") == h.word_length - 1
    assert len(h.pattern) == h.word_length
    assert h.reveal_count == 1


async def test_hint_progressive_reveal(session):
    ex = await session.next_exercise()
    assert ex is not None
    expected = ex.word.word_to
    if ex.expected_answer:
        expected = ex.expected_answer
    h1 = session.hint()
    assert h1.reveal_count == 1
    assert h1.pattern == (
        expected[0] + "_" * (len(expected) - 1)
    )
    h2 = session.hint()
    assert h2.reveal_count == 2
    assert h2.pattern[:2] == expected[:2]
    assert h2.pattern.count("_") == len(expected) - 2


async def test_hint_reveal_caps_at_length(session):
    ex = await session.next_exercise()
    assert ex is not None
    expected = ex.word.word_to
    if ex.expected_answer:
        expected = ex.expected_answer
    for _ in range(len(expected) + 5):
        h = session.hint()
    assert h.reveal_count == len(expected)
    assert h.pattern == expected


async def test_hint_resets_on_new_exercise(session):
    await session.next_exercise()
    session.hint()
    session.hint()
    await session.answer("wrong")
    ex2 = await session.next_exercise()
    assert ex2 is not None
    h = session.hint()
    assert h.reveal_count == 1


async def test_hint_without_exercise_raises(session):
    with pytest.raises(RuntimeError, match="No active exercise"):
        session.hint()


async def test_hint_does_not_consume_exercise(session):
    ex = await session.next_exercise()
    assert ex is not None
    session.hint()
    # Can still answer after getting a hint
    result = await session.answer(ex.word.word_to)
    assert result is not None


async def test_hint_example_sentence_with_gender(tmp_path):
    database = await Database.connect(tmp_path / "hint.db")
    await database.register_user("u1", "pass")
    await database.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="book", word_to="libro",
            gender="m",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="house", word_to="casa",
            gender="f",
        ),
    ])
    s = Session(
        database, user_id=1,
        language_from="en", language_to="es",
    )
    await s.next_exercise()
    h = s.hint()
    assert h.example_sentence != ""
    assert "___" in h.example_sentence
    await database.close()


async def test_hint_no_example_sentence_for_definitions(
    definition_session,
):
    await definition_session.next_exercise()
    h = definition_session.hint()
    assert h.example_sentence == ""


# --- Skip Tests ---


async def test_skip_returns_exercise(session):
    ex = await session.next_exercise()
    assert ex is not None
    skipped = session.skip()
    assert skipped is ex


async def test_skip_does_not_affect_progress(session):
    ex = await session.next_exercise()
    assert ex is not None
    word_id = ex.word.id
    session.skip()
    assert await session.db.get_progress(1, word_id) is None


async def test_skip_does_not_affect_stats(session):
    ex = await session.next_exercise()
    assert ex is not None
    session.skip()
    stats = session.summary()
    assert stats.total == 0
    assert stats.correct == 0
    assert stats.incorrect == 0


async def test_skip_without_exercise_raises(session):
    with pytest.raises(RuntimeError, match="No active exercise"):
        session.skip()


async def test_skip_allows_next_exercise(session):
    ex1 = await session.next_exercise()
    assert ex1 is not None
    session.skip()
    ex2 = await session.next_exercise()
    assert ex2 is not None


# --- Definition Mode Tests ---


async def test_definition_next_exercise_valid_type(
    definition_session,
):
    ex = await definition_session.next_exercise()
    assert ex is not None
    assert ex.exercise_type in (
        ExerciseType.MULTIPLE_CHOICE,
        ExerciseType.REVERSE_FLASHCARD,
        ExerciseType.SELF_GRADED,
    )


async def test_definition_reverse_flashcard_answer(
    definition_db,
):
    session = Session(
        definition_db, 1, "en", "en",
    )
    # Keep generating until we get a reverse flashcard
    for _ in range(100):
        ex = await session.next_exercise()
        if (
            ex is not None
            and ex.exercise_type
            == ExerciseType.REVERSE_FLASHCARD
        ):
            result = await session.answer(ex.word.word_from)
            assert result.correct is True
            return
    pytest.skip("Did not get a reverse flashcard exercise")


async def test_definition_self_graded_answer(definition_db):
    session = Session(
        definition_db, 1, "en", "en",
    )
    for _ in range(100):
        ex = await session.next_exercise()
        if (
            ex is not None
            and ex.exercise_type
            == ExerciseType.SELF_GRADED
        ):
            result = await session.answer(quality=4)
            assert result.correct is True
            return
    pytest.skip("Did not get a self-graded exercise")


async def test_definition_self_graded_updates_progress(
    definition_db,
):
    session = Session(
        definition_db, 1, "en", "en",
    )
    for _ in range(100):
        ex = await session.next_exercise()
        if (
            ex is not None
            and ex.exercise_type
            == ExerciseType.SELF_GRADED
        ):
            word_id = ex.word.id
            await session.answer(quality=4)
            progress = await definition_db.get_progress(
                1, word_id,
            )
            assert progress is not None
            assert progress.state == CardState.LEARNING
            return
    pytest.skip("Did not get a self-graded exercise")


# --- quick_session Tests ---

_SAMPLE_WORDS = [
    {"word": "cat", "definition": "gato"},
    {"word": "dog", "definition": "perro"},
    {"word": "house", "definition": "casa"},
    {"word": "book", "definition": "libro"},
    {"word": "tree", "definition": "árbol"},
]


async def test_quick_session_from_json(tmp_path):
    vocab_file = tmp_path / "words.json"
    vocab_file.write_text(
        json.dumps(_SAMPLE_WORDS), encoding="utf-8",
    )
    s = await quick_session(
        vocab_file,
        language_from="en",
        language_to="es",
    )
    words = await s.db.get_words("en", "es")
    assert len(words) == 5
    assert isinstance(s, Session)
    await s.db.close()


async def test_quick_session_from_list(tmp_path):
    s = await quick_session(
        _SAMPLE_WORDS,
        db_path=tmp_path / "inline.db",
        language_from="en",
        language_to="es",
    )
    words = await s.db.get_words("en", "es")
    assert len(words) == 5
    assert isinstance(s, Session)
    await s.db.close()


async def test_quick_session_skips_reload(tmp_path):
    vocab_file = tmp_path / "words.json"
    vocab_file.write_text(
        json.dumps(_SAMPLE_WORDS), encoding="utf-8",
    )
    db_path = tmp_path / "shared.db"

    s1 = await quick_session(
        vocab_file,
        db_path=db_path,
        language_from="en",
        language_to="es",
    )
    await s1.db.close()

    s2 = await quick_session(
        vocab_file,
        db_path=db_path,
        language_from="en",
        language_to="es",
    )
    words = await s2.db.get_words("en", "es")
    assert len(words) == 5
    await s2.db.close()


async def test_quick_session_limit(tmp_path):
    vocab_file = tmp_path / "words.json"
    vocab_file.write_text(
        json.dumps(_SAMPLE_WORDS), encoding="utf-8",
    )
    s = await quick_session(
        vocab_file,
        language_from="en",
        language_to="es",
        limit=3,
    )
    words = await s.db.get_words("en", "es")
    assert len(words) == 3
    await s.db.close()


# --- Session Mode Tests ---


async def test_session_learn_new_mode(db_with_words):
    all_words = await db_with_words.get_words("en", "es")
    due_word = all_words[0]
    await db_with_words.upsert_progress(UserProgress(
        user_id=1,
        word_id=due_word.id,
        next_review=datetime(2020, 1, 1),
    ))

    s = Session(
        db_with_words, 1, "en", "es",
        mode=SessionMode.LEARN_NEW,
    )
    ex = await s.next_exercise()
    assert ex is not None
    assert ex.word.id != due_word.id


async def test_session_review_due_mode(db_with_words):
    all_words = await db_with_words.get_words("en", "es")
    due_word = all_words[0]
    await db_with_words.upsert_progress(UserProgress(
        user_id=1,
        word_id=due_word.id,
        next_review=datetime(2020, 1, 1),
    ))

    s = Session(
        db_with_words, 1, "en", "es",
        mode=SessionMode.REVIEW_DUE,
    )
    ex = await s.next_exercise()
    assert ex is not None
    assert ex.word.id == due_word.id


async def test_session_word_ids_filter(db_with_words):
    all_words = await db_with_words.get_words("en", "es")
    subset = [all_words[0].id, all_words[1].id]

    s = Session(
        db_with_words, 1, "en", "es",
        word_ids=subset,
    )
    seen_ids = set()
    for _ in range(10):
        ex = await s.next_exercise()
        if ex is None:
            break
        seen_ids.add(ex.word.id)
        await s.answer(ex.expected_answer or ex.word.word_to)
    assert seen_ids <= set(subset)


async def test_quick_session_list_requires_db_path():
    with pytest.raises(
        ValueError, match="db_path is required",
    ):
        await quick_session(
            _SAMPLE_WORDS,
            language_from="en",
            language_to="es",
        )


# --- Answer History Recording Tests ---


async def test_answer_records_history(session):
    ex = await session.next_exercise()
    assert ex is not None
    await session.answer(ex.word.word_to)
    history = await session.db.get_answer_history(1)
    assert len(history) == 1
    assert history[0].word_id == ex.word.id
    assert history[0].correct is True


async def test_answer_incorrect_records_history(session):
    ex = await session.next_exercise()
    assert ex is not None
    await session.answer("wrong_answer_xyz")
    history = await session.db.get_answer_history(1)
    assert len(history) == 1
    assert history[0].correct is False


async def test_answer_records_exercise_type(session):
    ex = await session.next_exercise()
    assert ex is not None
    await session.answer(ex.word.word_to)
    history = await session.db.get_answer_history(1)
    assert history[0].exercise_type == ex.exercise_type.value


async def test_answer_records_quality(session):
    ex = await session.next_exercise()
    assert ex is not None
    await session.answer(ex.word.word_to)
    history = await session.db.get_answer_history(1)
    assert history[0].quality == 5  # correct -> quality 5


async def test_multiple_answers_recorded(session):
    for _ in range(3):
        ex = await session.next_exercise()
        if ex is None:
            break
        await session.answer(ex.word.word_to)
    history = await session.db.get_answer_history(1)
    assert len(history) == 3


# --- Daily Limit Tests ---


async def test_session_respects_max_new_cards(db_with_words):
    config = ReviewConfig(max_new_cards=2)
    s = Session(
        db_with_words, 1, "en", "es",
        review_config=config,
    )
    served = []
    for _ in range(5):
        ex = await s.next_exercise()
        if ex is None:
            break
        served.append(ex)
        await s.answer(ex.word.word_to)
    # Only 2 new cards should be served (then they enter
    # LEARNING and are served as in-steps, which are uncapped)
    assert s._new_served == 2


async def test_session_respects_max_review_cards(
    db_with_words,
):
    all_words = await db_with_words.get_words("en", "es")
    for w in all_words:
        await db_with_words.upsert_progress(UserProgress(
            user_id=1,
            word_id=w.id,
            state=CardState.REVIEW,
            next_review=datetime(2020, 1, 1),
        ))

    config = ReviewConfig(max_review_cards=1)
    s = Session(
        db_with_words, 1, "en", "es",
        mode=SessionMode.REVIEW_DUE,
        review_config=config,
    )
    ex1 = await s.next_exercise()
    assert ex1 is not None
    assert s._review_served == 1
    await s.answer(ex1.word.word_to)

    # After answering, the card enters LEARNING (in-steps)
    # which is uncapped. But no more REVIEW cards should
    # be served beyond the limit of 1.
    # Get next — should be None since the answered card is
    # now in LEARNING (not due yet) and review cap is hit.
    ex2 = await s.next_exercise()
    assert ex2 is None
    assert s._review_served == 1


# --- Sibling Burying Tests ---


async def test_sibling_burying_skips_shown_words(
    db_with_words,
):
    s = Session(
        db_with_words, user_id=1,
        language_from="en", language_to="es",
    )
    seen_word_ids: set[int | None] = set()
    for _ in range(5):
        ex = await s.next_exercise()
        assert ex is not None
        assert ex.word.id not in seen_word_ids
        seen_word_ids.add(ex.word.id)
        await s.answer(
            ex.expected_answer or ex.word.word_to,
        )

    # All 5 words used up — next should be None
    assert await s.next_exercise() is None


async def test_quick_session_custom_keys(tmp_path):
    custom_words = [
        {"term": "cat", "meaning": "gato"},
        {"term": "dog", "meaning": "perro"},
    ]
    vocab_file = tmp_path / "custom.json"
    vocab_file.write_text(
        json.dumps(custom_words), encoding="utf-8",
    )
    s = await quick_session(
        vocab_file,
        language_from="en",
        language_to="es",
        word_from_key="term",
        word_to_key="meaning",
    )
    words = await s.db.get_words("en", "es")
    assert len(words) == 2
    assert words[0].word_from == "cat"
    await s.db.close()


# --- Session Snapshot Tests ---


async def test_snapshot_roundtrip(session):
    ex = await session.next_exercise()
    assert ex is not None
    await session.answer(ex.word.word_to)

    ex2 = await session.next_exercise()
    assert ex2 is not None
    session.hint()

    snap = session.snapshot()
    assert snap.user_id == 1
    assert snap.correct == 1
    assert snap.hint_count == 1
    assert snap.current_exercise is not None
    assert len(snap.buried_word_ids) == 2


async def test_save_and_restore(db_with_words):
    s1 = Session(
        db_with_words, 1, "en", "es",
    )
    ex = await s1.next_exercise()
    assert ex is not None
    await s1.answer(ex.word.word_to)

    ex2 = await s1.next_exercise()
    assert ex2 is not None
    s1.hint()

    await s1.save()

    s2 = await Session.restore(db_with_words, 1)
    assert s2 is not None
    assert s2._correct == 1
    assert s2._hint_count == 1
    assert s2._current_exercise is not None
    assert s2._current_exercise.word.id == ex2.word.id
    assert len(s2._buried_word_ids) == 2
    assert s2.language_from == "en"
    assert s2.language_to == "es"


async def test_restore_nonexistent(db_with_words):
    result = await Session.restore(db_with_words, 999)
    assert result is None


async def test_save_with_key(db_with_words):
    s1 = Session(db_with_words, 1, "en", "es")
    await s1.save(key="chat_123")

    s2 = Session(db_with_words, 1, "en", "es")
    ex = await s2.next_exercise()
    assert ex is not None
    await s2.answer(ex.word.word_to)
    await s2.save(key="chat_456")

    r1 = await Session.restore(
        db_with_words, 1, key="chat_123",
    )
    r2 = await Session.restore(
        db_with_words, 1, key="chat_456",
    )
    assert r1 is not None
    assert r2 is not None
    assert r1._correct == 0
    assert r2._correct == 1


async def test_save_overwrites_existing(db_with_words):
    s = Session(db_with_words, 1, "en", "es")
    await s.save()

    ex = await s.next_exercise()
    assert ex is not None
    await s.answer(ex.word.word_to)
    await s.save()

    restored = await Session.restore(db_with_words, 1)
    assert restored is not None
    assert restored._correct == 1


async def test_delete_session_snapshot(db_with_words):
    s = Session(db_with_words, 1, "en", "es")
    await s.save()

    deleted = await db_with_words.delete_session_snapshot(1)
    assert deleted is True

    deleted2 = await db_with_words.delete_session_snapshot(1)
    assert deleted2 is False

    restored = await Session.restore(db_with_words, 1)
    assert restored is None


async def test_restore_preserves_config(db_with_words):
    config = ReviewConfig(
        max_new_cards=5,
        learning_steps=[1, 5, 15],
    )
    s = Session(
        db_with_words, 1, "en", "es",
        review_config=config,
        mode=SessionMode.LEARN_NEW,
        word_ids=[1, 2],
    )
    await s.save()

    restored = await Session.restore(db_with_words, 1)
    assert restored is not None
    assert restored.mode == SessionMode.LEARN_NEW
    assert restored._word_ids == [1, 2]
    assert restored._review_config is not None
    assert restored._review_config.max_new_cards == 5
    assert restored._review_config.learning_steps == [
        1, 5, 15,
    ]


async def test_restore_continues_session(db_with_words):
    s1 = Session(db_with_words, 1, "en", "es")
    ex = await s1.next_exercise()
    assert ex is not None
    await s1.answer(ex.word.word_to)
    await s1.save()

    s2 = await Session.restore(db_with_words, 1)
    assert s2 is not None
    ex2 = await s2.next_exercise()
    assert ex2 is not None
    assert ex2.word.id != ex.word.id
    await s2.answer(ex2.word.word_to)

    stats = s2.summary()
    assert stats.correct == 2
    assert stats.total == 2
