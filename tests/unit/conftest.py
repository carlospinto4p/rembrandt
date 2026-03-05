"""Shared fixtures for unit tests."""

import pytest

from rembrandt.db import Database
from rembrandt.models import Word


@pytest.fixture
def db(tmp_path):
    """Empty database for tests that don't need pre-loaded words."""
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


@pytest.fixture
def sample_words():
    """English-Spanish word pairs for exercise tests."""
    return [
        Word(
            id=i,
            language_from="en",
            language_to="es",
            word_from=w[0],
            word_to=w[1],
        )
        for i, w in enumerate(
            [
                ("cat", "gato"),
                ("dog", "perro"),
                ("house", "casa"),
                ("book", "libro"),
                ("water", "agua"),
            ],
            start=1,
        )
    ]


@pytest.fixture
def definition_words():
    """English-English definition pairs for exercise tests."""
    return [
        Word(
            id=i,
            language_from="en",
            language_to="en",
            word_from=w[0],
            word_to=w[1],
        )
        for i, w in enumerate(
            [
                (
                    "ephemeral",
                    "lasting for a very short time",
                ),
                ("ubiquitous", "present everywhere"),
                (
                    "candid",
                    "truthful and straightforward",
                ),
                (
                    "pragmatic",
                    "dealing with things practically",
                ),
                (
                    "verbose",
                    "using more words than needed",
                ),
            ],
            start=1,
        )
    ]


@pytest.fixture
def definition_db(tmp_path):
    """Database pre-loaded with EN-EN definition pairs."""
    database = Database(tmp_path / "def.db")
    database.register_user("u1", "pass")
    database.add_words([
        Word(
            language_from="en", language_to="en",
            word_from="ephemeral",
            word_to="lasting for a very short time",
        ),
        Word(
            language_from="en", language_to="en",
            word_from="ubiquitous",
            word_to="present everywhere",
        ),
        Word(
            language_from="en", language_to="en",
            word_from="candid",
            word_to="truthful and straightforward",
        ),
        Word(
            language_from="en", language_to="en",
            word_from="pragmatic",
            word_to="dealing with things practically",
        ),
        Word(
            language_from="en", language_to="en",
            word_from="verbose",
            word_to="using more words than needed",
        ),
    ])
    yield database
    database.close()


@pytest.fixture
def db_with_words(tmp_path):
    """Database pre-loaded with EN-ES word pairs and a user."""
    database = Database(tmp_path / "test.db")
    database.register_user("u1", "pass")
    database.register_user("u2", "pass")
    database.add_words([
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
        Word(
            language_from="en", language_to="es",
            word_from="book", word_to="libro",
        ),
        Word(
            language_from="en", language_to="es",
            word_from="water", word_to="agua",
        ),
    ])
    yield database
    database.close()
