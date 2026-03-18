"""Tests for rembrandt.db_postgres.

These tests require a running PostgreSQL instance. They are
automatically skipped when PostgreSQL is not available.

To run::

    docker compose up -d
    uv run pytest tests/unit/test_db_postgres.py -v
"""

from datetime import datetime

import pytest

try:
    import psycopg
    _PG_AVAILABLE = True
except ImportError:
    _PG_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _PG_AVAILABLE,
    reason="psycopg not installed",
)

_DSN = (
    "postgresql://rembrandt:rembrandt"
    "@localhost/rembrandt"
)


def _pg_available() -> bool:
    """Check if PostgreSQL is reachable."""
    if not _PG_AVAILABLE:
        return False
    try:
        conn = psycopg.connect(_DSN)
        conn.close()
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.skipif(
        not _pg_available(),
        reason="PostgreSQL not available",
    ),
    pytest.mark.asyncio,
]


@pytest.fixture
def pg_db():
    """Fresh PostgreSQL database for each test.

    Drops and recreates all tables to ensure
    isolation.
    """
    from rembrandt.db_postgres import (
        PostgresDatabase,
    )

    conn = psycopg.connect(_DSN, autocommit=True)
    with conn.cursor() as cur:
        cur.execute(
            "DROP TABLE IF EXISTS "
            "answer_history, topic_concepts, "
            "topics, progress, concepts, "
            "session_snapshots, "
            "conversation_states, "
            "user_sessions, users "
            "CASCADE"
        )
    conn.close()

    import asyncio
    db = asyncio.get_event_loop().run_until_complete(
        PostgresDatabase.connect(_DSN),
    )
    asyncio.get_event_loop().run_until_complete(
        db.register_user("u1", "pass"),
    )
    yield db
    asyncio.get_event_loop().run_until_complete(
        db.close(),
    )


# --- Concept CRUD Tests ---


async def test_add_concept(pg_db):
    concept = await pg_db.add_concept(
        "What is ML?", "Machine learning",
    )
    assert concept.id is not None
    assert concept.front == "What is ML?"
    assert concept.back == "Machine learning"


async def test_add_concepts_bulk(pg_db):
    from rembrandt.models import Concept

    concepts = await pg_db.add_concepts([
        Concept(front="cat", back="gato"),
        Concept(front="dog", back="perro"),
        Concept(front="house", back="casa"),
    ])
    assert len(concepts) == 3
    assert all(c.id is not None for c in concepts)
    assert concepts[0].front == "cat"
    assert concepts[2].back == "casa"


async def test_get_concepts_empty(pg_db):
    result = await pg_db.get_concepts()
    assert result == []


async def test_add_concept_with_tags(pg_db):
    concept = await pg_db.add_concept(
        "bread", "pan", tags=["food"],
    )
    assert concept.tags == ["food"]
    loaded = await pg_db.get_concepts()
    assert loaded[0].tags == ["food"]


async def test_tags_default_empty(pg_db):
    await pg_db.add_concept("cat", "gato")
    loaded = await pg_db.get_concepts()
    assert loaded[0].tags == []


async def test_update_concept(pg_db):
    concept = await pg_db.add_concept(
        "cat", "gato",
    )
    updated = await pg_db.update_concept(
        concept.model_copy(
            update={"back": "gatito"},
        ),
    )
    assert updated.back == "gatito"
    loaded = await pg_db.get_concepts()
    assert loaded[0].back == "gatito"


async def test_update_concept_not_found_raises(
    pg_db,
):
    from rembrandt.models import Concept

    concept = Concept(
        id=999, front="cat", back="gato",
    )
    with pytest.raises(
        ValueError, match="not found",
    ):
        await pg_db.update_concept(concept)


async def test_delete_concept(pg_db):
    concept = await pg_db.add_concept(
        "cat", "gato",
    )
    await pg_db.delete_concept(concept.id)
    assert await pg_db.get_concepts() == []


async def test_delete_concept_not_found_raises(
    pg_db,
):
    with pytest.raises(
        ValueError, match="not found",
    ):
        await pg_db.delete_concept(999)


# --- User CRUD Tests ---


async def test_register_user(pg_db):
    user = await pg_db.register_user(
        "alice", "s3cret",
    )
    assert user.id is not None
    assert user.username == "alice"


async def test_register_user_duplicate_raises(
    pg_db,
):
    await pg_db.register_user("alice", "pass1")
    with pytest.raises(
        ValueError, match="already exists",
    ):
        await pg_db.register_user("alice", "pass2")


async def test_authenticate_user_valid(pg_db):
    await pg_db.register_user("alice", "s3cret")
    user = await pg_db.authenticate_user(
        "alice", "s3cret",
    )
    assert user is not None
    assert user.username == "alice"


async def test_authenticate_user_wrong_password(
    pg_db,
):
    await pg_db.register_user("alice", "s3cret")
    assert (
        await pg_db.authenticate_user(
            "alice", "wrong",
        )
    ) is None


# --- User Session Tests ---


async def test_create_session(pg_db):
    user = await pg_db.register_user(
        "alice", "pass",
    )
    session = await pg_db.create_session(user.id)
    assert session.id is not None
    assert session.user_id == user.id
    assert len(session.token) == 64


async def test_get_session_valid(pg_db):
    user = await pg_db.register_user(
        "alice", "pass",
    )
    session = await pg_db.create_session(user.id)
    loaded = await pg_db.get_session(session.token)
    assert loaded is not None
    assert loaded.token == session.token


async def test_get_session_expired(pg_db):
    user = await pg_db.register_user(
        "alice", "pass",
    )
    session = await pg_db.create_session(
        user.id, ttl_hours=0,
    )
    assert (
        await pg_db.get_session(session.token)
    ) is None


async def test_delete_session(pg_db):
    user = await pg_db.register_user(
        "alice", "pass",
    )
    session = await pg_db.create_session(user.id)
    await pg_db.delete_session(session.token)
    assert (
        await pg_db.get_session(session.token)
    ) is None


# --- Progress CRUD Tests ---


async def test_upsert_progress_insert(pg_db):
    from rembrandt.models import (
        CardState,
        UserProgress,
    )

    progress = UserProgress(
        user_id=1,
        concept_id=1,
        easiness_factor=2.5,
        interval=1,
        repetitions=1,
        state=CardState.REVIEW,
        next_review=datetime(2026, 3, 1, 12, 0, 0),
    )
    await pg_db.upsert_progress(progress)
    loaded = await pg_db.get_progress(1, 1)
    assert loaded is not None
    assert loaded.easiness_factor == 2.5
    assert loaded.state == CardState.REVIEW


async def test_upsert_progress_update(pg_db):
    from rembrandt.models import UserProgress

    progress = UserProgress(
        user_id=1,
        concept_id=1,
        next_review=datetime(2026, 3, 1, 12, 0, 0),
    )
    await pg_db.upsert_progress(progress)

    progress.easiness_factor = 2.1
    progress.interval = 6
    progress.repetitions = 3
    await pg_db.upsert_progress(progress)

    loaded = await pg_db.get_progress(1, 1)
    assert loaded.easiness_factor == 2.1
    assert loaded.interval == 6
    assert loaded.repetitions == 3


async def test_get_all_progress(pg_db):
    from rembrandt.models import UserProgress

    dt = datetime(2026, 3, 1, 12, 0, 0)
    await pg_db.upsert_progress(UserProgress(
        user_id=1, concept_id=1,
        next_review=dt,
    ))
    await pg_db.upsert_progress(UserProgress(
        user_id=1, concept_id=3,
        next_review=dt,
    ))
    result = await pg_db.get_all_progress(
        1, [1, 2, 3],
    )
    assert len(result) == 2
    assert 1 in result
    assert 3 in result
    assert 2 not in result


async def test_get_all_progress_empty(pg_db):
    result = await pg_db.get_all_progress(1, [])
    assert result == {}


# --- Progress Export/Import Tests ---


async def test_export_import_roundtrip(pg_db):
    from rembrandt.models import UserProgress

    dt = datetime(2026, 3, 1, 12, 0, 0)
    await pg_db.upsert_progress(UserProgress(
        user_id=1, concept_id=1,
        easiness_factor=2.3, interval=6,
        repetitions=4, next_review=dt,
    ))
    exported = await pg_db.export_progress(1)
    assert len(exported) == 1
    assert exported[0]["next_review"] == (
        "2026-03-01T12:00:00"
    )


async def test_import_progress_missing_key_raises(
    pg_db,
):
    records = [
        {
            "user_id": 1, "concept_id": 1,
            "easiness_factor": 2.5,
        },
    ]
    with pytest.raises(
        KeyError, match="Missing keys",
    ):
        await pg_db.import_progress(records)


# --- Answer History Tests ---


async def test_record_answer(pg_db):
    await pg_db.record_answer(
        1, 1, "flashcard", True, 5,
    )
    history = await pg_db.get_answer_history(1)
    assert len(history) == 1
    assert history[0].correct is True
    assert history[0].quality == 5


async def test_get_answer_history_ordered(pg_db):
    await pg_db.record_answer(
        1, 1, "flashcard", True, 5,
    )
    await pg_db.record_answer(
        1, 2, "multiple_choice", False, 1,
    )
    history = await pg_db.get_answer_history(1)
    assert len(history) == 2
    assert history[0].concept_id == 2
    assert history[1].concept_id == 1


async def test_get_answer_history_limit(pg_db):
    for i in range(5):
        await pg_db.record_answer(
            1, i, "flashcard", True, 5,
        )
    history = await pg_db.get_answer_history(
        1, limit=3,
    )
    assert len(history) == 3


# --- Topic CRUD Tests ---


async def test_add_topic(pg_db):
    from rembrandt.models import Concept, Topic

    concepts = await pg_db.add_concepts([
        Concept(front="cat", back="gato"),
        Concept(front="dog", back="perro"),
    ])
    topic = await pg_db.add_topic(Topic(
        title="Animals",
        description="Animal concepts",
        concept_count=2,
        concept_ids=[
            concepts[0].id, concepts[1].id,
        ],
    ))
    assert topic.id is not None
    assert topic.title == "Animals"


async def test_get_topic_by_id(pg_db):
    from rembrandt.models import Concept, Topic

    concepts = await pg_db.add_concepts([
        Concept(front="cat", back="gato"),
    ])
    topic = await pg_db.add_topic(Topic(
        title="Test Topic",
        tags=["test"],
        concept_count=1,
        concept_ids=[concepts[0].id],
    ))
    loaded = await pg_db.get_topic(topic.id)
    assert loaded is not None
    assert loaded.title == "Test Topic"
    assert loaded.tags == ["test"]
    assert loaded.concept_ids == [concepts[0].id]


async def test_get_topics_filter_tag(pg_db):
    from rembrandt.models import Topic

    await pg_db.add_topics([
        Topic(
            title="Food Topic",
            tags=["food"],
        ),
        Topic(
            title="Travel Topic",
            tags=["travel"],
        ),
        Topic(
            title="Multi Tag",
            tags=["food", "travel"],
        ),
    ])
    food = await pg_db.get_topics(tag="food")
    assert len(food) == 2
    titles = {t.title for t in food}
    assert titles == {"Food Topic", "Multi Tag"}


async def test_update_topic(pg_db):
    from rembrandt.models import Topic

    topic = await pg_db.add_topic(Topic(
        title="Old Title",
    ))
    await pg_db.update_topic(
        topic.model_copy(update={
            "title": "New Title",
        }),
    )
    loaded = await pg_db.get_topic(topic.id)
    assert loaded.title == "New Title"


async def test_delete_topic(pg_db):
    from rembrandt.models import Topic

    topic = await pg_db.add_topic(Topic(
        title="Doomed",
    ))
    await pg_db.delete_topic(topic.id)
    assert await pg_db.get_topic(topic.id) is None


async def test_delete_topic_not_found_raises(
    pg_db,
):
    with pytest.raises(
        ValueError, match="not found",
    ):
        await pg_db.delete_topic(999)


# --- Context Manager Tests ---


async def test_context_manager(pg_db):
    await pg_db.add_concept("cat", "gato")
    concepts = await pg_db.get_concepts()
    assert len(concepts) == 1
