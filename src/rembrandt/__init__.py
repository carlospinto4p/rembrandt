"""rembrandt - A general-purpose spaced-repetition library."""

from importlib.metadata import version

from rembrandt.db import Database, import_concepts_csv
from rembrandt.db_postgres import PostgresDatabase
from rembrandt.topics import load_topics, topic_progress
from rembrandt.fsrs import fsrs_review
from rembrandt.models import (
    AnswerHistory,
    CardState,
    Concept,
    ConversationStage,
    ConversationState,
    DailyStats,
    ExerciseType,
    FSRSConfig,
    Hint,
    ReviewConfig,
    ReviewForecast,
    SessionMode,
    SessionSnapshot,
    SessionStats,
    Topic,
    TopicProgress,
    User,
    UserSession,
    WeakConcept,
)
from rembrandt.session import Session, quick_session

__version__ = version("rembrandt")

__all__ = [
    "AnswerHistory",
    "CardState",
    "Concept",
    "ConversationStage",
    "ConversationState",
    "DailyStats",
    "Database",
    "ExerciseType",
    "FSRSConfig",
    "Hint",
    "PostgresDatabase",
    "ReviewConfig",
    "ReviewForecast",
    "Session",
    "SessionMode",
    "SessionSnapshot",
    "SessionStats",
    "Topic",
    "TopicProgress",
    "User",
    "UserSession",
    "WeakConcept",
    "fsrs_review",
    "import_concepts_csv",
    "load_topics",
    "quick_session",
    "topic_progress",
]
