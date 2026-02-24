"""Tests for rembrandt.lessons."""

import json

from rembrandt.db import Database
from rembrandt.lessons import load_lessons
from rembrandt.models import Word


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


# --- Tests ---


def test_load_lessons_resolves_ranks(tmp_path):
    vocab = _make_vocab([1, 2, 3])
    _write_json(tmp_path / "vocab.json", vocab)

    db = Database(tmp_path / "test.db")
    words = db.add_words([
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

    result = load_lessons(
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
    db.close()


def test_load_lessons_preserves_order(tmp_path):
    vocab = _make_vocab([1, 2, 3])
    _write_json(tmp_path / "vocab.json", vocab)

    db = Database(tmp_path / "test.db")
    words = db.add_words([
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

    result = load_lessons(
        tmp_path / "lessons.json",
        tmp_path / "vocab.json",
        db,
        language_from="en",
        language_to="es",
    )
    assert result[0].word_ids == [
        words[2].id, words[0].id, words[1].id,
    ]
    db.close()


def test_load_lessons_skips_unresolved_ranks(tmp_path):
    vocab = _make_vocab([1, 2])
    _write_json(tmp_path / "vocab.json", vocab)

    db = Database(tmp_path / "test.db")
    db.add_words([
        Word(
            language_from="en", language_to="es",
            word_from="def_1", word_to="word_1",
        ),
    ])

    lessons_data = [
        _make_lesson("Partial", [1, 2, 99]),
    ]
    _write_json(tmp_path / "lessons.json", lessons_data)

    result = load_lessons(
        tmp_path / "lessons.json",
        tmp_path / "vocab.json",
        db,
        language_from="en",
        language_to="es",
    )
    assert result[0].word_count == 1
    db.close()


def test_load_lessons_empty_input(tmp_path):
    _write_json(tmp_path / "vocab.json", [])
    _write_json(tmp_path / "lessons.json", [])

    db = Database(tmp_path / "test.db")
    result = load_lessons(
        tmp_path / "lessons.json",
        tmp_path / "vocab.json",
        db,
        language_from="en",
        language_to="es",
    )
    assert result == []
    db.close()
