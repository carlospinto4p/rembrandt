"""SM-2 spaced-repetition algorithm and concept selection."""

import random
from datetime import datetime, timedelta
from typing import NamedTuple

from rembrandt.db import Database
from rembrandt.models import (
    CardState,
    Concept,
    ReviewConfig,
    SessionMode,
    UserProgress,
)

_DEFAULT_CONFIG = ReviewConfig()

# SM-2 scheduling constants
QUALITY_PASS_THRESHOLD = 3
_FIRST_CORRECT_INTERVAL = 1
_SECOND_CORRECT_INTERVAL = 6


def _update_ef(ef: float, quality: int) -> float:
    """Apply the SM-2 easiness-factor adjustment.

    :param ef: Current easiness factor.
    :param quality: Quality score 0-5.
    :return: Updated easiness factor (>= 1.3).
    """
    ef = ef + (
        0.1
        - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    )
    return max(ef, 1.3)


def _fuzz_interval(
    interval: int, max_fuzz_factor: float,
) -> int:
    """Add random jitter to a day-based interval.

    :param interval: Base interval in days.
    :param max_fuzz_factor: Maximum proportion of jitter.
    :return: Fuzzed interval (always >= 1).
    """
    if interval < 3 or max_fuzz_factor <= 0:
        return interval
    fuzz_days = max(1, round(interval * max_fuzz_factor))
    return max(
        1,
        random.randint(
            interval - fuzz_days, interval + fuzz_days,
        ),
    )


def _schedule(
    *, minutes: int = 0, days: int = 0,
) -> datetime:
    """Calculate a next-review datetime from now.

    :param minutes: Minutes from now.
    :param days: Days from now.
    :return: Scheduled datetime.
    """
    return datetime.now() + timedelta(
        minutes=minutes, days=days,
    )


class _ReviewResult(NamedTuple):
    """Intermediate result from a state handler."""

    state: CardState
    step_index: int
    interval: int
    reps: int
    lapse_count: int
    next_review: datetime


def _handle_new(
    progress: UserProgress,
    passed: bool,
    config: ReviewConfig,
) -> _ReviewResult:
    """Handle NEW -> LEARNING or REVIEW transition."""
    if config.learning_steps:
        return _ReviewResult(
            state=CardState.LEARNING,
            step_index=0,
            interval=progress.interval,
            reps=progress.repetitions,
            lapse_count=progress.lapse_count,
            next_review=_schedule(
                minutes=config.learning_steps[0],
            ),
        )
    if passed:
        interval = _fuzz_interval(
            config.graduating_interval,
            config.max_fuzz_factor,
        )
        return _ReviewResult(
            state=CardState.REVIEW,
            step_index=0,
            interval=interval,
            reps=1,
            lapse_count=progress.lapse_count,
            next_review=_schedule(days=interval),
        )
    return _ReviewResult(
        state=CardState.NEW,
        step_index=0,
        interval=progress.interval,
        reps=progress.repetitions,
        lapse_count=progress.lapse_count,
        next_review=_schedule(minutes=1),
    )


def _handle_learning(
    progress: UserProgress,
    passed: bool,
    config: ReviewConfig,
) -> _ReviewResult:
    """Handle LEARNING step advancement or graduation."""
    if not passed:
        return _ReviewResult(
            state=CardState.LEARNING,
            step_index=0,
            interval=progress.interval,
            reps=progress.repetitions,
            lapse_count=progress.lapse_count,
            next_review=_schedule(
                minutes=config.learning_steps[0],
            ),
        )
    next_step = progress.step_index + 1
    if next_step < len(config.learning_steps):
        return _ReviewResult(
            state=CardState.LEARNING,
            step_index=next_step,
            interval=progress.interval,
            reps=progress.repetitions,
            lapse_count=progress.lapse_count,
            next_review=_schedule(
                minutes=config.learning_steps[
                    next_step
                ],
            ),
        )
    interval = _fuzz_interval(
        config.graduating_interval,
        config.max_fuzz_factor,
    )
    return _ReviewResult(
        state=CardState.REVIEW,
        step_index=0,
        interval=interval,
        reps=1,
        lapse_count=progress.lapse_count,
        next_review=_schedule(days=interval),
    )


def _handle_review(
    progress: UserProgress,
    passed: bool,
    config: ReviewConfig,
) -> _ReviewResult:
    """Handle REVIEW pass (SM-2) or fail (lapse)."""
    if passed:
        reps = progress.repetitions
        if reps == 0:
            interval = _FIRST_CORRECT_INTERVAL
        elif reps == 1:
            interval = _fuzz_interval(
                _SECOND_CORRECT_INTERVAL,
                config.max_fuzz_factor,
            )
        else:
            interval = _fuzz_interval(
                round(
                    progress.interval
                    * progress.easiness_factor
                ),
                config.max_fuzz_factor,
            )
        return _ReviewResult(
            state=CardState.REVIEW,
            step_index=progress.step_index,
            interval=interval,
            reps=reps + 1,
            lapse_count=progress.lapse_count,
            next_review=_schedule(days=interval),
        )
    lapse_count = progress.lapse_count + 1
    if (
        config.leech_threshold > 0
        and lapse_count >= config.leech_threshold
    ):
        return _ReviewResult(
            state=CardState.SUSPENDED,
            step_index=progress.step_index,
            interval=progress.interval,
            reps=0,
            lapse_count=lapse_count,
            next_review=progress.next_review,
        )
    if config.relearning_steps:
        return _ReviewResult(
            state=CardState.RELEARNING,
            step_index=0,
            interval=progress.interval,
            reps=0,
            lapse_count=lapse_count,
            next_review=_schedule(
                minutes=config.relearning_steps[0],
            ),
        )
    interval = _fuzz_interval(
        max(
            round(
                progress.interval
                * config.lapse_new_interval_factor
            ),
            config.lapse_min_interval,
        ),
        config.max_fuzz_factor,
    )
    return _ReviewResult(
        state=CardState.REVIEW,
        step_index=progress.step_index,
        interval=interval,
        reps=0,
        lapse_count=lapse_count,
        next_review=_schedule(days=interval),
    )


def _handle_relearning(
    progress: UserProgress,
    passed: bool,
    config: ReviewConfig,
) -> _ReviewResult:
    """Handle RELEARNING step advancement or return."""
    if not passed:
        return _ReviewResult(
            state=CardState.RELEARNING,
            step_index=0,
            interval=progress.interval,
            reps=progress.repetitions,
            lapse_count=progress.lapse_count,
            next_review=_schedule(
                minutes=config.relearning_steps[0],
            ),
        )
    next_step = progress.step_index + 1
    if next_step < len(config.relearning_steps):
        return _ReviewResult(
            state=CardState.RELEARNING,
            step_index=next_step,
            interval=progress.interval,
            reps=progress.repetitions,
            lapse_count=progress.lapse_count,
            next_review=_schedule(
                minutes=config.relearning_steps[
                    next_step
                ],
            ),
        )
    interval = _fuzz_interval(
        max(
            round(
                progress.interval
                * config.lapse_new_interval_factor
            ),
            config.lapse_min_interval,
        ),
        config.max_fuzz_factor,
    )
    return _ReviewResult(
        state=CardState.REVIEW,
        step_index=0,
        interval=interval,
        reps=1,
        lapse_count=progress.lapse_count,
        next_review=_schedule(days=interval),
    )


def review(
    progress: UserProgress,
    quality: int,
    *,
    config: ReviewConfig | None = None,
) -> UserProgress:
    """Apply spaced-repetition with Anki-style learning steps.

    :param progress: Current progress for a user-concept pair.
    :param quality: Quality of recall, 0 (total blackout) to
        5 (perfect response).
    :param config: Learning/relearning configuration. Uses
        default `ReviewConfig` when `None`.
    :return: Updated `UserProgress` with new interval,
        easiness factor, and next review date.
    :raises ValueError: If `quality` is not in 0..5.
    """
    if not 0 <= quality <= 5:
        raise ValueError(
            f"quality must be 0-5, got {quality}"
        )

    if progress.state == CardState.SUSPENDED:
        return progress

    if config is None:
        config = _DEFAULT_CONFIG

    passed = quality >= QUALITY_PASS_THRESHOLD
    state = progress.state

    if state == CardState.NEW:
        r = _handle_new(progress, passed, config)
    elif state == CardState.LEARNING:
        r = _handle_learning(progress, passed, config)
    elif state == CardState.REVIEW:
        r = _handle_review(progress, passed, config)
    else:
        r = _handle_relearning(progress, passed, config)

    ef = _update_ef(progress.easiness_factor, quality)

    return UserProgress(
        user_id=progress.user_id,
        concept_id=progress.concept_id,
        easiness_factor=round(ef, 2),
        interval=r.interval,
        repetitions=r.reps,
        next_review=r.next_review,
        state=r.state,
        step_index=r.step_index,
        lapse_count=r.lapse_count,
    )


async def select_concepts(
    db: Database,
    user_id: int,
    count: int = 5,
    *,
    mode: SessionMode = SessionMode.MIXED,
    tag: str | None = None,
    concept_ids: list[int] | None = None,
    exclude_concept_ids: set[int] | None = None,
    prioritize_weak: bool = False,
    max_new: int | None = None,
    max_review: int | None = None,
) -> list[Concept]:
    """Pick concepts for review using spaced-repetition.

    :param db: The database instance.
    :param user_id: The user's database id.
    :param count: Number of concepts to select.
    :param mode: Session mode controlling which concepts are
        returned.
    :param tag: Optional tag filter.
    :param concept_ids: Restrict selection to these ids.
    :param exclude_concept_ids: Concept ids to exclude.
    :param prioritize_weak: Sort due concepts by error rate.
    :param max_new: Cap on new concepts returned.
    :param max_review: Cap on review concepts returned.
    :return: List of `Concept` objects to review.
    """
    all_concepts = await db.get_concepts(tag=tag)
    if not all_concepts:
        return []

    allowed = (
        set(concept_ids)
        if concept_ids is not None else None
    )
    excluded = exclude_concept_ids or set()
    if allowed is not None or excluded:
        all_concepts = [
            c for c in all_concepts
            if (allowed is None or c.id in allowed)
            and c.id not in excluded
        ]
        if not all_concepts:
            return []

    ids = [
        c.id for c in all_concepts
        if c.id is not None
    ]
    progress_map = await db.get_all_progress(
        user_id, ids,
    )

    now = datetime.now()
    in_steps: list[Concept] = []
    due: list[Concept] = []
    new: list[Concept] = []

    for concept in all_concepts:
        if concept.id is None:
            raise ValueError("Concept id must be set")
        progress = progress_map.get(concept.id)
        if progress is None:
            new.append(concept)
        elif progress.state == CardState.SUSPENDED:
            continue
        elif progress.state in (
            CardState.LEARNING,
            CardState.RELEARNING,
        ) and progress.next_review <= now:
            in_steps.append(concept)
        elif progress.next_review <= now:
            due.append(concept)

    if prioritize_weak and due:
        weak = await db.weak_concepts(
            user_id, tag=tag,
        )
        weak_ids = {wc.concept.id for wc in weak}
        due.sort(
            key=lambda c: c.id not in weak_ids,
        )

    if max_new is not None:
        new = new[:max_new]
    if max_review is not None:
        due = due[:max_review]

    if mode == SessionMode.LEARN_NEW:
        return (in_steps + new)[:count]
    if mode == SessionMode.REVIEW_DUE:
        return (in_steps + due)[:count]

    selected = in_steps + due
    selected = selected[:count]
    remaining = count - len(selected)
    if remaining > 0:
        selected.extend(new[:remaining])

    return selected[:count]
