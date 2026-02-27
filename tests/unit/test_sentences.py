"""Tests for rembrandt.sentences."""

import json

import pytest

from rembrandt.sentences import (
    extend_cloze_templates,
    generate_cloze,
    generate_translation_cloze_sentence,
    load_cloze_templates,
    _VERB_TEMPLATES,
    _NOUN_M_TEMPLATES,
)


# --- Verb Cloze Tests ---


def test_generate_cloze_verb():
    sentence, answer = generate_cloze(
        "hablar", conjugation_group="ar",
    )
    assert "___" in sentence
    assert "hablar" not in sentence
    assert answer == "hablar"


# --- Masculine Noun Cloze Tests ---


def test_generate_cloze_masculine_noun():
    sentence, answer = generate_cloze("libro", gender="m")
    assert "___" in sentence
    assert "libro" not in sentence
    assert answer == "libro"


# --- Feminine Noun Cloze Tests ---


def test_generate_cloze_feminine_noun():
    sentence, answer = generate_cloze("casa", gender="f")
    assert "___" in sentence
    assert "casa" not in sentence
    assert answer == "casa"


# --- Adjective Cloze Tests ---


def test_generate_cloze_adjective():
    sentence, answer = generate_cloze("grande")
    assert "___" in sentence
    assert "grande" not in sentence
    assert answer == "grande"


# --- Return Value Tests ---


def test_generate_cloze_returns_word():
    _, answer = generate_cloze("agua", gender="f")
    assert answer == "agua"


def test_generate_cloze_verb_over_noun():
    sentence, _ = generate_cloze(
        "hablar", gender=None, conjugation_group="ar",
    )
    # Verb templates don't use articles
    assert "___" in sentence


def test_generate_cloze_sentence_is_string():
    sentence, answer = generate_cloze("gato", gender="m")
    assert isinstance(sentence, str)
    assert isinstance(answer, str)


# --- Translation Cloze (English) Tests ---


def test_generate_translation_cloze_sentence_verb():
    sentence, hint = generate_translation_cloze_sentence(
        "speak", conjugation_group="ar",
    )
    assert "___" in sentence
    assert "speak" not in sentence
    assert hint == "speak"


def test_generate_translation_cloze_sentence_noun_m():
    sentence, hint = generate_translation_cloze_sentence(
        "book", gender="m",
    )
    assert "___" in sentence
    assert "book" not in sentence
    assert hint == "book"


def test_generate_translation_cloze_sentence_noun_f():
    sentence, hint = generate_translation_cloze_sentence(
        "house", gender="f",
    )
    assert "___" in sentence
    assert "house" not in sentence
    assert hint == "house"


def test_generate_translation_cloze_sentence_adjective():
    sentence, hint = generate_translation_cloze_sentence("big")
    assert "___" in sentence
    assert "big" not in sentence
    assert hint == "big"


# --- Template Count Tests ---


def test_builtin_template_counts():
    assert len(_VERB_TEMPLATES) >= 15
    assert len(_NOUN_M_TEMPLATES) >= 15


# --- load_cloze_templates Tests ---


def test_load_cloze_templates(tmp_path):
    data = {
        "verb": ["Necesitamos {word} juntos"],
        "noun_m": ["Vi el {word} ayer"],
    }
    path = tmp_path / "templates.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    before = len(_VERB_TEMPLATES)
    count = load_cloze_templates(path)
    assert count == 2
    assert len(_VERB_TEMPLATES) == before + 1
    assert "Necesitamos {word} juntos" in _VERB_TEMPLATES
    # Clean up to avoid affecting other tests
    _VERB_TEMPLATES.remove("Necesitamos {word} juntos")
    _NOUN_M_TEMPLATES.remove("Vi el {word} ayer")


def test_load_cloze_templates_unknown_key(tmp_path):
    data = {"unknown_key": ["bad {word}"]}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown template key"):
        load_cloze_templates(path)


def test_load_cloze_templates_missing_placeholder(tmp_path):
    data = {"verb": ["No placeholder here"]}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="missing.*placeholder"):
        load_cloze_templates(path)


def test_load_cloze_templates_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_cloze_templates("/nonexistent/path.json")


# --- extend_cloze_templates Tests ---


def test_extend_cloze_templates_dict():
    before = len(_VERB_TEMPLATES)
    count = extend_cloze_templates(
        {"verb": ["Debemos {word} juntos"]},
    )
    assert count == 1
    assert len(_VERB_TEMPLATES) == before + 1
    _VERB_TEMPLATES.remove("Debemos {word} juntos")


def test_extend_cloze_templates_unknown_key():
    with pytest.raises(ValueError, match="Unknown template key"):
        extend_cloze_templates({"bad_key": ["{word}"]})
