"""Tests for scripts.topic_classifier."""

import sys
from pathlib import Path

# Allow importing from scripts/.
sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent.parent / "scripts"),
)

from topic_classifier import classify  # noqa: E402


# --- classify Tests ---


def test_classify_food():
    assert classify("a piece of bread") == ["food"]


def test_classify_no_match():
    assert classify("to be or not to be") == []


def test_classify_multi_topic():
    tags = classify("drink water at the hotel")
    assert "food" in tags
    assert "travel" in tags


def test_classify_body():
    assert classify("relating to the hand") == ["body"]


def test_classify_emotions():
    assert classify("to feel happy") == ["emotions"]


def test_classify_family():
    assert classify("the mother of the child") == ["family"]


def test_classify_case_insensitive():
    assert classify("A PIECE OF BREAD") == ["food"]


def test_classify_empty_string():
    assert classify("") == []
