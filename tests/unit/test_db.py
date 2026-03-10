"""Tests for rembrandt.db."""

import sqlite3
from datetime import datetime

import pytest

from rembrandt.db import Database, import_words_csv
from rembrandt.models import (
    CardState,
    ConversationStage,
    ConversationState,
    Lesson,
    UserProgress,
    Word,
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
    with pytest.raises(ValueError, match="already exists"):
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
    user = await db.authenticate_user("alice", "s3cret")
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
    assert len(session.token) == 64  # 32 bytes hex
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


# --- Word CRUD Tests ---


async def test_add_word(db):
    word = await db.add_word(
        "en", "es", "hello", "hola",
    )
    assert word.id is not None
    assert word.word_from == "hello"
    assert word.word_to == "hola"


async def test_add_words_bulk(db):
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
    ])
    assert len(words) == 3
    assert all(w.id is not None for w in words)
    assert words[0].word_from == "cat"
    assert words[2].word_to == "casa"


async def test_get_words_empty(db):
    result = await db.get_words("en", "es")
    assert result == []


async def test_get_words_filters_by_language(db):
    await db.add_word("en", "es", "hello", "hola")
    await db.add_word("en", "fr", "hello", "bonjour")

    es_words = await db.get_words("en", "es")
    assert len(es_words) == 1
    assert es_words[0].word_to == "hola"

    fr_words = await db.get_words("en", "fr")
    assert len(fr_words) == 1
    assert fr_words[0].word_to == "bonjour"


async def test_add_word_auto_increments_id(db):
    w1 = await db.add_word("en", "es", "cat", "gato")
    w2 = await db.add_word("en", "es", "dog", "perro")
    assert w2.id == w1.id + 1


async def test_add_word_with_gender(db):
    word = await db.add_word(
        "es", "en", "casa", "house", gender="f",
    )
    assert word.gender == "f"
    loaded = await db.get_words("es", "en")
    assert loaded[0].gender == "f"
    assert loaded[0].conjugation_group is None


async def test_add_word_with_conjugation_group(db):
    word = await db.add_word(
        "es", "en", "hablar", "to speak",
        conjugation_group="ar",
    )
    assert word.conjugation_group == "ar"
    loaded = await db.get_words("es", "en")
    assert loaded[0].conjugation_group == "ar"
    assert loaded[0].gender is None


async def test_add_words_bulk_with_metadata(db):
    words = await db.add_words([
        Word(
            language_from="es", language_to="en",
            word_from="casa", word_to="house",
            gender="f",
        ),
        Word(
            language_from="es", language_to="en",
            word_from="hablar", word_to="to speak",
            conjugation_group="ar",
        ),
    ])
    assert words[0].gender == "f"
    assert words[1].conjugation_group == "ar"
    loaded = await db.get_words("es", "en")
    assert loaded[0].gender == "f"
    assert loaded[1].conjugation_group == "ar"


async def test_add_word_with_cefr(db):
    word = await db.add_word(
        "es", "en", "ser", "to be", cefr="A1",
    )
    assert word.cefr == "A1"
    loaded = await db.get_words("es", "en")
    assert loaded[0].cefr == "A1"


async def test_cefr_default_none(db):
    await db.add_word("en", "es", "cat", "gato")
    loaded = await db.get_words("en", "es")
    assert loaded[0].cefr is None


async def test_cefr_bulk_roundtrip(db):
    await db.add_words([
        Word(
            language_from="es", language_to="en",
            word_from="ser", word_to="to be",
            cefr="A1",
        ),
        Word(
            language_from="es", language_to="en",
            word_from="prescindir",
            word_to="to do without",
            cefr="C1",
        ),
        Word(
            language_from="es", language_to="en",
            word_from="casa", word_to="house",
        ),
    ])
    loaded = await db.get_words("es", "en")
    assert loaded[0].cefr == "A1"
    assert loaded[1].cefr == "C1"
    assert loaded[2].cefr is None


async def test_tags_default_empty(db):
    await db.add_word("en", "es", "cat", "gato")
    loaded = await db.get_words("en", "es")
    assert loaded[0].tags == []


async def test_tags_roundtrip(db):
    await db.add_word(
        "en", "es", "bread", "pan",
        tags=["food"],
    )
    loaded = await db.get_words("en", "es")
    assert loaded[0].tags == ["food"]


async def test_tags_bulk_roundtrip(db):
    await db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="bread", word_to="pan",
            tags=["food"],
        ),
        Word(
            language_from="en", language_to="es",
            word_from="mother", word_to="madre",
            tags=["family"],
        ),
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
    ])
    loaded = await db.get_words("en", "es")
    assert loaded[0].tags == ["food"]
    assert loaded[1].tags == ["family"]
    assert loaded[2].tags == []


# --- Word Update/Delete Tests ---


async def test_update_word(db):
    word = await db.add_word("en", "es", "cat", "gato")
    updated = await db.update_word(
        word.model_copy(update={"word_to": "gatito"}),
    )
    assert updated.word_to == "gatito"
    loaded = await db.get_words("en", "es")
    assert loaded[0].word_to == "gatito"


async def test_update_word_all_fields(db):
    word = await db.add_word(
        "en", "es", "cat", "gato",
    )
    modified = word.model_copy(update={
        "word_from": "kitten",
        "word_to": "gatito",
        "gender": "m",
        "tags": ["animals"],
        "cefr": "A1",
    })
    updated = await db.update_word(modified)
    assert updated.word_from == "kitten"
    assert updated.gender == "m"
    assert updated.tags == ["animals"]
    assert updated.cefr == "A1"


async def test_update_word_none_id_raises(db):
    word = Word(
        language_from="en", language_to="es",
        word_from="cat", word_to="gato",
    )
    with pytest.raises(ValueError, match="id must be set"):
        await db.update_word(word)


async def test_update_word_not_found_raises(db):
    word = Word(
        id=999,
        language_from="en", language_to="es",
        word_from="cat", word_to="gato",
    )
    with pytest.raises(ValueError, match="not found"):
        await db.update_word(word)


async def test_delete_word(db):
    word = await db.add_word(
        "en", "es", "cat", "gato",
    )
    await db.delete_word(word.id)
    assert await db.get_words("en", "es") == []


async def test_delete_word_not_found_raises(db):
    with pytest.raises(ValueError, match="not found"):
        await db.delete_word(999)


# --- Progress CRUD Tests ---


async def test_get_progress_nonexistent(db):
    u = await db.register_user("u1", "pass")
    result = await db.get_progress(u.id, 999)
    assert result is None


async def test_upsert_progress_insert(db):
    u = await db.register_user("u1", "pass")
    progress = UserProgress(
        user_id=u.id,
        word_id=1,
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
        word_id=1,
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
        word_id=1,
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
        user_id=u.id, word_id=1, next_review=dt,
    ))
    await db.upsert_progress(UserProgress(
        user_id=u.id, word_id=3, next_review=dt,
    ))

    result = await db.get_all_progress(u.id, [1, 2, 3])
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
        tmp_path / "ctx.db"
    ) as db:
        await db.add_word("en", "es", "cat", "gato")
        words = await db.get_words("en", "es")
        assert len(words) == 1


# --- Lesson CRUD Tests ---


async def test_add_lesson(db):
    words = await db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="dog", word_to="perro",
        ),
    ])
    lesson = await db.add_lesson(Lesson(
        title="A1 - Lesson 1",
        description="First lesson",
        language_from="en",
        language_to="es",
        cefr="A1",
        word_count=2,
        word_ids=[words[0].id, words[1].id],
    ))
    assert lesson.id is not None
    assert lesson.title == "A1 - Lesson 1"
    assert lesson.word_count == 2


async def test_add_lesson_word_order_preserved(db):
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
    ])
    ids = [words[2].id, words[0].id, words[1].id]
    lesson = await db.add_lesson(Lesson(
        title="Reversed order",
        language_from="en",
        language_to="es",
        word_count=3,
        word_ids=ids,
    ))
    loaded = await db.get_lesson(lesson.id)
    assert loaded is not None
    assert loaded.word_ids == ids


async def test_add_lessons_bulk(db):
    words = await db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="dog", word_to="perro",
        ),
    ])
    lessons = await db.add_lessons([
        Lesson(
            title="Lesson 1",
            language_from="en",
            language_to="es",
            cefr="A1",
            word_count=1,
            word_ids=[words[0].id],
        ),
        Lesson(
            title="Lesson 2",
            language_from="en",
            language_to="es",
            cefr="A1",
            word_count=1,
            word_ids=[words[1].id],
        ),
    ])
    assert len(lessons) == 2
    assert all(ls.id is not None for ls in lessons)
    assert lessons[0].title == "Lesson 1"
    assert lessons[1].title == "Lesson 2"


async def test_get_lessons_by_language(db):
    await db.add_lessons([
        Lesson(
            title="EN-ES Lesson",
            language_from="en",
            language_to="es",
        ),
        Lesson(
            title="EN-FR Lesson",
            language_from="en",
            language_to="fr",
        ),
    ])
    es = await db.get_lessons("en", "es")
    assert len(es) == 1
    assert es[0].title == "EN-ES Lesson"

    fr = await db.get_lessons("en", "fr")
    assert len(fr) == 1
    assert fr[0].title == "EN-FR Lesson"


async def test_get_lessons_filter_cefr(db):
    await db.add_lessons([
        Lesson(
            title="A1 Lesson",
            language_from="en",
            language_to="es",
            cefr="A1",
        ),
        Lesson(
            title="B1 Lesson",
            language_from="en",
            language_to="es",
            cefr="B1",
        ),
    ])
    result = await db.get_lessons(
        "en", "es", cefr="A1",
    )
    assert len(result) == 1
    assert result[0].title == "A1 Lesson"


async def test_get_lessons_filter_tag(db):
    await db.add_lessons([
        Lesson(
            title="Food Lesson",
            language_from="en",
            language_to="es",
            tags=["food"],
        ),
        Lesson(
            title="Travel Lesson",
            language_from="en",
            language_to="es",
            tags=["travel"],
        ),
        Lesson(
            title="Multi Tag",
            language_from="en",
            language_to="es",
            tags=["food", "travel"],
        ),
    ])
    food = await db.get_lessons("en", "es", tag="food")
    assert len(food) == 2
    titles = {ls.title for ls in food}
    assert titles == {"Food Lesson", "Multi Tag"}


async def test_get_lesson_by_id(db):
    words = await db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
    ])
    lesson = await db.add_lesson(Lesson(
        title="Test Lesson",
        language_from="en",
        language_to="es",
        cefr="A1",
        tags=["test"],
        word_count=1,
        word_ids=[words[0].id],
    ))
    loaded = await db.get_lesson(lesson.id)
    assert loaded is not None
    assert loaded.title == "Test Lesson"
    assert loaded.cefr == "A1"
    assert loaded.tags == ["test"]
    assert loaded.word_ids == [words[0].id]


async def test_get_lesson_not_found(db):
    assert await db.get_lesson(999) is None


async def test_lesson_with_no_words(db):
    lesson = await db.add_lesson(Lesson(
        title="Empty Lesson",
        language_from="en",
        language_to="es",
    ))
    loaded = await db.get_lesson(lesson.id)
    assert loaded is not None
    assert loaded.word_ids == []
    assert loaded.word_count == 0


async def test_get_lessons_populates_word_ids(db):
    words = await db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="dog", word_to="perro",
        ),
    ])
    await db.add_lessons([
        Lesson(
            title="L1",
            language_from="en",
            language_to="es",
            word_count=1,
            word_ids=[words[0].id],
        ),
        Lesson(
            title="L2",
            language_from="en",
            language_to="es",
            word_count=2,
            word_ids=[words[1].id, words[0].id],
        ),
    ])
    lessons = await db.get_lessons("en", "es")
    assert lessons[0].word_ids == [words[0].id]
    assert lessons[1].word_ids == [
        words[1].id, words[0].id,
    ]


# --- Lesson Update/Delete Tests ---


async def test_update_lesson_metadata(db):
    lesson = await db.add_lesson(Lesson(
        title="Old Title",
        language_from="en",
        language_to="es",
    ))
    updated = await db.update_lesson(
        lesson.model_copy(update={
            "title": "New Title",
            "description": "Updated",
            "cefr": "B1",
            "tags": ["food"],
        }),
    )
    assert updated.title == "New Title"
    loaded = await db.get_lesson(lesson.id)
    assert loaded.title == "New Title"
    assert loaded.description == "Updated"
    assert loaded.cefr == "B1"
    assert loaded.tags == ["food"]


async def test_update_lesson_replaces_word_ids(db):
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
    ])
    lesson = await db.add_lesson(Lesson(
        title="Test",
        language_from="en",
        language_to="es",
        word_count=2,
        word_ids=[words[0].id, words[1].id],
    ))
    await db.update_lesson(
        lesson.model_copy(update={
            "word_count": 2,
            "word_ids": [words[1].id, words[2].id],
        }),
    )
    loaded = await db.get_lesson(lesson.id)
    assert loaded.word_ids == [
        words[1].id, words[2].id,
    ]


async def test_update_lesson_none_id_raises(db):
    lesson = Lesson(
        title="Test",
        language_from="en",
        language_to="es",
    )
    with pytest.raises(
        ValueError, match="id must be set",
    ):
        await db.update_lesson(lesson)


async def test_update_lesson_not_found_raises(db):
    lesson = Lesson(
        id=999,
        title="Test",
        language_from="en",
        language_to="es",
    )
    with pytest.raises(ValueError, match="not found"):
        await db.update_lesson(lesson)


async def test_delete_lesson(db):
    lesson = await db.add_lesson(Lesson(
        title="Doomed",
        language_from="en",
        language_to="es",
    ))
    await db.delete_lesson(lesson.id)
    assert await db.get_lesson(lesson.id) is None


async def test_delete_lesson_removes_word_links(db):
    words = await db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
    ])
    lesson = await db.add_lesson(Lesson(
        title="Linked",
        language_from="en",
        language_to="es",
        word_count=1,
        word_ids=[words[0].id],
    ))
    await db.delete_lesson(lesson.id)
    assert await db.get_lesson(lesson.id) is None
    # Word itself still exists
    assert len(await db.get_words("en", "es")) == 1


async def test_delete_lesson_not_found_raises(db):
    with pytest.raises(ValueError, match="not found"):
        await db.delete_lesson(999)


# --- Progress Export/Import Tests ---


async def test_export_progress_empty(db):
    u = await db.register_user("u1", "pass")
    result = await db.export_progress(u.id)
    assert result == []


async def test_export_progress_returns_all(db):
    u = await db.register_user("u1", "pass")
    dt = datetime(2026, 3, 1, 12, 0, 0)
    await db.upsert_progress(UserProgress(
        user_id=u.id, word_id=1, next_review=dt,
    ))
    await db.upsert_progress(UserProgress(
        user_id=u.id, word_id=2,
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
        user_id=u1.id, word_id=1, next_review=dt,
    ))
    await db.upsert_progress(UserProgress(
        user_id=u2.id, word_id=2, next_review=dt,
    ))
    result = await db.export_progress(u1.id)
    assert len(result) == 1
    assert result[0]["user_id"] == u1.id


async def test_export_progress_next_review_is_string(db):
    u = await db.register_user("u1", "pass")
    dt = datetime(2026, 6, 15, 10, 30, 0)
    await db.upsert_progress(UserProgress(
        user_id=u.id, word_id=1, next_review=dt,
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
            "user_id": u.id, "word_id": 1,
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
        user_id=u.id, word_id=1,
        repetitions=1, next_review=dt,
    ))
    records = [
        {
            "user_id": u.id, "word_id": 1,
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
        user_id=u.id, word_id=1,
        easiness_factor=2.3, interval=6,
        repetitions=4, next_review=dt,
    ))
    await db.upsert_progress(UserProgress(
        user_id=u.id, word_id=2,
        easiness_factor=1.8, interval=1,
        repetitions=0, next_review=dt,
    ))
    exported = await db.export_progress(u.id)

    # Import into a fresh database
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
        user_id=u.id, word_id=1,
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
            "user_id": u.id, "word_id": 1,
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
            "user_id": u.id, "word_id": 1,
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
            "user_id": 1, "word_id": 1,
            "easiness_factor": 2.5,
            # missing interval, repetitions, next_review
        },
    ]
    with pytest.raises(KeyError, match="Missing keys"):
        await db.import_progress(records)


# --- Migration Tests ---


async def test_migrate_adds_state_columns(tmp_path):
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS users ("
        "    id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "    username TEXT NOT NULL UNIQUE,"
        "    display_name TEXT,"
        "    password_hash TEXT NOT NULL,"
        "    created_at TEXT NOT NULL"
        "        DEFAULT (datetime('now'))"
        ");"
        "INSERT INTO users "
        "(username, password_hash) "
        "VALUES ('u1', 'x');"
        "CREATE TABLE IF NOT EXISTS progress ("
        "    user_id INTEGER NOT NULL,"
        "    word_id INTEGER NOT NULL,"
        "    easiness_factor REAL NOT NULL DEFAULT 2.5,"
        "    interval INTEGER NOT NULL DEFAULT 0,"
        "    repetitions INTEGER NOT NULL DEFAULT 0,"
        "    next_review TEXT NOT NULL,"
        "    PRIMARY KEY (user_id, word_id)"
        ");"
    )
    conn.execute(
        "INSERT INTO progress "
        "(user_id, word_id, easiness_factor, interval, "
        "repetitions, next_review) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (1, 1, 2.5, 6, 3, "2026-03-01T12:00:00"),
    )
    conn.commit()
    conn.close()

    db = await Database.connect(db_path)
    loaded = await db.get_progress(1, 1)
    assert loaded is not None
    assert loaded.state == CardState.REVIEW
    assert loaded.step_index == 0
    assert loaded.repetitions == 3
    await db.close()


# --- Answer History Tests ---


async def test_record_answer(db):
    u = await db.register_user("u1", "pass")
    await db.record_answer(
        u.id, 1, "flashcard", True, 5,
    )
    history = await db.get_answer_history(u.id)
    assert len(history) == 1
    assert history[0].word_id == 1
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
    assert history[0].word_id == 2
    assert history[1].word_id == 1


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
        "(user_id, word_id, exercise_type, "
        " correct, quality, answered_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (u.id, 1, "flashcard", 1, 5,
         "2026-01-01T00:00:00"),
    )
    await db._conn.execute(
        "INSERT INTO answer_history "
        "(user_id, word_id, exercise_type, "
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
    assert history[0].word_id == 2


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
        "(user_id, word_id, exercise_type, "
        " correct, quality, answered_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (u.id, 1, "flashcard", 1, 5,
         "2026-02-27T10:00:00"),
    )
    await db._conn.execute(
        "INSERT INTO answer_history "
        "(user_id, word_id, exercise_type, "
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
    for day, word_id in [("2026-02-26", 1),
                         ("2026-02-27", 2)]:
        await db._conn.execute(
            "INSERT INTO answer_history "
            "(user_id, word_id, exercise_type, "
            " correct, quality, answered_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (u.id, word_id, "flashcard", 1, 5,
             f"{day}T10:00:00"),
        )
    await db._conn.commit()
    stats = await db.daily_stats(u.id, days=365)
    assert len(stats) == 2
    assert stats[0].date == "2026-02-27"
    assert stats[1].date == "2026-02-26"


# --- Weak Word Detection Tests ---


async def _add_history(db, user_id, word_id, correct, n):
    """Helper to insert N answer_history rows."""
    for _ in range(n):
        await db._conn.execute(
            "INSERT INTO answer_history "
            "(user_id, word_id, exercise_type, "
            " correct, quality, answered_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, word_id, "flashcard",
             int(correct), 5 if correct else 1,
             "2026-02-27T10:00:00"),
        )
    await db._conn.commit()


async def test_weak_words_empty(db):
    u = await db.register_user("u1", "pass")
    result = await db.weak_words(u.id, "en", "es")
    assert result == []


async def test_weak_words_detects_weak(db):
    u = await db.register_user("u1", "pass")
    w = await db.add_word("en", "es", "cat", "gato")
    # 1 correct + 3 incorrect = 75% error rate
    await _add_history(db, u.id, w.id, True, 1)
    await _add_history(db, u.id, w.id, False, 3)
    result = await db.weak_words(u.id, "en", "es")
    assert len(result) == 1
    assert result[0].word.id == w.id
    assert result[0].attempts == 4
    assert result[0].errors == 3
    assert result[0].error_rate == 0.75


async def test_weak_words_excludes_strong(db):
    u = await db.register_user("u1", "pass")
    w = await db.add_word("en", "es", "cat", "gato")
    # 4 correct + 0 incorrect = 0% error rate
    await _add_history(db, u.id, w.id, True, 4)
    result = await db.weak_words(u.id, "en", "es")
    assert result == []


async def test_weak_words_min_attempts(db):
    u = await db.register_user("u1", "pass")
    w = await db.add_word("en", "es", "cat", "gato")
    # Only 2 attempts (below default min_attempts=3)
    await _add_history(db, u.id, w.id, False, 2)
    result = await db.weak_words(u.id, "en", "es")
    assert result == []

    result = await db.weak_words(
        u.id, "en", "es", min_attempts=2,
    )
    assert len(result) == 1


async def test_weak_words_threshold(db):
    u = await db.register_user("u1", "pass")
    w = await db.add_word("en", "es", "cat", "gato")
    # 2 correct + 1 incorrect = 33% error rate
    await _add_history(db, u.id, w.id, True, 2)
    await _add_history(db, u.id, w.id, False, 1)

    # Default threshold 0.5 => not weak
    result = await db.weak_words(u.id, "en", "es")
    assert result == []

    # Lower threshold => weak
    result = await db.weak_words(
        u.id, "en", "es", threshold=0.3,
    )
    assert len(result) == 1


async def test_weak_words_ordered_by_error_rate(db):
    u = await db.register_user("u1", "pass")
    w1 = await db.add_word("en", "es", "cat", "gato")
    w2 = await db.add_word("en", "es", "dog", "perro")
    # w1: 50% error rate
    await _add_history(db, u.id, w1.id, True, 2)
    await _add_history(db, u.id, w1.id, False, 2)
    # w2: 75% error rate
    await _add_history(db, u.id, w2.id, True, 1)
    await _add_history(db, u.id, w2.id, False, 3)

    result = await db.weak_words(u.id, "en", "es")
    assert len(result) == 2
    assert result[0].word.id == w2.id
    assert result[1].word.id == w1.id


async def test_weak_words_filters_by_language(db):
    u = await db.register_user("u1", "pass")
    w1 = await db.add_word("en", "es", "cat", "gato")
    w2 = await db.add_word("en", "fr", "cat", "chat")
    await _add_history(db, u.id, w1.id, False, 4)
    await _add_history(db, u.id, w2.id, False, 4)

    result = await db.weak_words(u.id, "en", "es")
    assert len(result) == 1
    assert result[0].word.id == w1.id


async def test_weak_words_filters_by_user(db):
    u1 = await db.register_user("u1", "pass")
    u2 = await db.register_user("u2", "pass")
    w = await db.add_word("en", "es", "cat", "gato")
    await _add_history(db, u1.id, w.id, False, 4)
    await _add_history(db, u2.id, w.id, False, 4)

    result = await db.weak_words(u1.id, "en", "es")
    assert len(result) == 1

    result = await db.weak_words(u2.id, "en", "es")
    assert len(result) == 1


async def test_weak_words_limit(db):
    u = await db.register_user("u1", "pass")
    for i in range(5):
        w = await db.add_word(
            "en", "es", f"word{i}", f"w{i}",
        )
        await _add_history(db, u.id, w.id, False, 4)

    result = await db.weak_words(
        u.id, "en", "es", limit=3,
    )
    assert len(result) == 3


# --- Retention Rate Tests ---


async def test_retention_rate_empty(db):
    u = await db.register_user("u1", "pass")
    assert await db.retention_rate(u.id) == 0.0


async def test_retention_rate_all_correct(db):
    u = await db.register_user("u1", "pass")
    w = await db.add_word("en", "es", "cat", "gato")
    await _add_history(db, u.id, w.id, True, 10)
    assert await db.retention_rate(u.id) == 100.0


async def test_retention_rate_mixed(db):
    u = await db.register_user("u1", "pass")
    w = await db.add_word("en", "es", "cat", "gato")
    await _add_history(db, u.id, w.id, True, 7)
    await _add_history(db, u.id, w.id, False, 3)
    assert await db.retention_rate(u.id) == 70.0


# --- Forecast Tests ---


async def test_forecast_empty(db):
    u = await db.register_user("u1", "pass")
    result = await db.forecast(u.id, days=3)
    assert len(result) == 3
    assert all(f.due_count == 0 for f in result)


async def test_forecast_with_due_cards(db):
    u = await db.register_user("u1", "pass")
    w = await db.add_word("en", "es", "cat", "gato")
    # Schedule a review for today
    progress = UserProgress(
        user_id=u.id,
        word_id=w.id,
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
    w = await db.add_word("en", "es", "cat", "gato")
    progress = UserProgress(
        user_id=u.id,
        word_id=w.id,
        state=CardState.SUSPENDED,
        next_review=datetime.now(),
    )
    await db.upsert_progress(progress)
    result = await db.forecast(u.id, days=3)
    assert result[0].due_count == 0


# --- CSV/TSV Import Tests ---


async def test_import_words_csv_basic(db, tmp_path):
    csv_file = tmp_path / "words.csv"
    csv_file.write_text(
        "word_from,word_to\ncat,gato\ndog,perro\n",
        encoding="utf-8",
    )
    words = await import_words_csv(
        db, csv_file, "en", "es",
    )
    assert len(words) == 2
    assert words[0].word_from == "cat"
    assert words[0].word_to == "gato"
    assert words[0].id is not None


async def test_import_words_csv_optional_columns(
    db, tmp_path,
):
    csv_file = tmp_path / "words.csv"
    csv_file.write_text(
        "word_from,word_to,gender,cefr,tags\n"
        "libro,book,m,A1,\"education,objects\"\n",
        encoding="utf-8",
    )
    words = await import_words_csv(
        db, csv_file, "es", "en",
    )
    assert len(words) == 1
    assert words[0].gender == "m"
    assert words[0].cefr == "A1"
    assert words[0].tags == ["education", "objects"]


async def test_import_words_tsv(db, tmp_path):
    tsv_file = tmp_path / "words.tsv"
    tsv_file.write_text(
        "word_from\tword_to\ncat\tgato\n",
        encoding="utf-8",
    )
    words = await import_words_csv(
        db, tsv_file, "en", "es",
    )
    assert len(words) == 1
    assert words[0].word_from == "cat"


async def test_import_words_csv_custom_columns(
    db, tmp_path,
):
    csv_file = tmp_path / "words.csv"
    csv_file.write_text(
        "spanish,english\ngato,cat\n",
        encoding="utf-8",
    )
    words = await import_words_csv(
        db, csv_file, "es", "en",
        word_from_col="spanish",
        word_to_col="english",
    )
    assert words[0].word_from == "gato"
    assert words[0].word_to == "cat"


async def test_import_words_csv_missing_column(
    db, tmp_path,
):
    csv_file = tmp_path / "words.csv"
    csv_file.write_text(
        "word,meaning\ncat,gato\n",
        encoding="utf-8",
    )
    with pytest.raises(
        ValueError, match="Required column",
    ):
        await import_words_csv(
            db, csv_file, "en", "es",
        )


async def test_import_words_csv_with_owner(
    db, tmp_path,
):
    u = await db.register_user("u1", "pass")
    csv_file = tmp_path / "words.csv"
    csv_file.write_text(
        "word_from,word_to\ncat,gato\n",
        encoding="utf-8",
    )
    words = await import_words_csv(
        db, csv_file, "en", "es", owner_id=u.id,
    )
    assert words[0].owner_id == u.id


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
    assert loaded.stage == ConversationStage.AWAITING_ANSWER
    assert loaded.data == {"exercise_id": 42}


async def test_get_conversation_state_nonexistent(db):
    result = await db.get_conversation_state(999)
    assert result is None


async def test_save_conversation_state_overwrites(db):
    u = await db.register_user("u1", "pass")
    state1 = ConversationState(
        user_id=u.id,
        stage=ConversationStage.CHOOSING_LESSON,
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
    assert loaded.stage == ConversationStage.EXERCISING
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
    assert r2.stage == ConversationStage.EXERCISING


async def test_delete_conversation_state(db):
    u = await db.register_user("u1", "pass")
    state = ConversationState(
        user_id=u.id,
        stage=ConversationStage.VIEWING_STATS,
    )
    await db.save_conversation_state(state)

    deleted = await db.delete_conversation_state(u.id)
    assert deleted is True

    deleted2 = await db.delete_conversation_state(u.id)
    assert deleted2 is False

    loaded = await db.get_conversation_state(u.id)
    assert loaded is None


async def test_conversation_state_preserves_data(db):
    u = await db.register_user("u1", "pass")
    state = ConversationState(
        user_id=u.id,
        stage=ConversationStage.CHOOSING_LESSON,
        data={
            "page": 2,
            "cefr": "A1",
            "tags": ["food", "travel"],
        },
    )
    await db.save_conversation_state(state)

    loaded = await db.get_conversation_state(u.id)
    assert loaded is not None
    assert loaded.data["page"] == 2
    assert loaded.data["cefr"] == "A1"
    assert loaded.data["tags"] == ["food", "travel"]
