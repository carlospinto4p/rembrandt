"""Tests for rembrandt.conjugation."""

import pytest

from rembrandt.conjugation import (
    PERSONS,
    TENSES,
    can_conjugate,
    conjugate,
)


# --- Regular Conjugation Tests ---


def test_conjugate_ar_presente():
    assert conjugate("hablar", "ar", "presente", 0) == "hablo"
    assert conjugate("hablar", "ar", "presente", 1) == "hablas"
    assert conjugate("hablar", "ar", "presente", 2) == "habla"


def test_conjugate_ar_preterito():
    assert conjugate("hablar", "ar", "pretérito", 0) == "hablé"
    assert (
        conjugate("hablar", "ar", "pretérito", 2) == "habló"
    )


def test_conjugate_ar_imperfecto():
    assert (
        conjugate("hablar", "ar", "imperfecto", 0) == "hablaba"
    )
    assert (
        conjugate("hablar", "ar", "imperfecto", 3)
        == "hablábamos"
    )


def test_conjugate_er_presente():
    assert conjugate("comer", "er", "presente", 0) == "como"
    assert conjugate("comer", "er", "presente", 1) == "comes"
    assert conjugate("comer", "er", "presente", 4) == "coméis"


def test_conjugate_er_preterito():
    assert conjugate("comer", "er", "pretérito", 0) == "comí"
    assert conjugate("comer", "er", "pretérito", 2) == "comió"


def test_conjugate_er_imperfecto():
    assert (
        conjugate("comer", "er", "imperfecto", 0) == "comía"
    )


def test_conjugate_ir_presente():
    assert conjugate("vivir", "ir", "presente", 0) == "vivo"
    assert conjugate("vivir", "ir", "presente", 3) == "vivimos"


def test_conjugate_ir_preterito():
    assert conjugate("vivir", "ir", "pretérito", 0) == "viví"
    assert conjugate("vivir", "ir", "pretérito", 2) == "vivió"


def test_conjugate_ir_imperfecto():
    assert (
        conjugate("vivir", "ir", "imperfecto", 0) == "vivía"
    )


# --- Irregular Conjugation Tests ---


def test_conjugate_ser():
    assert conjugate("ser", "er", "presente", 0) == "soy"
    assert conjugate("ser", "er", "pretérito", 0) == "fui"
    assert conjugate("ser", "er", "imperfecto", 0) == "era"


def test_conjugate_ir_irregular():
    assert conjugate("ir", "ir", "presente", 0) == "voy"
    assert conjugate("ir", "ir", "pretérito", 2) == "fue"
    assert conjugate("ir", "ir", "imperfecto", 0) == "iba"


def test_conjugate_tener():
    assert conjugate("tener", "er", "presente", 0) == "tengo"
    assert conjugate("tener", "er", "pretérito", 0) == "tuve"
    assert (
        conjugate("tener", "er", "imperfecto", 0) == "tenía"
    )


def test_conjugate_hacer():
    assert conjugate("hacer", "er", "presente", 0) == "hago"
    assert conjugate("hacer", "er", "pretérito", 2) == "hizo"
    assert (
        conjugate("hacer", "er", "imperfecto", 0) == "hacía"
    )


# --- Validation Tests ---


def test_conjugate_invalid_tense():
    with pytest.raises(ValueError, match="Unknown tense"):
        conjugate("hablar", "ar", "futuro", 0)


def test_conjugate_invalid_person():
    with pytest.raises(ValueError, match="person must be 0-5"):
        conjugate("hablar", "ar", "presente", 6)


def test_conjugate_unknown_verb_returns_none():
    result = conjugate("xyz", "zz", "presente", 0)
    assert result is None


# --- can_conjugate Tests ---


def test_can_conjugate_regular():
    assert can_conjugate("hablar", "ar") is True
    assert can_conjugate("comer", "er") is True
    assert can_conjugate("vivir", "ir") is True


def test_can_conjugate_irregular():
    assert can_conjugate("ser", "er") is True
    assert can_conjugate("ir", "ir") is True


def test_can_conjugate_unknown():
    assert can_conjugate("xyz", "zz") is False


# --- Constants Tests ---


def test_persons_count():
    assert len(PERSONS) == 6
    assert PERSONS[0] == "yo"
    assert PERSONS[5] == "ellos/ellas"


def test_tenses_count():
    assert len(TENSES) == 3
    assert "presente" in TENSES
    assert "pretérito" in TENSES
    assert "imperfecto" in TENSES
