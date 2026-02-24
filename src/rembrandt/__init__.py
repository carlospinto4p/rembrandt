"""rembrandt - Mental exercises with the help of LLMs."""

from importlib.metadata import version

from rembrandt.conjugation import can_conjugate, conjugate
from rembrandt.db import Database
from rembrandt.lessons import lesson_progress, load_lessons
from rembrandt.models import (
    AnswerResult,
    Exercise,
    ExerciseType,
    LearningMode,
    Lesson,
    LessonProgress,
    SessionMode,
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
    "LessonProgress",
    "Session",
    "SessionMode",
    "Word",
    "can_conjugate",
    "conjugate",
    "learning_mode",
    "lesson_progress",
    "load_lessons",
    "quick_session",
]
