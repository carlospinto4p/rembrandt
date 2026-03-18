"""Tests for rembrandt.db."""

from datetime import datetime

import pytest

from rembrandt.db import Database, import_concepts_csv
from rembrandt.models import (
    CardState,
    Concept,
    ConversationStage,
    ConversationState,
    Topic,
    UserProgress,
)

pytestmark = pytest.mark.asyncio


# --- User CRUD Tests ---


async def test_register_user(db):
    user = await db.register_user("alice", "s3cret")
    assert user.id is not None
    assert user.username == "alice"
    assert user.display_name is None


async def test_register_user_with_display_name(db):
    user = await db.register_user(
        "bob", "pass", display_name="Bob S.",
    )
    assert user.display_name == "Bob S."


async def test_register_user_duplicate_raises(db):
    await db.register_user("alice", "pass1")
    with pytest.raises(
        ValueError, match="already exists",
    ):
        await db.register_user("alice", "pass2")


async def test_get_user_found(db):
    await db.register_user("alice", "pass")
    user = await db.get_user("alice")
    assert user is not None
    assert user.username == "alice"


async def test_get_user_not_found(db):
    assert await db.get_user("ghost") is None


async def test_authenticate_user_valid(db):
    await db.register_user("alice", "s3cret")
    user = await db.authenticate_user(
        "alice", "s3cret",
    )
    assert user is not None
    assert user.username == "alice"


async def test_authenticate_user_wrong_password(db):
    await db.register_user("alice", "s3cret")
    assert (
        await db.authenticate_user("alice", "wrong")
    ) is None


async def test_authenticate_user_unknown_username(db):
    assert (
        await db.authenticate_user("ghost", "pass")
    ) is None


# --- User Session Tests ---


async def test_create_session(db):
    user = await db.register_user("alice", "pass")
    session = await db.create_session(user.id)
    assert session.id is not None
    assert session.user_id == user.id
    assert len(session.token) == 64
    assert session.expires_at > session.created_at


async def test_create_session_custom_ttl(db):
    user = await db.register_user("alice", "pass")
    session = await db.create_session(
        user.id, ttl_hours=48,
    )
    diff = session.expires_at - session.created_at
    assert abs(diff.total_seconds() - 48 * 3600) < 2


async def test_get_session_valid(db):
    user = await db.register_user("alice", "pass")
    session = await db.create_session(user.id)
    loaded = await db.get_session(session.token)
    assert loaded is not None
    assert loaded.token == session.token
    assert loaded.user_id == user.id


async def test_get_session_not_found(db):
    assert await db.get_session("nonexistent") is None


async def test_get_session_expired(db):
    user = await db.register_user("alice", "pass")
    session = await db.create_session(
        user.id, ttl_hours=0,
    )
    assert await db.get_session(session.token) is None


async def test_delete_session(db):
    user = await db.register_user("alice", "pass")
    session = await db.create_session(user.id)
    await db.delete_session(session.token)
    assert await db.get_session(session.token) is None


async def test_delete_user_sessions(db):
    user = await db.register_user("alice", "pass")
    s1 = await db.create_session(user.id)
    s2 = await db.create_session(user.id)
    await db.delete_user_sessions(user.id)
    assert await db.get_session(s1.token) is None
    assert await db.get_session(s2.token) is None


# --- Concept CRUD Tests ---


async def test_add_concept(db):
    concept = await db.add_concept(
        "What is ML?", "Machine learning",
    )
    assert concept.id is not None
    assert concept.front == "What is ML?"
    assert concept.back == "Machine learning"


async def test_add_concepts_bulk(db):
    concepts = await db.add_concepts([
        Concept(front="cat", back="gato"),
        Concept(front="dog", back="perro"),
        Concept(front="house", back="casa"),
    ])
    assert len(concepts) == 3
    assert all(c.id is not None for c in concepts)
    assert concepts[0].front == "cat"
    assert concepts[2].back == "casa"


async def test_get_concepts_empty(db):
    result = await db.get_concepts()
    assert result == []


async def test_get_concepts_returns_all(db):
    await db.add_concept("cat", "gato")
    await db.add_concept("dog", "perro")
    result = await db.get_concepts()
    assert len(result) == 2


async def test_add_concept_auto_increments_id(db):
    c1 = await db.add_concept("cat", "gato")
    c2 = await db.add_concept("dog", "perro")
    assert c2.id == c1.id + 1


async def test_add_concept_with_context(db):
    concept = await db.add_concept(
        "cat", "gato",
        context="A common household pet",
    )
    assert concept.context == "A common household pet"
    loaded = await db.get_concepts()
    assert (
        loaded[0].context == "A common household pet"
    )


async def test_add_concept_with_owner(db):
    u = await db.register_user("u1", "pass")
    concept = await db.add_concept(
        "cat", "gato", owner_id=u.id,
    )
    assert concept.owner_id == u.id


async def test_get_concepts_filter_by_owner(db):
    u = await db.register_user("u1", "pass")
    await db.add_concept("cat", "gato")
    await db.add_concept(
        "dog", "perro", owner_id=u.id,
    )
    # Without owner filter, all returned
    all_concepts = await db.get_concepts()
    assert len(all_concepts) == 2

    # With owner_id, shared + owned
    owned = await db.get_concepts(owner_id=u.id)
    assert len(owned) == 2


async def test_tags_default_empty(db):
    await db.add_concept("cat", "gato")
    loaded = await db.get_concepts()
    assert loaded[0].tags == []


async def test_tags_roundtrip(db):
    await db.add_concept(
        "bread", "pan", tags=["food"],
    )
    loaded = await db.get_concepts()
    assert loaded[0].tags == ["food"]


async def test_tags_bulk_roundtrip(db):
    await db.add_concepts([
        Concept(
            front="bread", back="pan",
            tags=["food"],
        ),
        Concept(
            front="mother", back="madre",
            tags=["family"],
        ),
        Concept(front="cat", back="gato"),
    ])
    loaded = await db.get_concepts()
    assert loaded[0].tags == ["food"]
    assert loaded[1].tags == ["family"]
    assert loaded[2].tags == []


async def test_get_concepts_filter_by_tag(db):
    await db.add_concepts([
        Concept(
            front="bread", back="pan",
            tags=["food"],
        ),
        Concept(
            front="cat", back="gato",
            tags=["animals"],
        ),
        Concept(
            front="milk", back="leche",
            tags=["food", "drinks"],
        ),
    ])
    food = await db.get_concepts(tag="food")
    assert len(food) == 2
    fronts = {c.front for c in food}
    assert fronts == {"bread", "milk"}


# --- Concept Update/Delete Tests ---


async def test_update_concept(db):
    concept = await db.add_concept(
        "cat", "gato",
    )
    updated = await db.update_concept(
        concept.model_copy(update={"back": "gatito"}),
    )
    assert updated.back == "gatito"
    loaded = await db.get_concepts()
    assert loaded[0].back == "gatito"


async def test_update_concept_none_id_raises(db):
    concept = Concept(front="cat", back="gato")
    with pytest.raises(
        ValueError, match="id must be set",
    ):
        await db.update_concept(concept)


async def test_update_concept_not_found_raises(db):
    concept = Concept(
        id=999, front="cat", back="gato",
    )
    with pytest.raises(
        ValueError, match="not found",
    ):
        await db.update_concept(concept)


async def test_delete_concept(db):
    concept = await db.add_concept("cat", "gato")
    await db.delete_concept(concept.id)
    assert await db.get_concepts() == []


async def test_delete_concept_not_found_raises(db):
    with pytest.raises(
        ValueError, match="not found",
    ):
        await db.delete_concept(999)


# --- Progress CRUD Tests ---


async def test_get_progress_nonexistent(db):
    u = await db.register_user("u1", "pass")
    result = await db.get_progress(u.id, 999)
    assert result is None


async def test_upsert_progress_insert(db):
    u = await db.register_user("u1", "pass")
    progress = UserProgress(
        user_id=u.id,
        concept_id=1,
        easiness_factor=2.5,
        interval=1,
        repetitions=1,
        state=CardState.REVIEW,
        next_review=datetime(2026, 3, 1, 12, 0, 0),
    )
    await db.upsert_progress(progress)

    loaded = await db.get_progress(u.id, 1)
    assert loaded is not None
    assert loaded.easiness_factor == 2.5
    assert loaded.interval == 1
    assert loaded.repetitions == 1
    assert loaded.state == CardState.REVIEW
    assert loaded.step_index == 0


async def test_upsert_progress_update(db):
    u = await db.register_user("u1", "pass")
    progress = UserProgress(
        user_id=u.id,
        concept_id=1,
        next_review=datetime(2026, 3, 1, 12, 0, 0),
    )
    await db.upsert_progress(progress)

    progress.easiness_factor = 2.1
    progress.interval = 6
    progress.repetitions = 3
    await db.upsert_progress(progress)

    loaded = await db.get_progress(u.id, 1)
    assert loaded is not None
    assert loaded.easiness_factor == 2.1
    assert loaded.interval == 6
    assert loaded.repetitions == 3


async def test_progress_roundtrip_datetime(db):
    u = await db.register_user("u1", "pass")
    dt = datetime(2026, 6, 15, 10, 30, 0)
    progress = UserProgress(
        user_id=u.id,
        concept_id=1,
        next_review=dt,
    )
    await db.upsert_progress(progress)

    loaded = await db.get_progress(u.id, 1)
    assert loaded is not None
    assert loaded.next_review == dt


async def test_get_all_progress(db):
    u = await db.register_user("u1", "pass")
    dt = datetime(2026, 3, 1, 12, 0, 0)
    await db.upsert_progress(UserProgress(
        user_id=u.id, concept_id=1,
        next_review=dt,
    ))
    await db.upsert_progress(UserProgress(
        user_id=u.id, concept_id=3,
        next_review=dt,
    ))

    result = await db.get_all_progress(
        u.id, [1, 2, 3],
    )
    assert len(result) == 2
    assert 1 in result
    assert 3 in result
    assert 2 not in result


async def test_get_all_progress_empty(db):
    u = await db.register_user("u1", "pass")
    result = await db.get_all_progress(u.id, [])
    assert result == {}


# --- Context Manager Tests ---


async def test_context_manager(tmp_path):
    async with await Database.connect(
        tmp_path / "ctx.db",
    ) as db:
        await db.add_concept("cat", "gato")
        concepts = await db.get_concepts()
        assert len(concepts) == 1


# --- Topic CRUD Tests ---


async def test_add_topic(db):
    concepts = await db.add_concepts([
        Concept(front="cat", back="gato"),
        Concept(front="dog", back="perro"),
    ])
    topic = await db.add_topic(Topic(
        title="Animals",
        description="Animal concepts",
        tags=["animals"],
        concept_count=2,
        concept_ids=[
            concepts[0].id, concepts[1].id,
        ],
    ))
    assert topic.id is not None
    assert topic.title == "Animals"
    assert topic.concept_count == 2


async def test_add_topic_concept_order_preserved(db):
    concepts = await db.add_concepts([
        Concept(front="cat", back="gato"),
        Concept(front="dog", back="perro"),
        Concept(front="house", back="casa"),
    ])
    ids = [
        concepts[2].id,
        concepts[0].id,
        concepts[1].id,
    ]
    topic = await db.add_topic(Topic(
        title="Reversed order",
        concept_count=3,
        concept_ids=ids,
    ))
    loaded = await db.get_topic(topic.id)
    assert loaded is not None
    assert loaded.concept_ids == ids


async def test_add_topics_bulk(db):
    concepts = await db.add_concepts([
        Concept(front="cat", back="gato"),
        Concept(front="dog", back="perro"),
    ])
    topics = await db.add_topics([
        Topic(
            title="Topic 1",
            concept_count=1,
            concept_ids=[concepts[0].id],
        ),
        Topic(
            title="Topic 2",
            concept_count=1,
            concept_ids=[concepts[1].id],
        ),
    ])
    assert len(topics) == 2
    assert all(t.id is not None for t in topics)
    assert topics[0].title == "Topic 1"
    assert topics[1].title == "Topic 2"


async def test_get_topics(db):
    await db.add_topics([
        Topic(title="Topic A"),
        Topic(title="Topic B"),
    ])
    topics = await db.get_topics()
    assert len(topics) == 2


async def test_get_topics_filter_tag(db):
    await db.add_topics([
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
    food = await db.get_topics(tag="food")
    assert len(food) == 2
    titles = {t.title for t in food}
    assert titles == {"Food Topic", "Multi Tag"}


async def test_get_topic_by_id(db):
    concepts = await db.add_concepts([
        Concept(front="cat", back="gato"),
    ])
    topic = await db.add_topic(Topic(
        title="Test Topic",
        tags=["test"],
        concept_count=1,
        concept_ids=[concepts[0].id],
    ))
    loaded = await db.get_topic(topic.id)
    assert loaded is not None
    assert loaded.title == "Test Topic"
    assert loaded.tags == ["test"]
    assert loaded.concept_ids == [concepts[0].id]


async def test_get_topic_not_found(db):
    assert await db.get_topic(999) is None


async def test_topic_with_no_concepts(db):
    topic = await db.add_topic(Topic(
        title="Empty Topic",
    ))
    loaded = await db.get_topic(topic.id)
    assert loaded is not None
    assert loaded.concept_ids == []
    assert loaded.concept_count == 0


async def test_get_topics_populates_concept_ids(db):
    concepts = await db.add_concepts([
        Concept(front="cat", back="gato"),
        Concept(front="dog", back="perro"),
    ])
    await db.add_topics([
        Topic(
            title="T1",
            concept_count=1,
            concept_ids=[concepts[0].id],
        ),
        Topic(
            title="T2",
            concept_count=2,
            concept_ids=[
                concepts[1].id, concepts[0].id,
            ],
        ),
    ])
    topics = await db.get_topics()
    assert topics[0].concept_ids == [concepts[0].id]
    assert topics[1].concept_ids == [
        concepts[1].id, concepts[0].id,
    ]


# --- Topic Update/Delete Tests ---


async def test_update_topic_metadata(db):
    topic = await db.add_topic(Topic(
        title="Old Title",
    ))
    updated = await db.update_topic(
        topic.model_copy(update={
            "title": "New Title",
            "description": "Updated",
            "tags": ["food"],
        }),
    )
    assert updated.title == "New Title"
    loaded = await db.get_topic(topic.id)
    assert loaded.title == "New Title"
    assert loaded.description == "Updated"
    assert loaded.tags == ["food"]


async def test_update_topic_replaces_concept_ids(db):
    concepts = await db.add_concepts([
        Concept(front="cat", back="gato"),
        Concept(front="dog", back="perro"),
        Concept(front="house", back="casa"),
    ])
    topic = await db.add_topic(Topic(
        title="Test",
        concept_count=2,
        concept_ids=[
            concepts[0].id, concepts[1].id,
        ],
    ))
    await db.update_topic(
        topic.model_copy(update={
            "concept_count": 2,
            "concept_ids": [
                concepts[1].id, concepts[2].id,
            ],
        }),
    )
    loaded = await db.get_topic(topic.id)
    assert loaded.concept_ids == [
        concepts[1].id, concepts[2].id,
    ]


async def test_update_topic_none_id_raises(db):
    topic = Topic(title="Test")
    with pytest.raises(
        ValueError, match="id must be set",
    ):
        await db.update_topic(topic)


async def test_update_topic_not_found_raises(db):
    topic = Topic(id=999, title="Test")
    with pytest.raises(
        ValueError, match="not found",
    ):
        await db.update_topic(topic)


async def test_delete_topic(db):
    topic = await db.add_topic(Topic(
        title="Doomed",
    ))
    await db.delete_topic(topic.id)
    assert await db.get_topic(topic.id) is None


async def test_delete_topic_removes_concept_links(db):
    concepts = await db.add_concepts([
        Concept(front="cat", back="gato"),
    ])
    topic = await db.add_topic(Topic(
        title="Linked",
        concept_count=1,
        concept_ids=[concepts[0].id],
    ))
    await db.delete_topic(topic.id)
    assert await db.get_topic(topic.id) is None
    # Concept itself still exists
    assert len(await db.get_concepts()) == 1


async def test_delete_topic_not_found_raises(db):
    with pytest.raises(
        ValueError, match="not found",
    ):
        await db.delete_topic(999)


# --- Progress Export/Import Tests ---


async def test_export_progress_empty(db):
    u = await db.register_user("u1", "pass")
    result = await db.export_progress(u.id)
    assert result == []


async def test_export_progress_returns_all(db):
    u = await db.register_user("u1", "pass")
    dt = datetime(2026, 3, 1, 12, 0, 0)
    await db.upsert_progress(UserProgress(
        user_id=u.id, concept_id=1,
        next_review=dt,
    ))
    await db.upsert_progress(UserProgress(
        user_id=u.id, concept_id=2,
        easiness_factor=2.1, interval=6,
        repetitions=3, next_review=dt,
    ))
    result = await db.export_progress(u.id)
    assert len(result) == 2
    assert all(isinstance(r, dict) for r in result)


async def test_export_progress_filters_by_user(db):
    u1 = await db.register_user("u1", "pass")
    u2 = await db.register_user("u2", "pass")
    dt = datetime(2026, 3, 1, 12, 0, 0)
    await db.upsert_progress(UserProgress(
        user_id=u1.id, concept_id=1,
        next_review=dt,
    ))
    await db.upsert_progress(UserProgress(
        user_id=u2.id, concept_id=2,
        next_review=dt,
    ))
    result = await db.export_progress(u1.id)
    assert len(result) == 1
    assert result[0]["user_id"] == u1.id


async def test_export_progress_next_review_is_string(
    db,
):
    u = await db.register_user("u1", "pass")
    dt = datetime(2026, 6, 15, 10, 30, 0)
    await db.upsert_progress(UserProgress(
        user_id=u.id, concept_id=1,
        next_review=dt,
    ))
    result = await db.export_progress(u.id)
    assert (
        result[0]["next_review"]
        == "2026-06-15T10:30:00"
    )


async def test_import_progress_inserts(db):
    u = await db.register_user("u1", "pass")
    records = [
        {
            "user_id": u.id, "concept_id": 1,
            "easiness_factor": 2.5, "interval": 1,
            "repetitions": 1,
            "next_review": "2026-03-01T12:00:00",
        },
    ]
    count = await db.import_progress(records)
    assert count == 1
    loaded = await db.get_progress(u.id, 1)
    assert loaded is not None
    assert loaded.repetitions == 1


async def test_import_progress_upserts(db):
    u = await db.register_user("u1", "pass")
    dt = datetime(2026, 3, 1, 12, 0, 0)
    await db.upsert_progress(UserProgress(
        user_id=u.id, concept_id=1,
        repetitions=1, next_review=dt,
    ))
    records = [
        {
            "user_id": u.id, "concept_id": 1,
            "easiness_factor": 2.1, "interval": 6,
            "repetitions": 3,
            "next_review": "2026-04-01T12:00:00",
        },
    ]
    await db.import_progress(records)
    loaded = await db.get_progress(u.id, 1)
    assert loaded is not None
    assert loaded.repetitions == 3
    assert loaded.easiness_factor == 2.1


async def test_import_export_roundtrip(db):
    u = await db.register_user("u1", "pass")
    dt = datetime(2026, 3, 1, 12, 0, 0)
    await db.upsert_progress(UserProgress(
        user_id=u.id, concept_id=1,
        easiness_factor=2.3, interval=6,
        repetitions=4, next_review=dt,
    ))
    await db.upsert_progress(UserProgress(
        user_id=u.id, concept_id=2,
        easiness_factor=1.8, interval=1,
        repetitions=0, next_review=dt,
    ))
    exported = await db.export_progress(u.id)

    db2 = await Database.connect(":memory:")
    await db2.register_user("u1", "pass")
    count = await db2.import_progress(exported)
    assert count == 2

    re_exported = await db2.export_progress(u.id)
    assert re_exported == exported
    await db2.close()


async def test_export_progress_includes_state(db):
    u = await db.register_user("u1", "pass")
    await db.upsert_progress(UserProgress(
        user_id=u.id, concept_id=1,
        state=CardState.LEARNING, step_index=1,
        next_review=datetime(2026, 3, 1, 12, 0, 0),
    ))
    result = await db.export_progress(u.id)
    assert result[0]["state"] == "learning"
    assert result[0]["step_index"] == 1


async def test_import_progress_with_state(db):
    u = await db.register_user("u1", "pass")
    records = [
        {
            "user_id": u.id, "concept_id": 1,
            "easiness_factor": 2.5, "interval": 1,
            "repetitions": 1,
            "next_review": "2026-03-01T12:00:00",
            "state": "relearning", "step_index": 2,
        },
    ]
    await db.import_progress(records)
    loaded = await db.get_progress(u.id, 1)
    assert loaded.state == CardState.RELEARNING
    assert loaded.step_index == 2


async def test_import_progress_without_state_defaults(
    db,
):
    u = await db.register_user("u1", "pass")
    records = [
        {
            "user_id": u.id, "concept_id": 1,
            "easiness_factor": 2.5, "interval": 1,
            "repetitions": 1,
            "next_review": "2026-03-01T12:00:00",
        },
    ]
    await db.import_progress(records)
    loaded = await db.get_progress(u.id, 1)
    assert loaded.state == CardState.REVIEW
    assert loaded.step_index == 0


async def test_import_progress_missing_key_raises(db):
    records = [
        {
            "user_id": 1, "concept_id": 1,
            "easiness_factor": 2.5,
        },
    ]
    with pytest.raises(KeyError, match="Missing keys"):
        await db.import_progress(records)


# --- Answer History Tests ---


async def test_record_answer(db):
    u = await db.register_user("u1", "pass")
    await db.record_answer(
        u.id, 1, "flashcard", True, 5,
    )
    history = await db.get_answer_history(u.id)
    assert len(history) == 1
    assert history[0].concept_id == 1
    assert history[0].correct is True
    assert history[0].quality == 5


async def test_record_answer_incorrect(db):
    u = await db.register_user("u1", "pass")
    await db.record_answer(
        u.id, 1, "flashcard", False, 1,
    )
    history = await db.get_answer_history(u.id)
    assert len(history) == 1
    assert history[0].correct is False
    assert history[0].quality == 1


async def test_get_answer_history_empty(db):
    u = await db.register_user("u1", "pass")
    history = await db.get_answer_history(u.id)
    assert history == []


async def test_get_answer_history_ordered_newest_first(
    db,
):
    u = await db.register_user("u1", "pass")
    await db.record_answer(
        u.id, 1, "flashcard", True, 5,
    )
    await db.record_answer(
        u.id, 2, "multiple_choice", False, 1,
    )
    history = await db.get_answer_history(u.id)
    assert len(history) == 2
    assert history[0].concept_id == 2
    assert history[1].concept_id == 1


async def test_get_answer_history_limit(db):
    u = await db.register_user("u1", "pass")
    for i in range(5):
        await db.record_answer(
            u.id, i, "flashcard", True, 5,
        )
    history = await db.get_answer_history(
        u.id, limit=3,
    )
    assert len(history) == 3


async def test_get_answer_history_since(db):
    u = await db.register_user("u1", "pass")
    await db._conn.execute(
        "INSERT INTO answer_history "
        "(user_id, concept_id, exercise_type, "
        " correct, quality, answered_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (u.id, 1, "flashcard", 1, 5,
         "2026-01-01T00:00:00"),
    )
    await db._conn.execute(
        "INSERT INTO answer_history "
        "(user_id, concept_id, exercise_type, "
        " correct, quality, answered_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (u.id, 2, "flashcard", 1, 5,
         "2026-06-01T00:00:00"),
    )
    await db._conn.commit()
    history = await db.get_answer_history(
        u.id, since=datetime(2026, 3, 1),
    )
    assert len(history) == 1
    assert history[0].concept_id == 2


async def test_get_answer_history_filters_by_user(db):
    u1 = await db.register_user("u1", "pass")
    u2 = await db.register_user("u2", "pass")
    await db.record_answer(
        u1.id, 1, "flashcard", True, 5,
    )
    await db.record_answer(
        u2.id, 2, "flashcard", True, 5,
    )
    history = await db.get_answer_history(u1.id)
    assert len(history) == 1
    assert history[0].user_id == u1.id


async def test_daily_stats_empty(db):
    u = await db.register_user("u1", "pass")
    stats = await db.daily_stats(u.id)
    assert stats == []


async def test_daily_stats_aggregation(db):
    u = await db.register_user("u1", "pass")
    await db._conn.execute(
        "INSERT INTO answer_history "
        "(user_id, concept_id, exercise_type, "
        " correct, quality, answered_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (u.id, 1, "flashcard", 1, 5,
         "2026-02-27T10:00:00"),
    )
    await db._conn.execute(
        "INSERT INTO answer_history "
        "(user_id, concept_id, exercise_type, "
        " correct, quality, answered_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (u.id, 2, "flashcard", 0, 1,
         "2026-02-27T11:00:00"),
    )
    await db._conn.commit()
    stats = await db.daily_stats(u.id, days=365)
    assert len(stats) == 1
    assert stats[0].date == "2026-02-27"
    assert stats[0].answers == 2
    assert stats[0].correct == 1
    assert stats[0].accuracy_pct == 50.0


async def test_daily_stats_multiple_days(db):
    u = await db.register_user("u1", "pass")
    for day, cid in [
        ("2026-02-26", 1),
        ("2026-02-27", 2),
    ]:
        await db._conn.execute(
            "INSERT INTO answer_history "
            "(user_id, concept_id, exercise_type, "
            " correct, quality, answered_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (u.id, cid, "flashcard", 1, 5,
             f"{day}T10:00:00"),
        )
    await db._conn.commit()
    stats = await db.daily_stats(u.id, days=365)
    assert len(stats) == 2
    assert stats[0].date == "2026-02-27"
    assert stats[1].date == "2026-02-26"


# --- Weak Concept Detection Tests ---


async def _add_history(db, user_id, cid, correct, n):
    """Helper to insert N answer_history rows."""
    for _ in range(n):
        await db._conn.execute(
            "INSERT INTO answer_history "
            "(user_id, concept_id, exercise_type, "
            " correct, quality, answered_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, cid, "flashcard",
             int(correct), 5 if correct else 1,
             "2026-02-27T10:00:00"),
        )
    await db._conn.commit()


async def test_weak_concepts_empty(db):
    u = await db.register_user("u1", "pass")
    result = await db.weak_concepts(u.id)
    assert result == []


async def test_weak_concepts_detects_weak(db):
    u = await db.register_user("u1", "pass")
    c = await db.add_concept("cat", "gato")
    await _add_history(db, u.id, c.id, True, 1)
    await _add_history(db, u.id, c.id, False, 3)
    result = await db.weak_concepts(u.id)
    assert len(result) == 1
    assert result[0].concept.id == c.id
    assert result[0].attempts == 4
    assert result[0].errors == 3
    assert result[0].error_rate == 0.75


async def test_weak_concepts_excludes_strong(db):
    u = await db.register_user("u1", "pass")
    c = await db.add_concept("cat", "gato")
    await _add_history(db, u.id, c.id, True, 4)
    result = await db.weak_concepts(u.id)
    assert result == []


async def test_weak_concepts_min_attempts(db):
    u = await db.register_user("u1", "pass")
    c = await db.add_concept("cat", "gato")
    await _add_history(db, u.id, c.id, False, 2)
    result = await db.weak_concepts(u.id)
    assert result == []

    result = await db.weak_concepts(
        u.id, min_attempts=2,
    )
    assert len(result) == 1


async def test_weak_concepts_threshold(db):
    u = await db.register_user("u1", "pass")
    c = await db.add_concept("cat", "gato")
    await _add_history(db, u.id, c.id, True, 2)
    await _add_history(db, u.id, c.id, False, 1)

    result = await db.weak_concepts(u.id)
    assert result == []

    result = await db.weak_concepts(
        u.id, threshold=0.3,
    )
    assert len(result) == 1


async def test_weak_concepts_ordered_by_error_rate(db):
    u = await db.register_user("u1", "pass")
    c1 = await db.add_concept("cat", "gato")
    c2 = await db.add_concept("dog", "perro")
    await _add_history(db, u.id, c1.id, True, 2)
    await _add_history(db, u.id, c1.id, False, 2)
    await _add_history(db, u.id, c2.id, True, 1)
    await _add_history(db, u.id, c2.id, False, 3)

    result = await db.weak_concepts(u.id)
    assert len(result) == 2
    assert result[0].concept.id == c2.id
    assert result[1].concept.id == c1.id


async def test_weak_concepts_filters_by_tag(db):
    u = await db.register_user("u1", "pass")
    c1 = await db.add_concept(
        "cat", "gato", tags=["animals"],
    )
    c2 = await db.add_concept(
        "bread", "pan", tags=["food"],
    )
    await _add_history(db, u.id, c1.id, False, 4)
    await _add_history(db, u.id, c2.id, False, 4)

    result = await db.weak_concepts(
        u.id, tag="animals",
    )
    assert len(result) == 1
    assert result[0].concept.id == c1.id


async def test_weak_concepts_filters_by_user(db):
    u1 = await db.register_user("u1", "pass")
    u2 = await db.register_user("u2", "pass")
    c = await db.add_concept("cat", "gato")
    await _add_history(db, u1.id, c.id, False, 4)
    await _add_history(db, u2.id, c.id, False, 4)

    result = await db.weak_concepts(u1.id)
    assert len(result) == 1

    result = await db.weak_concepts(u2.id)
    assert len(result) == 1


async def test_weak_concepts_limit(db):
    u = await db.register_user("u1", "pass")
    for i in range(5):
        c = await db.add_concept(
            f"concept{i}", f"back{i}",
        )
        await _add_history(db, u.id, c.id, False, 4)

    result = await db.weak_concepts(
        u.id, limit=3,
    )
    assert len(result) == 3


# --- Retention Rate Tests ---


async def test_retention_rate_empty(db):
    u = await db.register_user("u1", "pass")
    assert await db.retention_rate(u.id) == 0.0


async def test_retention_rate_all_correct(db):
    u = await db.register_user("u1", "pass")
    c = await db.add_concept("cat", "gato")
    await _add_history(db, u.id, c.id, True, 10)
    assert await db.retention_rate(u.id) == 100.0


async def test_retention_rate_mixed(db):
    u = await db.register_user("u1", "pass")
    c = await db.add_concept("cat", "gato")
    await _add_history(db, u.id, c.id, True, 7)
    await _add_history(db, u.id, c.id, False, 3)
    assert await db.retention_rate(u.id) == 70.0


# --- Forecast Tests ---


async def test_forecast_empty(db):
    u = await db.register_user("u1", "pass")
    result = await db.forecast(u.id, days=3)
    assert len(result) == 3
    assert all(f.due_count == 0 for f in result)


async def test_forecast_with_due_cards(db):
    u = await db.register_user("u1", "pass")
    c = await db.add_concept("cat", "gato")
    progress = UserProgress(
        user_id=u.id,
        concept_id=c.id,
        state=CardState.REVIEW,
        next_review=datetime.now(),
    )
    await db.upsert_progress(progress)
    result = await db.forecast(u.id, days=3)
    assert result[0].due_count == 1
    assert (
        result[0].date
        == datetime.now().date().isoformat()
    )


async def test_forecast_excludes_suspended(db):
    u = await db.register_user("u1", "pass")
    c = await db.add_concept("cat", "gato")
    progress = UserProgress(
        user_id=u.id,
        concept_id=c.id,
        state=CardState.SUSPENDED,
        next_review=datetime.now(),
    )
    await db.upsert_progress(progress)
    result = await db.forecast(u.id, days=3)
    assert result[0].due_count == 0


# --- CSV/TSV Import Tests ---


async def test_import_concepts_csv_basic(
    db, tmp_path,
):
    csv_file = tmp_path / "concepts.csv"
    csv_file.write_text(
        "front,back\ncat,gato\ndog,perro\n",
        encoding="utf-8",
    )
    concepts = await import_concepts_csv(
        db, csv_file,
    )
    assert len(concepts) == 2
    assert concepts[0].front == "cat"
    assert concepts[0].back == "gato"
    assert concepts[0].id is not None


async def test_import_concepts_csv_optional_columns(
    db, tmp_path,
):
    csv_file = tmp_path / "concepts.csv"
    csv_file.write_text(
        "front,back,context,tags\n"
        "cat,gato,A pet,\"animals,pets\"\n",
        encoding="utf-8",
    )
    concepts = await import_concepts_csv(
        db, csv_file,
    )
    assert len(concepts) == 1
    assert concepts[0].context == "A pet"
    assert concepts[0].tags == ["animals", "pets"]


async def test_import_concepts_tsv(db, tmp_path):
    tsv_file = tmp_path / "concepts.tsv"
    tsv_file.write_text(
        "front\tback\ncat\tgato\n",
        encoding="utf-8",
    )
    concepts = await import_concepts_csv(
        db, tsv_file,
    )
    assert len(concepts) == 1
    assert concepts[0].front == "cat"


async def test_import_concepts_csv_custom_columns(
    db, tmp_path,
):
    csv_file = tmp_path / "concepts.csv"
    csv_file.write_text(
        "question,answer\nWhat is ML?,Machine Learning\n",
        encoding="utf-8",
    )
    concepts = await import_concepts_csv(
        db, csv_file,
        front_col="question",
        back_col="answer",
    )
    assert concepts[0].front == "What is ML?"
    assert concepts[0].back == "Machine Learning"


async def test_import_concepts_csv_missing_column(
    db, tmp_path,
):
    csv_file = tmp_path / "concepts.csv"
    csv_file.write_text(
        "word,meaning\ncat,gato\n",
        encoding="utf-8",
    )
    with pytest.raises(
        ValueError, match="Required column",
    ):
        await import_concepts_csv(db, csv_file)


async def test_import_concepts_csv_with_owner(
    db, tmp_path,
):
    u = await db.register_user("u1", "pass")
    csv_file = tmp_path / "concepts.csv"
    csv_file.write_text(
        "front,back\ncat,gato\n",
        encoding="utf-8",
    )
    concepts = await import_concepts_csv(
        db, csv_file, owner_id=u.id,
    )
    assert concepts[0].owner_id == u.id


# --- Conversation State Tests ---


async def test_save_and_get_conversation_state(db):
    u = await db.register_user("u1", "pass")
    state = ConversationState(
        user_id=u.id,
        stage=ConversationStage.AWAITING_ANSWER,
        data={"exercise_id": 42},
    )
    await db.save_conversation_state(state)

    loaded = await db.get_conversation_state(u.id)
    assert loaded is not None
    assert loaded.user_id == u.id
    assert (
        loaded.stage
        == ConversationStage.AWAITING_ANSWER
    )
    assert loaded.data == {"exercise_id": 42}


async def test_get_conversation_state_nonexistent(db):
    result = await db.get_conversation_state(999)
    assert result is None


async def test_save_conversation_state_overwrites(db):
    u = await db.register_user("u1", "pass")
    state1 = ConversationState(
        user_id=u.id,
        stage=ConversationStage.CHOOSING_TOPIC,
    )
    await db.save_conversation_state(state1)

    state2 = ConversationState(
        user_id=u.id,
        stage=ConversationStage.EXERCISING,
        data={"session_key": "abc"},
    )
    await db.save_conversation_state(state2)

    loaded = await db.get_conversation_state(u.id)
    assert loaded is not None
    assert (
        loaded.stage == ConversationStage.EXERCISING
    )
    assert loaded.data == {"session_key": "abc"}


async def test_conversation_state_with_key(db):
    u = await db.register_user("u1", "pass")
    s1 = ConversationState(
        user_id=u.id,
        key="chat_1",
        stage=ConversationStage.IDLE,
    )
    s2 = ConversationState(
        user_id=u.id,
        key="chat_2",
        stage=ConversationStage.EXERCISING,
    )
    await db.save_conversation_state(s1)
    await db.save_conversation_state(s2)

    r1 = await db.get_conversation_state(
        u.id, key="chat_1",
    )
    r2 = await db.get_conversation_state(
        u.id, key="chat_2",
    )
    assert r1 is not None
    assert r1.stage == ConversationStage.IDLE
    assert r2 is not None
    assert (
        r2.stage == ConversationStage.EXERCISING
    )


async def test_delete_conversation_state(db):
    u = await db.register_user("u1", "pass")
    state = ConversationState(
        user_id=u.id,
        stage=ConversationStage.VIEWING_STATS,
    )
    await db.save_conversation_state(state)

    deleted = await db.delete_conversation_state(
        u.id,
    )
    assert deleted is True

    deleted2 = await db.delete_conversation_state(
        u.id,
    )
    assert deleted2 is False

    loaded = await db.get_conversation_state(u.id)
    assert loaded is None


async def test_conversation_state_preserves_data(db):
    u = await db.register_user("u1", "pass")
    state = ConversationState(
        user_id=u.id,
        stage=ConversationStage.CHOOSING_TOPIC,
        data={
            "page": 2,
            "tags": ["food", "travel"],
        },
    )
    await db.save_conversation_state(state)

    loaded = await db.get_conversation_state(u.id)
    assert loaded is not None
    assert loaded.data["page"] == 2
    assert loaded.data["tags"] == [
        "food", "travel",
    ]
