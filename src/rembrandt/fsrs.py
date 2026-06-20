"""FSRS-5 spaced-repetition algorithm.

Implements the Free Spaced Repetition Scheduler (FSRS-5) as an
alternative to SM-2. Uses 19 optimizable parameters with a
power-law forgetting curve.

See https://github.com/open-spaced-repetition/fsrs4anki/wiki
"""

import math
from datetime import datetime, timedelta

from rembrandt.models import (
    CardState,
    FSRSConfig,
    UserProgress,
)

# FSRS-5 fixed constants
DECAY = -0.5
FACTOR = 19.0 / 81.0  # 0.9^(1/DECAY) - 1

# FSRS grade constants
AGAIN = 1
HARD = 2
GOOD = 3
EASY = 4


def retrievability(
    elapsed_days: float,
    stability: float,
) -> float:
    """Compute recall probability after `elapsed_days`.

    :param elapsed_days: Days since last review.
    :param stability: Current stability in days.
    :return: Probability of recall (0.0-1.0).
    """
    if stability <= 0:
        return 0.0
    return (1 + FACTOR * elapsed_days / stability) ** DECAY


def _interval(
    stability: float,
    desired_retention: float,
    max_interval: int,
) -> int:
    """Compute optimal interval from stability and retention.

    :param stability: Current stability in days.
    :param desired_retention: Target recall probability.
    :param max_interval: Maximum allowed interval.
    :return: Interval in days (>= 1).
    """
    if desired_retention <= 0 or desired_retention >= 1:
        return max_interval
    iv = stability / FACTOR * (desired_retention ** (1 / DECAY) - 1)
    return max(1, min(round(iv), max_interval))


def _init_stability(
    grade: int,
    w: tuple[float, ...],
) -> float:
    """Initial stability for a first review.

    :param grade: FSRS grade (1-4).
    :param w: FSRS weights.
    :return: Initial stability in days.
    """
    return max(0.001, w[grade - 1])


def _init_difficulty(
    grade: int,
    w: tuple[float, ...],
) -> float:
    """Initial difficulty for a first review.

    :param grade: FSRS grade (1-4).
    :param w: FSRS weights.
    :return: Difficulty (1.0-10.0).
    """
    d = w[4] - math.exp(w[5] * (grade - 1)) + 1
    return max(1.0, min(10.0, d))


def _next_difficulty(
    d: float,
    grade: int,
    w: tuple[float, ...],
) -> float:
    """Update difficulty after a review.

    :param d: Current difficulty.
    :param grade: FSRS grade (1-4).
    :param w: FSRS weights.
    :return: Updated difficulty (1.0-10.0).
    """
    delta = -w[6] * (grade - 3)
    d_prime = d + delta * (10 - d) / 9
    d_mean = w[7] * _init_difficulty(4, w)
    result = d_mean + (1 - w[7]) * d_prime
    return max(1.0, min(10.0, result))


def _next_stability_success(
    d: float,
    s: float,
    r: float,
    grade: int,
    w: tuple[float, ...],
) -> float:
    """Stability after a successful recall (Hard/Good/Easy).

    :param d: Current difficulty.
    :param s: Current stability.
    :param r: Retrievability at review time.
    :param grade: FSRS grade (2, 3, or 4).
    :param w: FSRS weights.
    :return: New stability in days.
    """
    hard_penalty = w[15] if grade == HARD else 1.0
    easy_bonus = w[16] if grade == EASY else 1.0
    new_s = s * (
        1
        + math.exp(w[8])
        * (11 - d)
        * s ** (-w[9])
        * (math.exp(w[10] * (1 - r)) - 1)
        * hard_penalty
        * easy_bonus
    )
    return max(0.001, new_s)


def _next_stability_fail(
    d: float,
    s: float,
    r: float,
    w: tuple[float, ...],
) -> float:
    """Stability after a lapse (Again).

    :param d: Current difficulty.
    :param s: Current stability.
    :param r: Retrievability at review time.
    :param w: FSRS weights.
    :return: New stability in days.
    """
    long_term = (
        w[11]
        * d ** (-w[12])
        * ((s + 1) ** w[13] - 1)
        * math.exp(w[14] * (1 - r))
    )
    short_cap = s / math.exp(w[17] * w[18])
    return max(0.001, min(long_term, short_cap))


def _quality_to_grade(quality: int) -> int:
    """Map SM-2 quality (0-5) to FSRS grade (1-4).

    :param quality: SM-2 quality score.
    :return: FSRS grade.
    """
    if quality <= 2:
        return AGAIN
    if quality == 3:
        return HARD
    if quality == 4:
        return GOOD
    return EASY


def fsrs_review(
    progress: UserProgress,
    quality: int,
    *,
    config: FSRSConfig | None = None,
) -> UserProgress:
    """Update progress using the FSRS-5 algorithm.

    :param progress: Current user-concept progress.
    :param quality: SM-2 quality score (0-5), mapped to FSRS
        grades internally (0-2 → Again, 3 → Hard, 4 → Good,
        5 → Easy).
    :param config: FSRS configuration. Uses defaults when
        `None`.
    :return: Updated `UserProgress` with new scheduling.
    """
    if progress.state == CardState.SUSPENDED:
        return progress

    if config is None:
        config = FSRSConfig()
    w = config.weights
    grade = _quality_to_grade(quality)

    updated = progress.model_copy()
    now = datetime.now()

    # --- NEW state ---
    if progress.state == CardState.NEW:
        updated.stability = _init_stability(grade, w)
        updated.difficulty = _init_difficulty(grade, w)

        if grade == AGAIN:
            updated.state = CardState.LEARNING
            updated.step_index = 0
            if config.learning_steps:
                mins = config.learning_steps[0]
                updated.next_review = now + timedelta(minutes=mins)
            else:
                updated.next_review = now + timedelta(
                    days=_interval(
                        updated.stability,
                        config.desired_retention,
                        config.max_interval,
                    )
                )
                updated.state = CardState.REVIEW
        elif grade == HARD:
            updated.state = CardState.LEARNING
            updated.step_index = 0
            if config.learning_steps:
                mins = config.learning_steps[0]
                updated.next_review = now + timedelta(minutes=mins)
            else:
                updated.state = CardState.REVIEW
                updated.next_review = now + timedelta(
                    days=_interval(
                        updated.stability,
                        config.desired_retention,
                        config.max_interval,
                    )
                )
        elif grade == GOOD:
            if config.learning_steps:
                updated.state = CardState.LEARNING
                updated.step_index = 0
                if len(config.learning_steps) == 1:
                    # Graduate immediately
                    updated.state = CardState.REVIEW
                    updated.next_review = now + timedelta(
                        days=_interval(
                            updated.stability,
                            config.desired_retention,
                            config.max_interval,
                        )
                    )
                else:
                    mins = config.learning_steps[1]
                    updated.step_index = 1
                    updated.next_review = now + timedelta(minutes=mins)
            else:
                updated.state = CardState.REVIEW
                updated.next_review = now + timedelta(
                    days=_interval(
                        updated.stability,
                        config.desired_retention,
                        config.max_interval,
                    )
                )
        else:  # EASY
            updated.state = CardState.REVIEW
            updated.next_review = now + timedelta(
                days=_interval(
                    updated.stability,
                    config.desired_retention,
                    config.max_interval,
                )
            )
        return updated

    # --- LEARNING / RELEARNING state ---
    if progress.state in (
        CardState.LEARNING,
        CardState.RELEARNING,
    ):
        is_relearning = progress.state == CardState.RELEARNING
        steps = (
            config.relearning_steps
            if is_relearning
            else config.learning_steps
        )

        if grade == AGAIN:
            updated.step_index = 0
            if steps:
                updated.next_review = now + timedelta(minutes=steps[0])
            else:
                updated.state = CardState.REVIEW
                updated.next_review = now + timedelta(
                    days=_interval(
                        updated.stability or 1.0,
                        config.desired_retention,
                        config.max_interval,
                    )
                )
        elif grade in (GOOD, EASY) or (
            grade == HARD and progress.step_index + 1 >= len(steps)
        ):
            # Graduate
            next_step = progress.step_index + 1
            if grade == EASY or next_step >= len(steps):
                updated.state = CardState.REVIEW
                s = updated.stability or 1.0
                updated.next_review = now + timedelta(
                    days=_interval(
                        s,
                        config.desired_retention,
                        config.max_interval,
                    )
                )
            else:
                updated.step_index = next_step
                updated.next_review = now + timedelta(
                    minutes=steps[next_step]
                )
        else:
            # HARD: stay at current step
            if steps and progress.step_index < len(steps):
                mins = steps[progress.step_index]
                updated.next_review = now + timedelta(minutes=mins)
        return updated

    # --- REVIEW state ---
    elapsed = (now - progress.next_review).total_seconds() / 86400.0
    elapsed = max(
        0.0, elapsed + (progress.interval if progress.interval else 1)
    )

    s = progress.stability or 1.0
    d = progress.difficulty or 5.0
    r = retrievability(elapsed, s)

    updated.difficulty = _next_difficulty(d, grade, w)

    if grade == AGAIN:
        updated.stability = _next_stability_fail(
            d,
            s,
            r,
            w,
        )
        updated.lapse_count = progress.lapse_count + 1
        if config.relearning_steps:
            updated.state = CardState.RELEARNING
            updated.step_index = 0
            updated.next_review = now + timedelta(
                minutes=config.relearning_steps[0],
            )
        else:
            iv = _interval(
                updated.stability,
                config.desired_retention,
                config.max_interval,
            )
            updated.interval = iv
            updated.next_review = now + timedelta(days=iv)
    else:
        updated.stability = _next_stability_success(
            d,
            s,
            r,
            grade,
            w,
        )
        iv = _interval(
            updated.stability,
            config.desired_retention,
            config.max_interval,
        )
        updated.interval = iv
        updated.next_review = now + timedelta(days=iv)

    return updated
