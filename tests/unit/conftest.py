"""Shared fixtures for unit tests."""

import pytest

from rembrandt.db import Database


@pytest.fixture
def db(tmp_path):
    """Empty database for tests that don't need pre-loaded words."""
    database = Database(tmp_path / "test.db")
    yield database
    database.close()
