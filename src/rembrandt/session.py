"""Chat session for spaced-repetition exercises."""

import json
from pathlib import Path

from rembrandt.db import Database
from rembrandt.exercises import (
    evaluate_answer,
    generate_exercise,
)
from rembrandt.fsrs import fsrs_review
from rembrandt.models import (
    AnswerResult,
    CardState,
    Concept,
    Exercise,
    FSRSConfig,
    Hint,
    ReviewConfig,
    SessionMode,
    SessionSnapshot,
    SessionStats,
    UserProgress,
)
from rembrandt.spaced_repetition import (
    review,
    select_concepts,
)


class Session:
    """Main entry point for exercise sessions.

    :param db: The database instance.
    :param user_id: The user's database id.
    :param mode: Session mode (`MIXED`, `LEARN_NEW`, or
        `REVIEW_DUE`).
    :param tags: Optional tag filter (concepts matching any
        of these tags).
    :param concept_ids: Restrict exercises to these concept
        ids (e.g. from a `Topic`).
    :param review_config: Anki-style learning/relearning
        step configuration. Uses default `ReviewConfig`
        when `None`.
    :param fsrs_config: FSRS algorithm configuration.
        When provided, the session uses FSRS instead of SM-2.
    """

    def __init__(
        self,
        db: Database,
        user_id: int,
        *,
        mode: SessionMode = SessionMode.MIXED,
        tags: list[str] | None = None,
        concept_ids: list[int] | None = None,
        review_config: ReviewConfig | None = None,
        fsrs_config: FSRSConfig | None = None,
    ) -> None:
        self.db = db
        self.user_id = user_id
        self.mode = mode
        self._tags = tags
        self._concept_ids = concept_ids
        self._review_config = review_config
        self._fsrs_config = fsrs_config
        self._current_exercise: Exercise | None = None
        self._hint_count = 0
        self._buried_concept_ids: set[int] = set()
        self._correct = 0
        self._incorrect = 0
        self._streak = 0
        self._best_streak = 0
        self._new_served = 0
        self._review_served = 0
        self._all_concepts: list[Concept] | None = None
        self._topic_concepts: list[Concept] | None = None

    async def next_exercise(self) -> Exercise | None:
        """Select a concept and generate an exercise.

        :return: An `Exercise`, or `None` if no concepts
            are available.
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

        tag = self._tags[0] if self._tags else None
        concepts = await select_concepts(
            self.db,
            self.user_id,
            count=1,
            mode=self.mode,
            tag=tag,
            concept_ids=self._concept_ids,
            exclude_concept_ids=(
                self._buried_concept_ids or None
            ),
            max_new=max_new,
            max_review=max_review,
        )
        if not concepts:
            return None

        concept = concepts[0]
        if concept.id is not None:
            self._buried_concept_ids.add(concept.id)
        await self._track_served(concept)
        if self._all_concepts is None:
            self._all_concepts = (
                await self.db.get_concepts(tag=tag)
            )
        if (
            self._topic_concepts is None
            and self._concept_ids
        ):
            id_set = set(self._concept_ids)
            self._topic_concepts = [
                c for c in self._all_concepts
                if c.id in id_set
            ]
        exercise = generate_exercise(
            concept, self._all_concepts,
            preferred=self._topic_concepts,
        )
        self._current_exercise = exercise
        self._hint_count = 0
        return exercise

    async def _track_served(
        self, concept: Concept,
    ) -> None:
        """Increment new/review served counters.

        :param concept: The concept about to be served.
        """
        progress = await self.db.get_progress(
            self.user_id, concept.id,
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
        :param quality: Self-assessment score 0-5 (required
            for `SELF_GRADED` exercises).
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
        concept_id = result.concept.id
        if concept_id is None:
            raise ValueError("Concept id must be set")
        progress = await self.db.get_progress(
            self.user_id, concept_id
        )
        if progress is None:
            progress = UserProgress(
                user_id=self.user_id,
                concept_id=concept_id,
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
            concept_id,
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
        expected answer (e.g. `"g___"` → `"ga__"` →
        `"gat_"`). When the concept has a non-empty `context`
        field, the first call also includes it.

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
        else:
            answer = ex.concept.back

        self._hint_count += 1
        reveal = min(self._hint_count, len(answer))

        first = answer[0] if answer else ""
        length = len(answer)
        pattern = (
            answer[:reveal] + "_" * (length - reveal)
            if length else ""
        )

        context = ex.concept.context or ""

        return Hint(
            first_letter=first,
            word_length=length,
            pattern=pattern,
            reveal_count=reveal,
            context=context,
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

    def snapshot(self) -> SessionSnapshot:
        """Create a serializable snapshot of this session.

        :return: A `SessionSnapshot` capturing all in-memory
            state.
        """
        return SessionSnapshot(
            user_id=self.user_id,
            mode=self.mode,
            tags=self._tags,
            concept_ids=self._concept_ids,
            review_config=self._review_config,
            fsrs_config=self._fsrs_config,
            current_exercise=self._current_exercise,
            hint_count=self._hint_count,
            buried_concept_ids=sorted(
                self._buried_concept_ids,
            ),
            correct=self._correct,
            incorrect=self._incorrect,
            streak=self._streak,
            best_streak=self._best_streak,
            new_served=self._new_served,
            review_served=self._review_served,
        )

    async def save(self, key: str = "") -> None:
        """Save this session's state to the database.

        :param key: Optional key to distinguish multiple
            sessions per user (e.g. a chat id).
        """
        await self.db.save_session_snapshot(
            self.snapshot(), key=key,
        )

    @classmethod
    async def restore(
        cls,
        db: "Database",
        user_id: int,
        key: str = "",
    ) -> "Session | None":
        """Restore a session from a saved snapshot.

        :param db: The database instance.
        :param user_id: The user's database id.
        :param key: Optional key matching the one used
            when saving.
        :return: A restored `Session`, or `None` if no
            snapshot exists.
        """
        snap = await db.get_session_snapshot(
            user_id, key=key,
        )
        if snap is None:
            return None
        session = cls(
            db,
            snap.user_id,
            mode=snap.mode,
            tags=snap.tags,
            concept_ids=snap.concept_ids,
            review_config=snap.review_config,
            fsrs_config=snap.fsrs_config,
        )
        session._current_exercise = snap.current_exercise
        session._hint_count = snap.hint_count
        session._buried_concept_ids = set(
            snap.buried_concept_ids,
        )
        session._correct = snap.correct
        session._incorrect = snap.incorrect
        session._streak = snap.streak
        session._best_streak = snap.best_streak
        session._new_served = snap.new_served
        session._review_served = snap.review_served
        return session


async def quick_session(
    vocab: str | Path | list[dict[str, str]],
    *,
    db_path: str | Path | None = None,
    user_id: int | None = None,
    limit: int | None = None,
    front_key: str = "front",
    back_key: str = "back",
    review_config: ReviewConfig | None = None,
) -> Session:
    """Create a `Session` from a JSON file or inline list.

    Handles database creation, conditional concept loading
    (only on first run), and session setup in a single call.

    :param vocab: Path to a JSON file or a list of dicts with
        front/back pairs.
    :param db_path: SQLite file path. If `None`, derived from
        `vocab` filename (same directory, `.db` extension).
        Required when `vocab` is a list.
    :param user_id: The user's database id. When `None`,
        auto-registers a `"default"` user and uses its id.
    :param limit: Maximum number of concepts to load.
    :param front_key: Key in each dict for `front`.
    :param back_key: Key in each dict for `back`.
    :param review_config: Anki-style learning/relearning
        step configuration.
    :return: A ready-to-use `Session`.
    :raises ValueError: If `vocab` is a list and `db_path`
        is `None`.
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
        concepts = [
            Concept(
                front=e[front_key],
                back=e[back_key],
                context=e.get("context", ""),
                tags=e.get("tags", []),
            )
            for e in entries[:limit]
        ]
        await db.add_concepts(concepts)

    return Session(
        db, user_id,
        review_config=review_config,
    )
