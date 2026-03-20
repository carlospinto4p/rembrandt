"""Tests for rembrandt.session."""

import json

import pytest
import pytest_asyncio

from datetime import datetime

from rembrandt.db import Database
from rembrandt.models import (
    CardState,
    Concept,
    Exercise,
    ExerciseType,
    ReviewConfig,
    SessionMode,
    UserProgress,
)
from rembrandt.session import Session, quick_session

pytestmark = pytest.mark.asyncio


def _correct_answer(ex: Exercise) -> dict:
    """Return kwargs for `session.answer()` that
    produce a correct answer for any exercise type.
    """
    if ex.expected_answer:
        return {"text": ex.expected_answer}
    return {"text": ex.concept.back}


def _wrong_answer(ex: Exercise) -> dict:
    """Return kwargs for `session.answer()` that
    produce a wrong answer for any exercise type.
    """
    return {"text": "wrong_answer_xyz"}


@pytest_asyncio.fixture
async def session(db_with_concepts):
    return Session(db_with_concepts, user_id=1)


# --- Session Tests ---


async def test_next_exercise_returns_exercise(session):
    ex = await session.next_exercise()
    assert ex is not None
    assert ex.exercise_type in (
        ExerciseType.FLASHCARD,
        ExerciseType.MULTIPLE_CHOICE,
    )


async def test_next_exercise_no_concepts(tmp_path):
    db = await Database.connect(
        tmp_path / "empty.db",
    )
    u = await db.register_user("u1", "pass")
    s = Session(db, u.id)
    assert await s.next_exercise() is None
    await db.close()


async def test_answer_correct(session):
    ex = await session.next_exercise()
    assert ex is not None
    result = await session.answer(
        **_correct_answer(ex),
    )
    assert result.correct is True


async def test_answer_incorrect(session):
    ex = await session.next_exercise()
    assert ex is not None
    result = await session.answer(
        **_wrong_answer(ex),
    )
    assert result.correct is False


async def test_answer_updates_progress(session):
    ex = await session.next_exercise()
    assert ex is not None
    concept_id = ex.concept.id
    await session.answer(**_correct_answer(ex))

    progress = await session.db.get_progress(
        1, concept_id,
    )
    assert progress is not None
    assert progress.state == CardState.LEARNING


async def test_answer_without_exercise_raises(session):
    with pytest.raises(
        RuntimeError, match="No active exercise",
    ):
        await session.answer("anything")


async def test_full_session_flow(session):
    ex1 = await session.next_exercise()
    assert ex1 is not None
    r1 = await session.answer(**_correct_answer(ex1))
    assert r1.correct is True

    ex2 = await session.next_exercise()
    assert ex2 is not None
    r2 = await session.answer(**_wrong_answer(ex2))
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
    await session.answer(**_correct_answer(ex))
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
    await session.answer(**_wrong_answer(ex))
    stats = session.summary()
    assert stats.total == 1
    assert stats.correct == 0
    assert stats.incorrect == 1
    assert stats.streak == 0


async def test_summary_streak_resets(session):
    ex = await session.next_exercise()
    await session.answer(**_correct_answer(ex))
    ex = await session.next_exercise()
    await session.answer(**_correct_answer(ex))
    ex = await session.next_exercise()
    await session.answer(**_wrong_answer(ex))

    stats = session.summary()
    assert stats.streak == 0
    assert stats.best_streak == 2
    assert stats.total == 3
    assert stats.correct == 2
    assert stats.incorrect == 1


async def test_summary_accuracy_pct(session):
    ex = await session.next_exercise()
    await session.answer(**_correct_answer(ex))
    ex = await session.next_exercise()
    await session.answer(**_wrong_answer(ex))
    stats = session.summary()
    assert stats.accuracy_pct == 50.0


# --- Hint Tests ---


async def test_hint_returns_first_letter_and_length(
    session,
):
    ex = await session.next_exercise()
    assert ex is not None
    h = session.hint()
    expected = ex.concept.back
    if ex.expected_answer:
        expected = ex.expected_answer
    assert h.first_letter == expected[0]
    assert h.word_length == len(expected)


async def test_hint_pattern_format(session):
    ex = await session.next_exercise()
    assert ex is not None
    h = session.hint()
    assert h.pattern[0] == h.first_letter
    assert h.pattern.count("_") == (
        h.word_length - 1
    )
    assert len(h.pattern) == h.word_length
    assert h.reveal_count == 1


async def test_hint_progressive_reveal(session):
    ex = await session.next_exercise()
    assert ex is not None
    expected = ex.concept.back
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
    assert h2.pattern.count("_") == (
        len(expected) - 2
    )


async def test_hint_reveal_caps_at_length(session):
    ex = await session.next_exercise()
    assert ex is not None
    expected = ex.concept.back
    if ex.expected_answer:
        expected = ex.expected_answer
    for _ in range(len(expected) + 5):
        h = session.hint()
    assert h.reveal_count == len(expected)
    assert h.pattern == expected


async def test_hint_resets_on_new_exercise(session):
    ex = await session.next_exercise()
    session.hint()
    session.hint()
    await session.answer(**_wrong_answer(ex))
    ex2 = await session.next_exercise()
    assert ex2 is not None
    h = session.hint()
    assert h.reveal_count == 1


async def test_hint_without_exercise_raises(session):
    with pytest.raises(
        RuntimeError, match="No active exercise",
    ):
        session.hint()


async def test_hint_does_not_consume_exercise(
    session,
):
    ex = await session.next_exercise()
    assert ex is not None
    session.hint()
    result = await session.answer(**_correct_answer(ex))
    assert result is not None


async def test_hint_context_field(tmp_path):
    database = await Database.connect(
        tmp_path / "hint.db",
    )
    await database.register_user("u1", "pass")
    await database.add_concepts([
        Concept(
            front="cat", back="gato",
            context="A small furry animal",
        ),
        Concept(
            front="dog", back="perro",
            context="A loyal pet",
        ),
    ])
    s = Session(database, user_id=1)
    await s.next_exercise()
    h = s.hint()
    # Context should be populated from concept
    assert isinstance(h.context, str)
    await database.close()


# --- Skip Tests ---


async def test_skip_returns_exercise(session):
    ex = await session.next_exercise()
    assert ex is not None
    skipped = session.skip()
    assert skipped is ex


async def test_skip_does_not_affect_progress(
    session,
):
    ex = await session.next_exercise()
    assert ex is not None
    concept_id = ex.concept.id
    session.skip()
    assert (
        await session.db.get_progress(1, concept_id)
    ) is None


async def test_skip_does_not_affect_stats(session):
    ex = await session.next_exercise()
    assert ex is not None
    session.skip()
    stats = session.summary()
    assert stats.total == 0
    assert stats.correct == 0
    assert stats.incorrect == 0


async def test_skip_without_exercise_raises(session):
    with pytest.raises(
        RuntimeError, match="No active exercise",
    ):
        session.skip()


async def test_skip_allows_next_exercise(session):
    ex1 = await session.next_exercise()
    assert ex1 is not None
    session.skip()
    ex2 = await session.next_exercise()
    assert ex2 is not None


# --- quick_session Tests ---

_SAMPLE_CONCEPTS = [
    {"front": "cat", "back": "gato"},
    {"front": "dog", "back": "perro"},
    {"front": "house", "back": "casa"},
    {"front": "book", "back": "libro"},
    {"front": "tree", "back": "arbol"},
]


async def test_quick_session_from_json(tmp_path):
    vocab_file = tmp_path / "concepts.json"
    vocab_file.write_text(
        json.dumps(_SAMPLE_CONCEPTS),
        encoding="utf-8",
    )
    s = await quick_session(vocab_file)
    concepts = await s.db.get_concepts()
    assert len(concepts) == 5
    assert isinstance(s, Session)
    await s.db.close()


async def test_quick_session_from_list(tmp_path):
    s = await quick_session(
        _SAMPLE_CONCEPTS,
        db_path=tmp_path / "inline.db",
    )
    concepts = await s.db.get_concepts()
    assert len(concepts) == 5
    assert isinstance(s, Session)
    await s.db.close()


async def test_quick_session_skips_reload(tmp_path):
    vocab_file = tmp_path / "concepts.json"
    vocab_file.write_text(
        json.dumps(_SAMPLE_CONCEPTS),
        encoding="utf-8",
    )
    db_path = tmp_path / "shared.db"

    s1 = await quick_session(
        vocab_file, db_path=db_path,
    )
    await s1.db.close()

    s2 = await quick_session(
        vocab_file, db_path=db_path,
    )
    concepts = await s2.db.get_concepts()
    assert len(concepts) == 5
    await s2.db.close()


async def test_quick_session_limit(tmp_path):
    vocab_file = tmp_path / "concepts.json"
    vocab_file.write_text(
        json.dumps(_SAMPLE_CONCEPTS),
        encoding="utf-8",
    )
    s = await quick_session(
        vocab_file, limit=3,
    )
    concepts = await s.db.get_concepts()
    assert len(concepts) == 3
    await s.db.close()


async def test_quick_session_custom_keys(tmp_path):
    custom_items = [
        {"question": "What is ML?",
         "answer": "Machine learning"},
        {"question": "What is AI?",
         "answer": "Artificial intelligence"},
    ]
    vocab_file = tmp_path / "custom.json"
    vocab_file.write_text(
        json.dumps(custom_items),
        encoding="utf-8",
    )
    s = await quick_session(
        vocab_file,
        front_key="question",
        back_key="answer",
    )
    concepts = await s.db.get_concepts()
    assert len(concepts) == 2
    assert concepts[0].front == "What is ML?"
    await s.db.close()


async def test_quick_session_list_requires_db_path():
    with pytest.raises(
        ValueError, match="db_path is required",
    ):
        await quick_session(_SAMPLE_CONCEPTS)


# --- Session Mode Tests ---


async def test_session_learn_new_mode(
    db_with_concepts,
):
    all_concepts = await db_with_concepts.get_concepts()
    due_concept = all_concepts[0]
    await db_with_concepts.upsert_progress(
        UserProgress(
            user_id=1,
            concept_id=due_concept.id,
            next_review=datetime(2020, 1, 1),
        ),
    )

    s = Session(
        db_with_concepts, 1,
        mode=SessionMode.LEARN_NEW,
    )
    ex = await s.next_exercise()
    assert ex is not None
    assert ex.concept.id != due_concept.id


async def test_session_review_due_mode(
    db_with_concepts,
):
    all_concepts = await db_with_concepts.get_concepts()
    due_concept = all_concepts[0]
    await db_with_concepts.upsert_progress(
        UserProgress(
            user_id=1,
            concept_id=due_concept.id,
            next_review=datetime(2020, 1, 1),
        ),
    )

    s = Session(
        db_with_concepts, 1,
        mode=SessionMode.REVIEW_DUE,
    )
    ex = await s.next_exercise()
    assert ex is not None
    assert ex.concept.id == due_concept.id


async def test_session_concept_ids_filter(
    db_with_concepts,
):
    all_concepts = await db_with_concepts.get_concepts()
    subset = [
        all_concepts[0].id, all_concepts[1].id,
    ]

    s = Session(
        db_with_concepts, 1,
        concept_ids=subset,
    )
    seen_ids = set()
    for _ in range(10):
        ex = await s.next_exercise()
        if ex is None:
            break
        seen_ids.add(ex.concept.id)
        await s.answer(**_correct_answer(ex))
    assert seen_ids <= set(subset)


# --- Answer History Recording Tests ---


async def test_answer_records_history(session):
    ex = await session.next_exercise()
    assert ex is not None
    await session.answer(**_correct_answer(ex))
    history = await session.db.get_answer_history(1)
    assert len(history) == 1
    assert history[0].concept_id == ex.concept.id
    assert history[0].correct is True


async def test_answer_incorrect_records_history(
    session,
):
    ex = await session.next_exercise()
    assert ex is not None
    await session.answer(**_wrong_answer(ex))
    history = await session.db.get_answer_history(1)
    assert len(history) == 1
    assert history[0].correct is False


async def test_answer_records_exercise_type(session):
    ex = await session.next_exercise()
    assert ex is not None
    await session.answer(**_correct_answer(ex))
    history = await session.db.get_answer_history(1)
    assert (
        history[0].exercise_type
        == ex.exercise_type.value
    )


async def test_answer_records_quality(session):
    ex = await session.next_exercise()
    assert ex is not None
    await session.answer(**_correct_answer(ex))
    history = await session.db.get_answer_history(1)
    assert history[0].quality == 5


async def test_multiple_answers_recorded(session):
    for _ in range(3):
        ex = await session.next_exercise()
        if ex is None:
            break
        await session.answer(**_correct_answer(ex))
    history = await session.db.get_answer_history(1)
    assert len(history) == 3


# --- Daily Limit Tests ---


async def test_session_respects_max_new_cards(
    db_with_concepts,
):
    config = ReviewConfig(max_new_cards=2)
    s = Session(
        db_with_concepts, 1,
        review_config=config,
    )
    served = []
    for _ in range(5):
        ex = await s.next_exercise()
        if ex is None:
            break
        served.append(ex)
        await s.answer(**_correct_answer(ex))
    assert s._new_served == 2


async def test_session_respects_max_review_cards(
    db_with_concepts,
):
    all_concepts = (
        await db_with_concepts.get_concepts()
    )
    for c in all_concepts:
        await db_with_concepts.upsert_progress(
            UserProgress(
                user_id=1,
                concept_id=c.id,
                state=CardState.REVIEW,
                next_review=datetime(2020, 1, 1),
            ),
        )

    config = ReviewConfig(max_review_cards=1)
    s = Session(
        db_with_concepts, 1,
        mode=SessionMode.REVIEW_DUE,
        review_config=config,
    )
    ex1 = await s.next_exercise()
    assert ex1 is not None
    assert s._review_served == 1
    await s.answer(**_correct_answer(ex1))

    ex2 = await s.next_exercise()
    assert ex2 is None
    assert s._review_served == 1


# --- Sibling Burying Tests ---


async def test_sibling_burying_skips_shown_concepts(
    db_with_concepts,
):
    s = Session(db_with_concepts, user_id=1)
    seen_ids: set[int | None] = set()
    for _ in range(5):
        ex = await s.next_exercise()
        assert ex is not None
        assert ex.concept.id not in seen_ids
        seen_ids.add(ex.concept.id)
        await s.answer(**_correct_answer(ex))

    assert await s.next_exercise() is None


# --- Session Snapshot Tests ---


async def test_snapshot_roundtrip(session):
    ex = await session.next_exercise()
    assert ex is not None
    await session.answer(**_correct_answer(ex))

    ex2 = await session.next_exercise()
    assert ex2 is not None
    session.hint()

    snap = session.snapshot()
    assert snap.user_id == 1
    assert snap.correct == 1
    assert snap.hint_count == 1
    assert snap.current_exercise is not None
    assert len(snap.buried_concept_ids) == 2


async def test_save_and_restore(db_with_concepts):
    s1 = Session(db_with_concepts, 1)
    ex = await s1.next_exercise()
    assert ex is not None
    await s1.answer(**_correct_answer(ex))

    ex2 = await s1.next_exercise()
    assert ex2 is not None
    s1.hint()

    await s1.save()

    s2 = await Session.restore(db_with_concepts, 1)
    assert s2 is not None
    assert s2._correct == 1
    assert s2._hint_count == 1
    assert s2._current_exercise is not None
    assert (
        s2._current_exercise.concept.id
        == ex2.concept.id
    )
    assert len(s2._buried_concept_ids) == 2


async def test_restore_nonexistent(db_with_concepts):
    result = await Session.restore(
        db_with_concepts, 999,
    )
    assert result is None


async def test_save_with_key(db_with_concepts):
    s1 = Session(db_with_concepts, 1)
    await s1.save(key="chat_123")

    s2 = Session(db_with_concepts, 1)
    ex = await s2.next_exercise()
    assert ex is not None
    await s2.answer(**_correct_answer(ex))
    await s2.save(key="chat_456")

    r1 = await Session.restore(
        db_with_concepts, 1, key="chat_123",
    )
    r2 = await Session.restore(
        db_with_concepts, 1, key="chat_456",
    )
    assert r1 is not None
    assert r2 is not None
    assert r1._correct == 0
    assert r2._correct == 1


async def test_save_overwrites_existing(
    db_with_concepts,
):
    s = Session(db_with_concepts, 1)
    await s.save()

    ex = await s.next_exercise()
    assert ex is not None
    await s.answer(**_correct_answer(ex))
    await s.save()

    restored = await Session.restore(
        db_with_concepts, 1,
    )
    assert restored is not None
    assert restored._correct == 1


async def test_delete_session_snapshot(
    db_with_concepts,
):
    s = Session(db_with_concepts, 1)
    await s.save()

    deleted = (
        await db_with_concepts
        .delete_session_snapshot(1)
    )
    assert deleted is True

    deleted2 = (
        await db_with_concepts
        .delete_session_snapshot(1)
    )
    assert deleted2 is False

    restored = await Session.restore(
        db_with_concepts, 1,
    )
    assert restored is None


async def test_restore_preserves_config(
    db_with_concepts,
):
    config = ReviewConfig(
        max_new_cards=5,
        learning_steps=[1, 5, 15],
    )
    s = Session(
        db_with_concepts, 1,
        review_config=config,
        mode=SessionMode.LEARN_NEW,
        concept_ids=[1, 2],
    )
    await s.save()

    restored = await Session.restore(
        db_with_concepts, 1,
    )
    assert restored is not None
    assert restored.mode == SessionMode.LEARN_NEW
    assert restored._concept_ids == [1, 2]
    assert restored._review_config is not None
    assert (
        restored._review_config.max_new_cards == 5
    )
    assert (
        restored._review_config.learning_steps
        == [1, 5, 15]
    )


async def test_restore_continues_session(
    db_with_concepts,
):
    s1 = Session(db_with_concepts, 1)
    ex = await s1.next_exercise()
    assert ex is not None
    await s1.answer(**_correct_answer(ex))
    await s1.save()

    s2 = await Session.restore(
        db_with_concepts, 1,
    )
    assert s2 is not None
    ex2 = await s2.next_exercise()
    assert ex2 is not None
    assert ex2.concept.id != ex.concept.id
    await s2.answer(**_correct_answer(ex2))

    stats = s2.summary()
    assert stats.correct == 2
    assert stats.total == 2
