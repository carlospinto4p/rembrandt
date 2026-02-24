"""Tests for rembrandt.db."""

from datetime import datetime

from rembrandt.db import Database
from rembrandt.models import UserProgress, Word


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
