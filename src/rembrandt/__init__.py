"""rembrandt - Mental exercises with the help of LLMs."""

from importlib.metadata import version

from rembrandt.db import Database, import_words_csv
from rembrandt.db_postgres import PostgresDatabase
from rembrandt.lessons import lesson_progress, load_lessons
from rembrandt.fsrs import fsrs_review
from rembrandt.models import (
    AnswerHistory,
    CardState,
    DailyStats,
    FSRSConfig,
    Hint,
    Lesson,
    ReviewConfig,
    ReviewForecast,
    SessionMode,
    SessionStats,
    User,
    UserSession,
    WeakWord,
    Word,
)
from rembrandt.exercises import load_exercise_config
from rembrandt.sentences import load_cloze_templates
from rembrandt.session import Session, quick_session

__version__ = version("rembrandt")

__all__ = [
    "AnswerHistory",
    "CardState",
    "DailyStats",
    "Database",
    "FSRSConfig",
    "Hint",
    "fsrs_review",
    "PostgresDatabase",
    "Lesson",
    "ReviewConfig",
    "ReviewForecast",
    "Session",
    "SessionMode",
    "SessionStats",
    "User",
    "UserSession",
    "WeakWord",
    "Word",
    "import_words_csv",
    "lesson_progress",
    "load_cloze_templates",
    "load_exercise_config",
    "load_lessons",
    "quick_session",
]
