"""SM-2 spaced-repetition algorithm and word selection."""

import random
from datetime import datetime, timedelta
from typing import NamedTuple

from rembrandt.db import Database
from rembrandt.models import (
    CardState,
    ReviewConfig,
    SessionMode,
    UserProgress,
    Word,
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

    Intervals below 3 days are returned unchanged. When
    `max_fuzz_factor` is 0 or negative, no fuzz is applied.

    :param interval: Base interval in days.
    :param max_fuzz_factor: Maximum proportion of jitter
        (e.g. `0.05` means +/-5%).
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

    Routes cards through a state machine:

    - `NEW` -> `LEARNING` (or `REVIEW` if no learning steps)
    - `LEARNING` + pass -> advance step (or graduate to
      `REVIEW`)
    - `LEARNING` + fail -> reset to step 0
    - `REVIEW` + pass -> normal SM-2 interval
    - `REVIEW` + fail -> `RELEARNING` (or stay in `REVIEW`
      if no relearning steps)
    - `RELEARNING` + pass -> advance step (or return to
      `REVIEW` with reduced interval)
    - `RELEARNING` + fail -> reset to step 0

    :param progress: Current progress for a user-word pair.
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
        return progress.model_copy()

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
        word_id=progress.word_id,
        easiness_factor=round(ef, 2),
        interval=r.interval,
        repetitions=r.reps,
        next_review=r.next_review,
        state=r.state,
        step_index=r.step_index,
        lapse_count=r.lapse_count,
    )


def select_words(
    db: Database,
    user_id: int,
    language_from: str,
    language_to: str,
    count: int = 5,
    *,
    mode: SessionMode = SessionMode.MIXED,
    word_ids: list[int] | None = None,
    exclude_word_ids: set[int] | None = None,
    prioritize_weak: bool = False,
    max_new: int | None = None,
    max_review: int | None = None,
) -> list[Word]:
    """Pick words for review using spaced-repetition scheduling.

    Words in `LEARNING` or `RELEARNING` state are returned
    first (before regular due/new words) when their
    `next_review` has passed.

    :param db: The database instance.
    :param user_id: The user's database id.
    :param language_from: Source language code.
    :param language_to: Target language code.
    :param count: Number of words to select.
    :param mode: Session mode controlling which words are
        returned. `MIXED` (default) returns due words first,
        then fills with new. `LEARN_NEW` returns only new
        words. `REVIEW_DUE` returns only due words.
    :param word_ids: If provided, restrict selection to these
        word ids (e.g. from a lesson).
    :param exclude_word_ids: Word ids to exclude from
        selection (e.g. sibling burying).
    :param prioritize_weak: When `True`, sorts due words so
        that weak words (high error rate) come first.
    :param max_new: Cap on new words returned. `None` means
        no cap (unlimited).
    :param max_review: Cap on review (due) words returned.
        `None` means no cap. In-steps cards are never capped.
    :return: List of `Word` objects to review.
    """
    all_words = db.get_words(language_from, language_to)
    if not all_words:
        return []

    allowed = set(word_ids) if word_ids is not None else None
    excluded = exclude_word_ids or set()
    if allowed is not None or excluded:
        all_words = [
            w for w in all_words
            if (allowed is None or w.id in allowed)
            and w.id not in excluded
        ]
        if not all_words:
            return []

    ids = [w.id for w in all_words if w.id is not None]
    progress_map = db.get_all_progress(user_id, ids)

    now = datetime.now()
    in_steps: list[Word] = []
    due: list[Word] = []
    new: list[Word] = []

    for word in all_words:
        if word.id is None:
            raise ValueError("Word id must be set")
        progress = progress_map.get(word.id)
        if progress is None:
            new.append(word)
        elif progress.state == CardState.SUSPENDED:
            continue
        elif progress.state in (
            CardState.LEARNING,
            CardState.RELEARNING,
        ) and progress.next_review <= now:
            in_steps.append(word)
        elif progress.next_review <= now:
            due.append(word)

    if prioritize_weak and due:
        weak = db.weak_words(
            user_id, language_from, language_to,
        )
        weak_ids = {ww.word.id for ww in weak}
        due.sort(
            key=lambda w: w.id not in weak_ids,
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
