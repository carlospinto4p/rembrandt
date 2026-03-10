"""Chat session for vocabulary exercises."""

import json
from pathlib import Path

from rembrandt.db import Database
from rembrandt.exercises import (
    _spanish_word,
    evaluate_answer,
    generate_exercise,
)
from rembrandt.fsrs import fsrs_review
from rembrandt.models import (
    AnswerResult,
    CardState,
    Exercise,
    ExerciseType,
    FSRSConfig,
    Hint,
    LearningMode,
    ReviewConfig,
    SessionMode,
    SessionStats,
    UserProgress,
    Word,
    learning_mode,
)
from rembrandt.sentences import generate_cloze
from rembrandt.spaced_repetition import review, select_words


class Session:
    """Main entry point for vocabulary exercise sessions.

    :param db: The database instance.
    :param user_id: The user's database id.
    :param language_from: Source language code.
    :param language_to: Target language code.
    :param mode: Session mode (`MIXED`, `LEARN_NEW`, or
        `REVIEW_DUE`).
    :param word_ids: Restrict exercises to these word ids
        (e.g. from a `Lesson`).
    :param review_config: Anki-style learning/relearning
        step configuration. Uses default `ReviewConfig`
        when `None`.
    :param fsrs_config: FSRS algorithm configuration.
        When provided, the session uses FSRS instead of SM-2.
        Mutually exclusive with `review_config`.
    """

    def __init__(
        self,
        db: Database,
        user_id: int,
        language_from: str,
        language_to: str,
        *,
        mode: SessionMode = SessionMode.MIXED,
        word_ids: list[int] | None = None,
        review_config: ReviewConfig | None = None,
        fsrs_config: FSRSConfig | None = None,
    ) -> None:
        self.db = db
        self.user_id = user_id
        self.language_from = language_from
        self.language_to = language_to
        self.mode = mode
        self._word_ids = word_ids
        self._review_config = review_config
        self._fsrs_config = fsrs_config
        self._current_exercise: Exercise | None = None
        self._hint_count = 0
        self._buried_word_ids: set[int] = set()
        self._correct = 0
        self._incorrect = 0
        self._streak = 0
        self._best_streak = 0
        self._new_served = 0
        self._review_served = 0
        self._all_words: list[Word] | None = None

    async def next_exercise(self) -> Exercise | None:
        """Select a word and generate an exercise.

        :return: An `Exercise`, or `None` if no words are
            available.
        """
        cfg = self._review_config
        max_new: int | None = None
        max_review: int | None = None

        if cfg is not None and cfg.max_new_cards > 0:
            remaining = cfg.max_new_cards - self._new_served
            max_new = max(remaining, 0)
        if cfg is not None and cfg.max_review_cards > 0:
            remaining = (
                cfg.max_review_cards - self._review_served
            )
            max_review = max(remaining, 0)

        words = await select_words(
            self.db,
            self.user_id,
            self.language_from,
            self.language_to,
            count=1,
            mode=self.mode,
            word_ids=self._word_ids,
            exclude_word_ids=self._buried_word_ids or None,
            max_new=max_new,
            max_review=max_review,
        )
        if not words:
            return None

        word = words[0]
        if word.id is not None:
            self._buried_word_ids.add(word.id)
        await self._track_served(word)
        if self._all_words is None:
            self._all_words = await self.db.get_words(
                self.language_from, self.language_to,
            )
        exercise = generate_exercise(word, self._all_words)
        self._current_exercise = exercise
        self._hint_count = 0
        return exercise

    async def _track_served(self, word: Word) -> None:
        """Increment new/review served counters.

        :param word: The word about to be served.
        """
        progress = await self.db.get_progress(
            self.user_id, word.id,
        )
        if progress is None:
            self._new_served += 1
        elif progress.state in (
            CardState.LEARNING,
            CardState.RELEARNING,
        ):
            pass  # in-steps — don't count
        else:
            self._review_served += 1

    async def answer(
        self,
        text: str = "",
        quality: int | None = None,
    ) -> AnswerResult:
        """Evaluate the user's answer and update progress.

        :param text: The user's answer text (ignored for
            self-graded exercises).
        :param quality: Self-assessment score 0-5 (required for
            `SELF_GRADED` exercises). When provided, this value
            is passed directly to the SM-2 algorithm instead of
            the default binary 5/1.
        :return: An `AnswerResult`.
        :raises RuntimeError: If no exercise is active.
        """
        if self._current_exercise is None:
            raise RuntimeError(
                "No active exercise. "
                "Call next_exercise() first."
            )

        result = evaluate_answer(
            self._current_exercise, text, quality=quality,
        )

        if quality is not None:
            sm2_quality = quality
        else:
            sm2_quality = 5 if result.correct else 1
        word_id = result.word.id
        if word_id is None:
            raise ValueError("Word id must be set")
        progress = await self.db.get_progress(
            self.user_id, word_id
        )
        if progress is None:
            progress = UserProgress(
                user_id=self.user_id,
                word_id=word_id,
            )

        if self._fsrs_config is not None:
            updated = fsrs_review(
                progress, sm2_quality,
                config=self._fsrs_config,
            )
        else:
            updated = review(
                progress, sm2_quality,
                config=self._review_config,
            )
        await self.db.upsert_progress(updated)

        await self.db.record_answer(
            self.user_id,
            word_id,
            self._current_exercise.exercise_type.value,
            result.correct,
            sm2_quality,
        )

        self._update_stats(result.correct)
        self._current_exercise = None
        return result

    def _update_stats(self, correct: bool) -> None:
        """Update session counters after an answer.

        :param correct: Whether the answer was correct.
        """
        if correct:
            self._correct += 1
            self._streak += 1
            if self._streak > self._best_streak:
                self._best_streak = self._streak
        else:
            self._incorrect += 1
            self._streak = 0

    def skip(self) -> Exercise:
        """Skip the current exercise without affecting progress.

        :return: The skipped `Exercise`.
        :raises RuntimeError: If no exercise is active.
        """
        if self._current_exercise is None:
            raise RuntimeError(
                "No active exercise. "
                "Call next_exercise() first."
            )
        skipped = self._current_exercise
        self._current_exercise = None
        return skipped

    def hint(self) -> Hint:
        """Return a progressive hint for the current exercise.

        Each successive call reveals one more letter of the
        expected answer (e.g. `"g___"` → `"ga__"` → `"gat_"`).
        When the word has gender or a conjugation group, the
        first call also includes an example sentence with a
        blank.

        :return: A `Hint`.
        :raises RuntimeError: If no exercise is active.
        """
        if self._current_exercise is None:
            raise RuntimeError(
                "No active exercise. "
                "Call next_exercise() first."
            )
        ex = self._current_exercise
        if ex.expected_answer:
            answer = ex.expected_answer
        elif (
            ex.exercise_type
            == ExerciseType.REVERSE_FLASHCARD
        ):
            answer = ex.word.word_from
        else:
            answer = ex.word.word_to

        self._hint_count += 1
        reveal = min(self._hint_count, len(answer))

        first = answer[0] if answer else ""
        length = len(answer)
        pattern = (
            answer[:reveal] + "_" * (length - reveal)
            if length else ""
        )

        example = ""
        if (
            learning_mode(ex.word)
            == LearningMode.TRANSLATION
            and (
                ex.word.gender is not None
                or ex.word.conjugation_group is not None
            )
        ):
            spanish = _spanish_word(ex.word)
            sentence, _ = generate_cloze(
                spanish,
                gender=ex.word.gender,
                conjugation_group=(
                    ex.word.conjugation_group
                ),
            )
            example = sentence

        return Hint(
            first_letter=first,
            word_length=length,
            pattern=pattern,
            reveal_count=reveal,
            example_sentence=example,
        )

    def summary(self) -> SessionStats:
        """Return statistics for the current session.

        :return: A `SessionStats` snapshot.
        """
        total = self._correct + self._incorrect
        pct = (
            self._correct / total * 100.0 if total else 0.0
        )
        return SessionStats(
            total=total,
            correct=self._correct,
            incorrect=self._incorrect,
            streak=self._streak,
            best_streak=self._best_streak,
            accuracy_pct=round(pct, 1),
        )


async def quick_session(
    vocab: str | Path | list[dict[str, str]],
    *,
    db_path: str | Path | None = None,
    language_from: str,
    language_to: str,
    user_id: int | None = None,
    limit: int | None = None,
    word_from_key: str = "word",
    word_to_key: str = "definition",
    review_config: ReviewConfig | None = None,
) -> Session:
    """Create a `Session` from a JSON file or inline word list.

    Handles database creation, conditional word loading (only on
    first run), and session setup in a single call.

    :param vocab: Path to a JSON file or a list of dicts with
        word/definition pairs.
    :param db_path: SQLite file path. If `None`, derived from
        `vocab` filename (same directory, `.db` extension).
        Required when `vocab` is a list.
    :param language_from: Source language code.
    :param language_to: Target language code.
    :param user_id: The user's database id. When `None`,
        auto-registers a `"default"` user and uses its id.
    :param limit: Maximum number of words to load. `None` loads
        all.
    :param word_from_key: Key in each dict for `word_from`.
    :param word_to_key: Key in each dict for `word_to`.
    :param review_config: Anki-style learning/relearning
        step configuration. Uses default `ReviewConfig`
        when `None`.
    :return: A ready-to-use `Session`.
    :raises ValueError: If `vocab` is a list and `db_path` is
        `None`.
    """
    if isinstance(vocab, list):
        if db_path is None:
            raise ValueError(
                "db_path is required when vocab is a list"
            )
        entries = vocab
    else:
        vocab = Path(vocab)
        if db_path is None:
            db_path = vocab.with_suffix(".db")

    db_path = Path(db_path)
    fresh = not db_path.exists()
    db = await Database.connect(db_path)

    if user_id is None:
        user = await db.get_user("default")
        if user is None:
            user = await db.register_user(
                "default", "default",
            )
        user_id = user.id

    if fresh:
        if not isinstance(vocab, list):
            with open(vocab, encoding="utf-8") as fh:
                entries = json.load(fh)
        words = [
            Word(
                language_from=language_from,
                language_to=language_to,
                word_from=e[word_from_key],
                word_to=e[word_to_key],
                gender=e.get("gender"),
                conjugation_group=e.get(
                    "conjugation_group"
                ),
                tags=e.get("tags", []),
                cefr=e.get("cefr"),
            )
            for e in entries[:limit]
        ]
        await db.add_words(words)

    return Session(
        db, user_id, language_from, language_to,
        review_config=review_config,
    )
