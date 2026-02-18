"""Chat session for vocabulary exercises."""

from __future__ import annotations

from rembrandt.db import Database
from rembrandt.exercises import (
    evaluate_answer,
    generate_exercise,
)
from rembrandt.models import AnswerResult, Exercise
from rembrandt.spaced_repetition import review, select_words


class Session:
    """Main entry point for vocabulary exercise sessions.

    :param db: The database instance.
    :param user_id: Identifier for the user.
    :param language_from: Source language code.
    :param language_to: Target language code.
    """

    def __init__(
        self,
        db: Database,
        user_id: str,
        language_from: str,
        language_to: str,
    ) -> None:
        self.db = db
        self.user_id = user_id
        self.language_from = language_from
        self.language_to = language_to
        self._current_exercise: Exercise | None = None

    def next_exercise(self) -> Exercise | None:
        """Select a word and generate an exercise.

        :return: An `Exercise`, or ``None`` if no words are
            available.
        """
        words = select_words(
            self.db,
            self.user_id,
            self.language_from,
            self.language_to,
            count=1,
        )
        if not words:
            return None

        word = words[0]
        all_words = self.db.get_words(
            self.language_from, self.language_to
        )
        exercise = generate_exercise(word, all_words)
        self._current_exercise = exercise
        return exercise

    def answer(self, text: str) -> AnswerResult:
        """Evaluate the user's answer and update progress.

        :param text: The user's answer text.
        :return: An `AnswerResult`.
        :raises RuntimeError: If no exercise is active.
        """
        if self._current_exercise is None:
            raise RuntimeError(
                "No active exercise. Call next_exercise() first."
            )

        result = evaluate_answer(self._current_exercise, text)

        quality = 5 if result.correct else 1
        word_id = result.word.id
        progress = self.db.get_progress(
            self.user_id, word_id  # type: ignore[arg-type]
        )
        if progress is None:
            from rembrandt.models import UserProgress

            progress = UserProgress(
                user_id=self.user_id,
                word_id=word_id,  # type: ignore[arg-type]
            )

        updated = review(progress, quality)
        self.db.upsert_progress(updated)

        self._current_exercise = None
        return result
