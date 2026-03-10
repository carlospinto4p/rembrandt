"""Tests for rembrandt.lessons."""

import json

from datetime import datetime

import pytest

from rembrandt.db import Database
from rembrandt.lessons import lesson_progress, load_lessons
from rembrandt.models import (
    CardState,
    Lesson,
    UserProgress,
    Word,
)

pytestmark = pytest.mark.asyncio


# --- Helpers ---


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _make_vocab(ranks):
    """Build a minimal vocab list from rank numbers."""
    return [
        {
            "rank": r,
            "word": f"word_{r}",
            "definition": f"def_{r}",
            "tags": [],
            "cefr": "A1",
        }
        for r in ranks
    ]


def _make_lesson(title, ranks, **kwargs):
    """Build a minimal lesson entry."""
    entry = {
        "title": title,
        "language_from": "en",
        "language_to": "es",
        "word_ranks": ranks,
        **kwargs,
    }
    return entry


async def _make_db_with_lesson(tmp_path):
    """Create a DB with 4 words and a lesson."""
    db = await Database.connect(
        tmp_path / "progress.db",
    )
    await db.register_user("u1", "pass")
    words = await db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="dog", word_to="perro",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="house", word_to="casa",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="book", word_to="libro",
        ),
    ])
    word_ids = [w.id for w in words]
    lesson = Lesson(
        id=1,
        title="Test Lesson",
        language_from="en",
        language_to="es",
        word_count=4,
        word_ids=word_ids,
    )
    return db, lesson, words


# --- Tests ---


async def test_load_lessons_resolves_ranks(tmp_path):
    vocab = _make_vocab([1, 2, 3])
    _write_json(tmp_path / "vocab.json", vocab)

    db = await Database.connect(tmp_path / "test.db")
    words = await db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="def_1", word_to="word_1",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="def_2", word_to="word_2",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="def_3", word_to="word_3",
        ),
    ])

    lessons_data = [
        _make_lesson("Lesson 1", [1, 2, 3]),
    ]
    _write_json(tmp_path / "lessons.json", lessons_data)

    result = await load_lessons(
        tmp_path / "lessons.json",
        tmp_path / "vocab.json",
        db,
        language_from="en",
        language_to="es",
    )
    assert len(result) == 1
    assert result[0].title == "Lesson 1"
    assert result[0].word_count == 3
    assert result[0].word_ids == [
        words[0].id, words[1].id, words[2].id,
    ]
    await db.close()


async def test_load_lessons_preserves_order(tmp_path):
    vocab = _make_vocab([1, 2, 3])
    _write_json(tmp_path / "vocab.json", vocab)

    db = await Database.connect(tmp_path / "test.db")
    words = await db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="def_1", word_to="word_1",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="def_2", word_to="word_2",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="def_3", word_to="word_3",
        ),
    ])

    lessons_data = [
        _make_lesson("Reversed", [3, 1, 2]),
    ]
    _write_json(tmp_path / "lessons.json", lessons_data)

    result = await load_lessons(
        tmp_path / "lessons.json",
        tmp_path / "vocab.json",
        db,
        language_from="en",
        language_to="es",
    )
    assert result[0].word_ids == [
        words[2].id, words[0].id, words[1].id,
    ]
    await db.close()


async def test_load_lessons_skips_unresolved_ranks(
    tmp_path,
):
    vocab = _make_vocab([1, 2])
    _write_json(tmp_path / "vocab.json", vocab)

    db = await Database.connect(tmp_path / "test.db")
    await db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="def_1", word_to="word_1",
        ),
    ])

    lessons_data = [
        _make_lesson("Partial", [1, 2, 99]),
    ]
    _write_json(tmp_path / "lessons.json", lessons_data)

    result = await load_lessons(
        tmp_path / "lessons.json",
        tmp_path / "vocab.json",
        db,
        language_from="en",
        language_to="es",
    )
    assert result[0].word_count == 1
    await db.close()


async def test_load_lessons_empty_input(tmp_path):
    _write_json(tmp_path / "vocab.json", [])
    _write_json(tmp_path / "lessons.json", [])

    db = await Database.connect(tmp_path / "test.db")
    result = await load_lessons(
        tmp_path / "lessons.json",
        tmp_path / "vocab.json",
        db,
        language_from="en",
        language_to="es",
    )
    assert result == []
    await db.close()


# --- Lesson Progress Tests ---


async def test_lesson_progress_no_progress(tmp_path):
    db, lesson, _ = await _make_db_with_lesson(tmp_path)
    lp = await lesson_progress(db, 1, lesson)
    assert lp.words_total == 4
    assert lp.words_studied == 0
    assert lp.words_mastered == 0
    assert lp.completion_pct == 0.0
    assert lp.mastery_pct == 0.0
    await db.close()


async def test_lesson_progress_partial(tmp_path):
    db, lesson, words = (
        await _make_db_with_lesson(tmp_path)
    )
    await db.upsert_progress(UserProgress(
        user_id=1,
        word_id=words[0].id,
        repetitions=1,
        next_review=datetime(2026, 1, 1),
    ))
    await db.upsert_progress(UserProgress(
        user_id=1,
        word_id=words[1].id,
        repetitions=2,
        next_review=datetime(2026, 1, 1),
    ))
    lp = await lesson_progress(db, 1, lesson)
    assert lp.words_studied == 2
    assert lp.words_mastered == 0
    assert lp.completion_pct == 50.0
    assert lp.mastery_pct == 0.0
    await db.close()


async def test_lesson_progress_mastered(tmp_path):
    db, lesson, words = (
        await _make_db_with_lesson(tmp_path)
    )
    await db.upsert_progress(UserProgress(
        user_id=1,
        word_id=words[0].id,
        repetitions=3,
        state=CardState.REVIEW,
        next_review=datetime(2026, 1, 1),
    ))
    await db.upsert_progress(UserProgress(
        user_id=1,
        word_id=words[1].id,
        repetitions=5,
        state=CardState.REVIEW,
        next_review=datetime(2026, 1, 1),
    ))
    lp = await lesson_progress(db, 1, lesson)
    assert lp.words_studied == 2
    assert lp.words_mastered == 2
    assert lp.completion_pct == 50.0
    assert lp.mastery_pct == 50.0
    await db.close()


async def test_lesson_progress_full_completion(
    tmp_path,
):
    db, lesson, words = (
        await _make_db_with_lesson(tmp_path)
    )
    for w in words:
        await db.upsert_progress(UserProgress(
            user_id=1,
            word_id=w.id,
            repetitions=1,
            next_review=datetime(2026, 1, 1),
        ))
    lp = await lesson_progress(db, 1, lesson)
    assert lp.words_studied == 4
    assert lp.completion_pct == 100.0
    await db.close()


async def test_lesson_progress_empty_lesson(tmp_path):
    db = await Database.connect(tmp_path / "empty.db")
    await db.register_user("u1", "pass")
    lesson = Lesson(
        id=1,
        title="Empty",
        language_from="en",
        language_to="es",
        word_count=0,
        word_ids=[],
    )
    lp = await lesson_progress(db, 1, lesson)
    assert lp.words_total == 0
    assert lp.completion_pct == 0.0
    assert lp.mastery_pct == 0.0
    await db.close()
