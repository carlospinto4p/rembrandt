"""Tests for rembrandt.db."""

from datetime import datetime, timedelta

import pytest

from rembrandt.db import Database
from rembrandt.models import Lesson, UserProgress, Word


# --- User CRUD Tests ---


def test_register_user(db):
    user = db.register_user("alice", "s3cret")
    assert user.id is not None
    assert user.username == "alice"
    assert user.display_name is None


def test_register_user_with_display_name(db):
    user = db.register_user(
        "bob", "pass", display_name="Bob S.",
    )
    assert user.display_name == "Bob S."


def test_register_user_duplicate_raises(db):
    db.register_user("alice", "pass1")
    with pytest.raises(ValueError, match="already exists"):
        db.register_user("alice", "pass2")


def test_get_user_found(db):
    db.register_user("alice", "pass")
    user = db.get_user("alice")
    assert user is not None
    assert user.username == "alice"


def test_get_user_not_found(db):
    assert db.get_user("ghost") is None


def test_authenticate_user_valid(db):
    db.register_user("alice", "s3cret")
    user = db.authenticate_user("alice", "s3cret")
    assert user is not None
    assert user.username == "alice"


def test_authenticate_user_wrong_password(db):
    db.register_user("alice", "s3cret")
    assert db.authenticate_user("alice", "wrong") is None


def test_authenticate_user_unknown_username(db):
    assert db.authenticate_user("ghost", "pass") is None


# --- User Session Tests ---


def test_create_session(db):
    user = db.register_user("alice", "pass")
    session = db.create_session(user.id)
    assert session.id is not None
    assert session.user_id == user.id
    assert len(session.token) == 64  # 32 bytes hex
    assert session.expires_at > session.created_at


def test_create_session_custom_ttl(db):
    user = db.register_user("alice", "pass")
    session = db.create_session(user.id, ttl_hours=48)
    diff = session.expires_at - session.created_at
    assert abs(diff.total_seconds() - 48 * 3600) < 2


def test_get_session_valid(db):
    user = db.register_user("alice", "pass")
    session = db.create_session(user.id)
    loaded = db.get_session(session.token)
    assert loaded is not None
    assert loaded.token == session.token
    assert loaded.user_id == user.id


def test_get_session_not_found(db):
    assert db.get_session("nonexistent") is None


def test_get_session_expired(db):
    user = db.register_user("alice", "pass")
    session = db.create_session(user.id, ttl_hours=0)
    assert db.get_session(session.token) is None


def test_delete_session(db):
    user = db.register_user("alice", "pass")
    session = db.create_session(user.id)
    db.delete_session(session.token)
    assert db.get_session(session.token) is None


def test_delete_user_sessions(db):
    user = db.register_user("alice", "pass")
    s1 = db.create_session(user.id)
    s2 = db.create_session(user.id)
    db.delete_user_sessions(user.id)
    assert db.get_session(s1.token) is None
    assert db.get_session(s2.token) is None


# --- Word CRUD Tests ---


def test_add_word(db):
    word = db.add_word("en", "es", "hello", "hola")
    assert word.id is not None
    assert word.word_from == "hello"
    assert word.word_to == "hola"


def test_add_words_bulk(db):
    words = db.add_words([
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


def test_get_words_empty(db):
    result = db.get_words("en", "es")
    assert result == []


def test_get_words_filters_by_language(db):
    db.add_word("en", "es", "hello", "hola")
    db.add_word("en", "fr", "hello", "bonjour")

    es_words = db.get_words("en", "es")
    assert len(es_words) == 1
    assert es_words[0].word_to == "hola"

    fr_words = db.get_words("en", "fr")
    assert len(fr_words) == 1
    assert fr_words[0].word_to == "bonjour"


def test_add_word_auto_increments_id(db):
    w1 = db.add_word("en", "es", "cat", "gato")
    w2 = db.add_word("en", "es", "dog", "perro")
    assert w2.id == w1.id + 1


def test_add_word_with_gender(db):
    word = db.add_word(
        "es", "en", "casa", "house", gender="f",
    )
    assert word.gender == "f"
    loaded = db.get_words("es", "en")
    assert loaded[0].gender == "f"
    assert loaded[0].conjugation_group is None


def test_add_word_with_conjugation_group(db):
    word = db.add_word(
        "es", "en", "hablar", "to speak",
        conjugation_group="ar",
    )
    assert word.conjugation_group == "ar"
    loaded = db.get_words("es", "en")
    assert loaded[0].conjugation_group == "ar"
    assert loaded[0].gender is None


def test_add_words_bulk_with_metadata(db):
    words = db.add_words([
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
    loaded = db.get_words("es", "en")
    assert loaded[0].gender == "f"
    assert loaded[1].conjugation_group == "ar"


def test_add_word_with_cefr(db):
    word = db.add_word(
        "es", "en", "ser", "to be", cefr="A1",
    )
    assert word.cefr == "A1"
    loaded = db.get_words("es", "en")
    assert loaded[0].cefr == "A1"


def test_cefr_default_none(db):
    db.add_word("en", "es", "cat", "gato")
    loaded = db.get_words("en", "es")
    assert loaded[0].cefr is None


def test_cefr_bulk_roundtrip(db):
    db.add_words([
        Word(
            language_from="es", language_to="en",
            word_from="ser", word_to="to be",
            cefr="A1",
        ),
        Word(
            language_from="es", language_to="en",
            word_from="prescindir", word_to="to do without",
            cefr="C1",
        ),
        Word(
            language_from="es", language_to="en",
            word_from="casa", word_to="house",
        ),
    ])
    loaded = db.get_words("es", "en")
    assert loaded[0].cefr == "A1"
    assert loaded[1].cefr == "C1"
    assert loaded[2].cefr is None


def test_tags_default_empty(db):
    db.add_word("en", "es", "cat", "gato")
    loaded = db.get_words("en", "es")
    assert loaded[0].tags == []


def test_tags_roundtrip(db):
    db.add_word(
        "en", "es", "bread", "pan",
        tags=["food"],
    )
    loaded = db.get_words("en", "es")
    assert loaded[0].tags == ["food"]


def test_tags_bulk_roundtrip(db):
    db.add_words([
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
    loaded = db.get_words("en", "es")
    assert loaded[0].tags == ["food"]
    assert loaded[1].tags == ["family"]
    assert loaded[2].tags == []


# --- Word Update/Delete Tests ---


def test_update_word(db):
    word = db.add_word("en", "es", "cat", "gato")
    updated = db.update_word(
        word.model_copy(update={"word_to": "gatito"}),
    )
    assert updated.word_to == "gatito"
    loaded = db.get_words("en", "es")
    assert loaded[0].word_to == "gatito"


def test_update_word_all_fields(db):
    word = db.add_word("en", "es", "cat", "gato")
    modified = word.model_copy(update={
        "word_from": "kitten",
        "word_to": "gatito",
        "gender": "m",
        "tags": ["animals"],
        "cefr": "A1",
    })
    updated = db.update_word(modified)
    assert updated.word_from == "kitten"
    assert updated.gender == "m"
    assert updated.tags == ["animals"]
    assert updated.cefr == "A1"


def test_update_word_none_id_raises(db):
    word = Word(
        language_from="en", language_to="es",
        word_from="cat", word_to="gato",
    )
    with pytest.raises(ValueError, match="id must be set"):
        db.update_word(word)


def test_update_word_not_found_raises(db):
    word = Word(
        id=999,
        language_from="en", language_to="es",
        word_from="cat", word_to="gato",
    )
    with pytest.raises(ValueError, match="not found"):
        db.update_word(word)


def test_delete_word(db):
    word = db.add_word("en", "es", "cat", "gato")
    db.delete_word(word.id)
    assert db.get_words("en", "es") == []


def test_delete_word_not_found_raises(db):
    with pytest.raises(ValueError, match="not found"):
        db.delete_word(999)


# --- Progress CRUD Tests ---


def test_get_progress_nonexistent(db):
    result = db.get_progress("u1", 999)
    assert result is None


def test_upsert_progress_insert(db):
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        easiness_factor=2.5,
        interval=1,
        repetitions=1,
        next_review=datetime(2026, 3, 1, 12, 0, 0),
    )
    db.upsert_progress(progress)

    loaded = db.get_progress("u1", 1)
    assert loaded is not None
    assert loaded.easiness_factor == 2.5
    assert loaded.interval == 1
    assert loaded.repetitions == 1


def test_upsert_progress_update(db):
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        next_review=datetime(2026, 3, 1, 12, 0, 0),
    )
    db.upsert_progress(progress)

    progress.easiness_factor = 2.1
    progress.interval = 6
    progress.repetitions = 3
    db.upsert_progress(progress)

    loaded = db.get_progress("u1", 1)
    assert loaded is not None
    assert loaded.easiness_factor == 2.1
    assert loaded.interval == 6
    assert loaded.repetitions == 3


def test_progress_roundtrip_datetime(db):
    dt = datetime(2026, 6, 15, 10, 30, 0)
    progress = UserProgress(
        user_id="u1",
        word_id=1,
        next_review=dt,
    )
    db.upsert_progress(progress)

    loaded = db.get_progress("u1", 1)
    assert loaded is not None
    assert loaded.next_review == dt


def test_get_all_progress(db):
    dt = datetime(2026, 3, 1, 12, 0, 0)
    db.upsert_progress(UserProgress(
        user_id="u1", word_id=1, next_review=dt,
    ))
    db.upsert_progress(UserProgress(
        user_id="u1", word_id=3, next_review=dt,
    ))

    result = db.get_all_progress("u1", [1, 2, 3])
    assert len(result) == 2
    assert 1 in result
    assert 3 in result
    assert 2 not in result


def test_get_all_progress_empty(db):
    result = db.get_all_progress("u1", [])
    assert result == {}


# --- Context Manager Tests ---


def test_context_manager(tmp_path):
    with Database(tmp_path / "ctx.db") as db:
        db.add_word("en", "es", "cat", "gato")
        words = db.get_words("en", "es")
        assert len(words) == 1


# --- Lesson CRUD Tests ---


def test_add_lesson(db):
    words = db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="dog", word_to="perro",
        ),
    ])
    lesson = db.add_lesson(Lesson(
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


def test_add_lesson_word_order_preserved(db):
    words = db.add_words([
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
    lesson = db.add_lesson(Lesson(
        title="Reversed order",
        language_from="en",
        language_to="es",
        word_count=3,
        word_ids=ids,
    ))
    loaded = db.get_lesson(lesson.id)
    assert loaded is not None
    assert loaded.word_ids == ids


def test_add_lessons_bulk(db):
    words = db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="dog", word_to="perro",
        ),
    ])
    lessons = db.add_lessons([
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


def test_get_lessons_by_language(db):
    db.add_lessons([
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
    es = db.get_lessons("en", "es")
    assert len(es) == 1
    assert es[0].title == "EN-ES Lesson"

    fr = db.get_lessons("en", "fr")
    assert len(fr) == 1
    assert fr[0].title == "EN-FR Lesson"


def test_get_lessons_filter_cefr(db):
    db.add_lessons([
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
    result = db.get_lessons("en", "es", cefr="A1")
    assert len(result) == 1
    assert result[0].title == "A1 Lesson"


def test_get_lessons_filter_tag(db):
    db.add_lessons([
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
    food = db.get_lessons("en", "es", tag="food")
    assert len(food) == 2
    titles = {ls.title for ls in food}
    assert titles == {"Food Lesson", "Multi Tag"}


def test_get_lesson_by_id(db):
    words = db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
    ])
    lesson = db.add_lesson(Lesson(
        title="Test Lesson",
        language_from="en",
        language_to="es",
        cefr="A1",
        tags=["test"],
        word_count=1,
        word_ids=[words[0].id],
    ))
    loaded = db.get_lesson(lesson.id)
    assert loaded is not None
    assert loaded.title == "Test Lesson"
    assert loaded.cefr == "A1"
    assert loaded.tags == ["test"]
    assert loaded.word_ids == [words[0].id]


def test_get_lesson_not_found(db):
    assert db.get_lesson(999) is None


def test_lesson_with_no_words(db):
    lesson = db.add_lesson(Lesson(
        title="Empty Lesson",
        language_from="en",
        language_to="es",
    ))
    loaded = db.get_lesson(lesson.id)
    assert loaded is not None
    assert loaded.word_ids == []
    assert loaded.word_count == 0


def test_get_lessons_populates_word_ids(db):
    words = db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="dog", word_to="perro",
        ),
    ])
    db.add_lessons([
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
    lessons = db.get_lessons("en", "es")
    assert lessons[0].word_ids == [words[0].id]
    assert lessons[1].word_ids == [words[1].id, words[0].id]


# --- Lesson Update/Delete Tests ---


def test_update_lesson_metadata(db):
    lesson = db.add_lesson(Lesson(
        title="Old Title",
        language_from="en",
        language_to="es",
    ))
    updated = db.update_lesson(
        lesson.model_copy(update={
            "title": "New Title",
            "description": "Updated",
            "cefr": "B1",
            "tags": ["food"],
        }),
    )
    assert updated.title == "New Title"
    loaded = db.get_lesson(lesson.id)
    assert loaded.title == "New Title"
    assert loaded.description == "Updated"
    assert loaded.cefr == "B1"
    assert loaded.tags == ["food"]


def test_update_lesson_replaces_word_ids(db):
    words = db.add_words([
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
    lesson = db.add_lesson(Lesson(
        title="Test",
        language_from="en",
        language_to="es",
        word_count=2,
        word_ids=[words[0].id, words[1].id],
    ))
    db.update_lesson(
        lesson.model_copy(update={
            "word_count": 2,
            "word_ids": [words[1].id, words[2].id],
        }),
    )
    loaded = db.get_lesson(lesson.id)
    assert loaded.word_ids == [words[1].id, words[2].id]


def test_update_lesson_none_id_raises(db):
    lesson = Lesson(
        title="Test",
        language_from="en",
        language_to="es",
    )
    with pytest.raises(ValueError, match="id must be set"):
        db.update_lesson(lesson)


def test_update_lesson_not_found_raises(db):
    lesson = Lesson(
        id=999,
        title="Test",
        language_from="en",
        language_to="es",
    )
    with pytest.raises(ValueError, match="not found"):
        db.update_lesson(lesson)


def test_delete_lesson(db):
    lesson = db.add_lesson(Lesson(
        title="Doomed",
        language_from="en",
        language_to="es",
    ))
    db.delete_lesson(lesson.id)
    assert db.get_lesson(lesson.id) is None


def test_delete_lesson_removes_word_links(db):
    words = db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
    ])
    lesson = db.add_lesson(Lesson(
        title="Linked",
        language_from="en",
        language_to="es",
        word_count=1,
        word_ids=[words[0].id],
    ))
    db.delete_lesson(lesson.id)
    assert db.get_lesson(lesson.id) is None
    # Word itself still exists
    assert len(db.get_words("en", "es")) == 1


def test_delete_lesson_not_found_raises(db):
    with pytest.raises(ValueError, match="not found"):
        db.delete_lesson(999)
