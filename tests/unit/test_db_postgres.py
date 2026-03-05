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
    "postgresql://rembrandt:rembrandt@localhost/rembrandt"
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
]


@pytest.fixture
def pg_db():
    """Fresh PostgreSQL database for each test.

    Drops and recreates all tables to ensure isolation.
    """
    from rembrandt.db_postgres import PostgresDatabase

    conn = psycopg.connect(_DSN, autocommit=True)
    with conn.cursor() as cur:
        cur.execute(
            "DROP TABLE IF EXISTS "
            "answer_history, lesson_words, lessons, "
            "progress, words, user_sessions, users "
            "CASCADE"
        )
    conn.close()

    db = PostgresDatabase(_DSN)
    yield db
    db.close()


# --- Word CRUD Tests ---


def test_add_word(pg_db):
    word = pg_db.add_word("en", "es", "hello", "hola")
    assert word.id is not None
    assert word.word_from == "hello"
    assert word.word_to == "hola"


def test_add_words_bulk(pg_db):
    from rembrandt.models import Word

    words = pg_db.add_words([
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


def test_get_words_empty(pg_db):
    result = pg_db.get_words("en", "es")
    assert result == []


def test_get_words_filters_by_language(pg_db):
    pg_db.add_word("en", "es", "hello", "hola")
    pg_db.add_word("en", "fr", "hello", "bonjour")

    es_words = pg_db.get_words("en", "es")
    assert len(es_words) == 1
    assert es_words[0].word_to == "hola"

    fr_words = pg_db.get_words("en", "fr")
    assert len(fr_words) == 1
    assert fr_words[0].word_to == "bonjour"


def test_add_word_with_tags(pg_db):
    word = pg_db.add_word(
        "en", "es", "bread", "pan",
        tags=["food"],
    )
    assert word.tags == ["food"]
    loaded = pg_db.get_words("en", "es")
    assert loaded[0].tags == ["food"]


def test_tags_default_empty(pg_db):
    pg_db.add_word("en", "es", "cat", "gato")
    loaded = pg_db.get_words("en", "es")
    assert loaded[0].tags == []


def test_add_word_with_cefr(pg_db):
    word = pg_db.add_word(
        "es", "en", "ser", "to be", cefr="A1",
    )
    assert word.cefr == "A1"
    loaded = pg_db.get_words("es", "en")
    assert loaded[0].cefr == "A1"


def test_update_word(pg_db):
    word = pg_db.add_word("en", "es", "cat", "gato")
    updated = pg_db.update_word(
        word.model_copy(update={"word_to": "gatito"}),
    )
    assert updated.word_to == "gatito"
    loaded = pg_db.get_words("en", "es")
    assert loaded[0].word_to == "gatito"


def test_update_word_not_found_raises(pg_db):
    from rembrandt.models import Word

    word = Word(
        id=999,
        language_from="en", language_to="es",
        word_from="cat", word_to="gato",
    )
    with pytest.raises(ValueError, match="not found"):
        pg_db.update_word(word)


def test_delete_word(pg_db):
    word = pg_db.add_word("en", "es", "cat", "gato")
    pg_db.delete_word(word.id)
    assert pg_db.get_words("en", "es") == []


def test_delete_word_not_found_raises(pg_db):
    with pytest.raises(ValueError, match="not found"):
        pg_db.delete_word(999)


# --- User CRUD Tests ---


def test_register_user(pg_db):
    user = pg_db.register_user("alice", "s3cret")
    assert user.id is not None
    assert user.username == "alice"


def test_register_user_duplicate_raises(pg_db):
    pg_db.register_user("alice", "pass1")
    with pytest.raises(
        ValueError, match="already exists",
    ):
        pg_db.register_user("alice", "pass2")


def test_authenticate_user_valid(pg_db):
    pg_db.register_user("alice", "s3cret")
    user = pg_db.authenticate_user("alice", "s3cret")
    assert user is not None
    assert user.username == "alice"


def test_authenticate_user_wrong_password(pg_db):
    pg_db.register_user("alice", "s3cret")
    assert pg_db.authenticate_user(
        "alice", "wrong",
    ) is None


# --- User Session Tests ---


def test_create_session(pg_db):
    user = pg_db.register_user("alice", "pass")
    session = pg_db.create_session(user.id)
    assert session.id is not None
    assert session.user_id == user.id
    assert len(session.token) == 64


def test_get_session_valid(pg_db):
    user = pg_db.register_user("alice", "pass")
    session = pg_db.create_session(user.id)
    loaded = pg_db.get_session(session.token)
    assert loaded is not None
    assert loaded.token == session.token


def test_get_session_expired(pg_db):
    user = pg_db.register_user("alice", "pass")
    session = pg_db.create_session(
        user.id, ttl_hours=0,
    )
    assert pg_db.get_session(session.token) is None


def test_delete_session(pg_db):
    user = pg_db.register_user("alice", "pass")
    session = pg_db.create_session(user.id)
    pg_db.delete_session(session.token)
    assert pg_db.get_session(session.token) is None


# --- Progress CRUD Tests ---


def test_upsert_progress_insert(pg_db):
    from rembrandt.models import CardState, UserProgress

    progress = UserProgress(
        user_id="u1",
        word_id=1,
        easiness_factor=2.5,
        interval=1,
        repetitions=1,
        state=CardState.REVIEW,
        next_review=datetime(2026, 3, 1, 12, 0, 0),
    )
    pg_db.upsert_progress(progress)
    loaded = pg_db.get_progress("u1", 1)
    assert loaded is not None
    assert loaded.easiness_factor == 2.5
    assert loaded.state == CardState.REVIEW


def test_upsert_progress_update(pg_db):
    from rembrandt.models import UserProgress

    progress = UserProgress(
        user_id="u1",
        word_id=1,
        next_review=datetime(2026, 3, 1, 12, 0, 0),
    )
    pg_db.upsert_progress(progress)

    progress.easiness_factor = 2.1
    progress.interval = 6
    progress.repetitions = 3
    pg_db.upsert_progress(progress)

    loaded = pg_db.get_progress("u1", 1)
    assert loaded.easiness_factor == 2.1
    assert loaded.interval == 6
    assert loaded.repetitions == 3


def test_get_all_progress(pg_db):
    from rembrandt.models import UserProgress

    dt = datetime(2026, 3, 1, 12, 0, 0)
    pg_db.upsert_progress(UserProgress(
        user_id="u1", word_id=1, next_review=dt,
    ))
    pg_db.upsert_progress(UserProgress(
        user_id="u1", word_id=3, next_review=dt,
    ))
    result = pg_db.get_all_progress("u1", [1, 2, 3])
    assert len(result) == 2
    assert 1 in result
    assert 3 in result
    assert 2 not in result


def test_get_all_progress_empty(pg_db):
    result = pg_db.get_all_progress("u1", [])
    assert result == {}


# --- Progress Export/Import Tests ---


def test_export_import_roundtrip(pg_db):
    from rembrandt.models import UserProgress

    dt = datetime(2026, 3, 1, 12, 0, 0)
    pg_db.upsert_progress(UserProgress(
        user_id="u1", word_id=1,
        easiness_factor=2.3, interval=6,
        repetitions=4, next_review=dt,
    ))
    exported = pg_db.export_progress("u1")
    assert len(exported) == 1
    assert exported[0]["next_review"] == (
        "2026-03-01T12:00:00"
    )


def test_import_progress_missing_key_raises(pg_db):
    records = [
        {
            "user_id": "u1", "word_id": 1,
            "easiness_factor": 2.5,
        },
    ]
    with pytest.raises(KeyError, match="Missing keys"):
        pg_db.import_progress(records)


# --- Answer History Tests ---


def test_record_answer(pg_db):
    pg_db.record_answer(
        "u1", 1, "flashcard", True, 5,
    )
    history = pg_db.get_answer_history("u1")
    assert len(history) == 1
    assert history[0].correct is True
    assert history[0].quality == 5


def test_get_answer_history_ordered(pg_db):
    pg_db.record_answer(
        "u1", 1, "flashcard", True, 5,
    )
    pg_db.record_answer(
        "u1", 2, "multiple_choice", False, 1,
    )
    history = pg_db.get_answer_history("u1")
    assert len(history) == 2
    assert history[0].word_id == 2
    assert history[1].word_id == 1


def test_get_answer_history_limit(pg_db):
    for i in range(5):
        pg_db.record_answer(
            "u1", i, "flashcard", True, 5,
        )
    history = pg_db.get_answer_history("u1", limit=3)
    assert len(history) == 3


# --- Lesson CRUD Tests ---


def test_add_lesson(pg_db):
    from rembrandt.models import Lesson, Word

    words = pg_db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="dog", word_to="perro",
        ),
    ])
    lesson = pg_db.add_lesson(Lesson(
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


def test_get_lesson_by_id(pg_db):
    from rembrandt.models import Lesson, Word

    words = pg_db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="cat", word_to="gato",
        ),
    ])
    lesson = pg_db.add_lesson(Lesson(
        title="Test Lesson",
        language_from="en",
        language_to="es",
        cefr="A1",
        tags=["test"],
        word_count=1,
        word_ids=[words[0].id],
    ))
    loaded = pg_db.get_lesson(lesson.id)
    assert loaded is not None
    assert loaded.title == "Test Lesson"
    assert loaded.tags == ["test"]
    assert loaded.word_ids == [words[0].id]


def test_get_lessons_filter_tag(pg_db):
    from rembrandt.models import Lesson

    pg_db.add_lessons([
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
    food = pg_db.get_lessons("en", "es", tag="food")
    assert len(food) == 2
    titles = {ls.title for ls in food}
    assert titles == {"Food Lesson", "Multi Tag"}


def test_update_lesson(pg_db):
    from rembrandt.models import Lesson

    lesson = pg_db.add_lesson(Lesson(
        title="Old Title",
        language_from="en",
        language_to="es",
    ))
    pg_db.update_lesson(
        lesson.model_copy(update={
            "title": "New Title",
            "cefr": "B1",
        }),
    )
    loaded = pg_db.get_lesson(lesson.id)
    assert loaded.title == "New Title"
    assert loaded.cefr == "B1"


def test_delete_lesson(pg_db):
    from rembrandt.models import Lesson

    lesson = pg_db.add_lesson(Lesson(
        title="Doomed",
        language_from="en",
        language_to="es",
    ))
    pg_db.delete_lesson(lesson.id)
    assert pg_db.get_lesson(lesson.id) is None


def test_delete_lesson_not_found_raises(pg_db):
    with pytest.raises(ValueError, match="not found"):
        pg_db.delete_lesson(999)


# --- Context Manager Tests ---


def test_context_manager(pg_db):
    pg_db.add_word("en", "es", "cat", "gato")
    words = pg_db.get_words("en", "es")
    assert len(words) == 1
