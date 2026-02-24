"""rembrandt - Mental exercises with the help of LLMs."""

from importlib.metadata import version

from rembrandt.db import Database
from rembrandt.lessons import load_lessons
from rembrandt.models import (
    AnswerResult,
    Exercise,
    ExerciseType,
    LearningMode,
    Lesson,
    Word,
    learning_mode,
)
from rembrandt.session import Session, quick_session

__version__ = version("rembrandt")

__all__ = [
    "AnswerResult",
    "Database",
    "Exercise",
    "ExerciseType",
    "LearningMode",
    "Lesson",
    "Session",
    "Word",
    "learning_mode",
    "load_lessons",
    "quick_session",
]
