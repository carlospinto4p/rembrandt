"""Tests for rembrandt.topics."""

import json

from datetime import datetime

import pytest

from rembrandt.db import Database
from rembrandt.models import (
    CardState,
    Concept,
    Topic,
    UserProgress,
)
from rembrandt.topics import load_topics, topic_progress

pytestmark = pytest.mark.asyncio


# --- Helpers ---


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


async def _make_db_with_topic(tmp_path):
    """Create a DB with 4 concepts and a topic."""
    db = await Database.connect(
        tmp_path / "progress.db",
    )
    await db.register_user("u1", "pass")
    concepts = await db.add_concepts(
        [
            Concept(front="cat", back="gato"),
            Concept(front="dog", back="perro"),
            Concept(front="house", back="casa"),
            Concept(front="book", back="libro"),
        ]
    )
    concept_ids = [c.id for c in concepts]
    topic = Topic(
        id=1,
        title="Test Topic",
        concept_count=4,
        concept_ids=concept_ids,
    )
    return db, topic, concepts


# --- load_topics Tests ---


async def test_load_topics_resolves_ids(tmp_path):
    db = await Database.connect(
        tmp_path / "test.db",
    )
    concepts = await db.add_concepts(
        [
            Concept(front="cat", back="gato"),
            Concept(front="dog", back="perro"),
            Concept(front="house", back="casa"),
        ]
    )

    topics_data = [
        {
            "title": "Topic 1",
            "concept_ids": [
                concepts[0].id,
                concepts[1].id,
                concepts[2].id,
            ],
        },
    ]
    _write_json(
        tmp_path / "topics.json",
        topics_data,
    )

    result = await load_topics(
        tmp_path / "topics.json",
        db,
    )
    assert len(result) == 1
    assert result[0].title == "Topic 1"
    assert result[0].concept_count == 3
    assert result[0].concept_ids == [
        concepts[0].id,
        concepts[1].id,
        concepts[2].id,
    ]
    await db.close()


async def test_load_topics_preserves_order(
    tmp_path,
):
    db = await Database.connect(
        tmp_path / "test.db",
    )
    concepts = await db.add_concepts(
        [
            Concept(front="cat", back="gato"),
            Concept(front="dog", back="perro"),
            Concept(front="house", back="casa"),
        ]
    )

    topics_data = [
        {
            "title": "Reversed",
            "concept_ids": [
                concepts[2].id,
                concepts[0].id,
                concepts[1].id,
            ],
        },
    ]
    _write_json(
        tmp_path / "topics.json",
        topics_data,
    )

    result = await load_topics(
        tmp_path / "topics.json",
        db,
    )
    assert result[0].concept_ids == [
        concepts[2].id,
        concepts[0].id,
        concepts[1].id,
    ]
    await db.close()


async def test_load_topics_empty_input(tmp_path):
    _write_json(tmp_path / "topics.json", [])

    db = await Database.connect(
        tmp_path / "test.db",
    )
    result = await load_topics(
        tmp_path / "topics.json",
        db,
    )
    assert result == []
    await db.close()


async def test_load_topics_with_metadata(tmp_path):
    db = await Database.connect(
        tmp_path / "test.db",
    )
    concepts = await db.add_concepts(
        [
            Concept(front="cat", back="gato"),
        ]
    )

    topics_data = [
        {
            "title": "Animals",
            "description": "Animal vocabulary",
            "tags": ["animals"],
            "concept_ids": [concepts[0].id],
        },
    ]
    _write_json(
        tmp_path / "topics.json",
        topics_data,
    )

    result = await load_topics(
        tmp_path / "topics.json",
        db,
    )
    assert result[0].description == ("Animal vocabulary")
    assert result[0].tags == ["animals"]
    await db.close()


# --- topic_progress Tests ---


async def test_topic_progress_no_progress(tmp_path):
    db, topic, _ = await _make_db_with_topic(
        tmp_path,
    )
    tp = await topic_progress(db, 1, topic)
    assert tp.concepts_total == 4
    assert tp.concepts_studied == 0
    assert tp.concepts_mastered == 0
    assert tp.completion_pct == 0.0
    assert tp.mastery_pct == 0.0
    await db.close()


async def test_topic_progress_partial(tmp_path):
    db, topic, concepts = await _make_db_with_topic(tmp_path)
    await db.upsert_progress(
        UserProgress(
            user_id=1,
            concept_id=concepts[0].id,
            repetitions=1,
            next_review=datetime(2026, 1, 1),
        )
    )
    await db.upsert_progress(
        UserProgress(
            user_id=1,
            concept_id=concepts[1].id,
            repetitions=2,
            next_review=datetime(2026, 1, 1),
        )
    )
    tp = await topic_progress(db, 1, topic)
    assert tp.concepts_studied == 2
    assert tp.concepts_mastered == 0
    assert tp.completion_pct == 50.0
    assert tp.mastery_pct == 0.0
    await db.close()


async def test_topic_progress_mastered(tmp_path):
    db, topic, concepts = await _make_db_with_topic(tmp_path)
    await db.upsert_progress(
        UserProgress(
            user_id=1,
            concept_id=concepts[0].id,
            repetitions=3,
            state=CardState.REVIEW,
            next_review=datetime(2026, 1, 1),
        )
    )
    await db.upsert_progress(
        UserProgress(
            user_id=1,
            concept_id=concepts[1].id,
            repetitions=5,
            state=CardState.REVIEW,
            next_review=datetime(2026, 1, 1),
        )
    )
    tp = await topic_progress(db, 1, topic)
    assert tp.concepts_studied == 2
    assert tp.concepts_mastered == 2
    assert tp.completion_pct == 50.0
    assert tp.mastery_pct == 50.0
    await db.close()


async def test_topic_progress_full_completion(
    tmp_path,
):
    db, topic, concepts = await _make_db_with_topic(tmp_path)
    for c in concepts:
        await db.upsert_progress(
            UserProgress(
                user_id=1,
                concept_id=c.id,
                repetitions=1,
                next_review=datetime(2026, 1, 1),
            )
        )
    tp = await topic_progress(db, 1, topic)
    assert tp.concepts_studied == 4
    assert tp.completion_pct == 100.0
    await db.close()


async def test_topic_progress_empty_topic(tmp_path):
    db = await Database.connect(
        tmp_path / "empty.db",
    )
    await db.register_user("u1", "pass")
    topic = Topic(
        id=1,
        title="Empty",
        concept_count=0,
        concept_ids=[],
    )
    tp = await topic_progress(db, 1, topic)
    assert tp.concepts_total == 0
    assert tp.completion_pct == 0.0
    assert tp.mastery_pct == 0.0
    await db.close()
