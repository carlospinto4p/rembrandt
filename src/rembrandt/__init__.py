"""rembrandt - Mental exercises with the help of LLMs."""

from importlib.metadata import version

from rembrandt.db import Database
from rembrandt.lessons import lesson_progress, load_lessons
from rembrandt.models import Lesson, SessionMode, User, Word
from rembrandt.session import Session, quick_session

__version__ = version("rembrandt")

__all__ = [
    "Database",
    "Lesson",
    "Session",
    "SessionMode",
    "User",
    "Word",
    "lesson_progress",
    "load_lessons",
    "quick_session",
]
