"""SM-2 spaced-repetition algorithm and word selection."""

import random
from datetime import datetime, timedelta

from rembrandt.db import Database
from rembrandt.models import (
    CardState,
    ReviewConfig,
    SessionMode,
    UserProgress,
    Word,
)

_DEFAULT_CONFIG = ReviewConfig()


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

    old_ef = progress.easiness_factor
    state = progress.state
    step_index = progress.step_index
    interval = progress.interval
    reps = progress.repetitions
    lapse_count = progress.lapse_count
    passed = quality >= 3

    if state == CardState.NEW:
        if passed:
            if config.learning_steps:
                state = CardState.LEARNING
                step_index = 0
                next_review = datetime.now() + timedelta(
                    minutes=config.learning_steps[0],
                )
            else:
                state = CardState.REVIEW
                step_index = 0
                interval = _fuzz_interval(
                    config.graduating_interval,
                    config.max_fuzz_factor,
                )
                reps = 1
                next_review = datetime.now() + timedelta(
                    days=interval,
                )
        else:
            if config.learning_steps:
                state = CardState.LEARNING
                step_index = 0
                next_review = datetime.now() + timedelta(
                    minutes=config.learning_steps[0],
                )
            else:
                state = CardState.NEW
                step_index = 0
                next_review = datetime.now() + timedelta(
                    minutes=1,
                )

    elif state == CardState.LEARNING:
        if passed:
            next_step = step_index + 1
            if next_step < len(config.learning_steps):
                step_index = next_step
                next_review = datetime.now() + timedelta(
                    minutes=config.learning_steps[
                        next_step
                    ],
                )
            else:
                state = CardState.REVIEW
                step_index = 0
                interval = _fuzz_interval(
                    config.graduating_interval,
                    config.max_fuzz_factor,
                )
                reps = 1
                next_review = datetime.now() + timedelta(
                    days=interval,
                )
        else:
            step_index = 0
            next_review = datetime.now() + timedelta(
                minutes=config.learning_steps[0],
            )

    elif state == CardState.REVIEW:
        if passed:
            if reps == 0:
                interval = 1
            elif reps == 1:
                interval = _fuzz_interval(
                    6, config.max_fuzz_factor,
                )
            else:
                interval = _fuzz_interval(
                    round(interval * old_ef),
                    config.max_fuzz_factor,
                )
            reps += 1
            next_review = datetime.now() + timedelta(
                days=interval,
            )
        else:
            reps = 0
            lapse_count += 1
            if (
                config.leech_threshold > 0
                and lapse_count >= config.leech_threshold
            ):
                state = CardState.SUSPENDED
                next_review = progress.next_review
            elif config.relearning_steps:
                state = CardState.RELEARNING
                step_index = 0
                next_review = datetime.now() + timedelta(
                    minutes=config.relearning_steps[0],
                )
            else:
                new_interval = _fuzz_interval(
                    max(
                        round(
                            interval
                            * config.lapse_new_interval_factor
                        ),
                        config.lapse_min_interval,
                    ),
                    config.max_fuzz_factor,
                )
                interval = new_interval
                next_review = datetime.now() + timedelta(
                    days=interval,
                )

    elif state == CardState.RELEARNING:
        if passed:
            next_step = step_index + 1
            if next_step < len(config.relearning_steps):
                step_index = next_step
                next_review = datetime.now() + timedelta(
                    minutes=config.relearning_steps[
                        next_step
                    ],
                )
            else:
                state = CardState.REVIEW
                step_index = 0
                new_interval = _fuzz_interval(
                    max(
                        round(
                            interval
                            * config.lapse_new_interval_factor
                        ),
                        config.lapse_min_interval,
                    ),
                    config.max_fuzz_factor,
                )
                interval = new_interval
                reps = 1
                next_review = datetime.now() + timedelta(
                    days=interval,
                )
        else:
            step_index = 0
            next_review = datetime.now() + timedelta(
                minutes=config.relearning_steps[0],
            )

    ef = _update_ef(old_ef, quality)

    return UserProgress(
        user_id=progress.user_id,
        word_id=progress.word_id,
        easiness_factor=round(ef, 2),
        interval=interval,
        repetitions=reps,
        next_review=next_review,
        state=state,
        step_index=step_index,
        lapse_count=lapse_count,
    )


def select_words(
    db: Database,
    user_id: str,
    language_from: str,
    language_to: str,
    count: int = 5,
    *,
    mode: SessionMode = SessionMode.MIXED,
    word_ids: list[int] | None = None,
    prioritize_weak: bool = False,
) -> list[Word]:
    """Pick words for review using spaced-repetition scheduling.

    Words in `LEARNING` or `RELEARNING` state are returned
    first (before regular due/new words) when their
    `next_review` has passed.

    :param db: The database instance.
    :param user_id: The user identifier.
    :param language_from: Source language code.
    :param language_to: Target language code.
    :param count: Number of words to select.
    :param mode: Session mode controlling which words are
        returned. `MIXED` (default) returns due words first,
        then fills with new. `LEARN_NEW` returns only new
        words. `REVIEW_DUE` returns only due words.
    :param word_ids: If provided, restrict selection to these
        word ids (e.g. from a lesson).
    :param prioritize_weak: When `True`, sorts due words so
        that weak words (high error rate) come first.
    :return: List of `Word` objects to review.
    """
    all_words = db.get_words(language_from, language_to)
    if not all_words:
        return []

    if word_ids is not None:
        allowed = set(word_ids)
        all_words = [
            w for w in all_words if w.id in allowed
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
