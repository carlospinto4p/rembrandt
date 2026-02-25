"""Tests for rembrandt.sentences."""

from rembrandt.sentences import generate_cloze, generate_translation_cloze_sentence


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
