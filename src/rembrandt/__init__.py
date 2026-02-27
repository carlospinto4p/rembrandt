"""rembrandt - Mental exercises with the help of LLMs."""

from importlib.metadata import version

from rembrandt.db import Database
from rembrandt.lessons import lesson_progress, load_lessons
from rembrandt.models import (
    AnswerHistory,
    DailyStats,
    Hint,
    Lesson,
    SessionMode,
    SessionStats,
    User,
    UserSession,
    WeakWord,
    Word,
)
from rembrandt.sentences import load_cloze_templates
from rembrandt.session import Session, quick_session

__version__ = version("rembrandt")

__all__ = [
    "AnswerHistory",
    "DailyStats",
    "Database",
    "Hint",
    "Lesson",
    "Session",
    "SessionMode",
    "SessionStats",
    "User",
    "UserSession",
    "WeakWord",
    "Word",
    "lesson_progress",
    "load_cloze_templates",
    "load_lessons",
    "quick_session",
]
