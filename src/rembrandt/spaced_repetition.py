"""SM-2 spaced-repetition algorithm and word selection."""

from datetime import datetime, timedelta

from rembrandt.db import Database
from rembrandt.models import SessionMode, UserProgress, Word


def review(
    progress: UserProgress,
    quality: int,
) -> UserProgress:
    """Apply the SM-2 algorithm to update progress.

    :param progress: Current progress for a user-word pair.
    :param quality: Quality of recall, 0 (total blackout) to
        5 (perfect response).
    :return: Updated `UserProgress` with new interval,
        easiness factor, and next review date.
    :raises ValueError: If `quality` is not in 0..5.
    """
    if not 0 <= quality <= 5:
        raise ValueError(
            f"quality must be 0-5, got {quality}"
        )

    ef = progress.easiness_factor
    reps = progress.repetitions
    interval = progress.interval

    if quality >= 3:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ef)
        reps += 1
    else:
        reps = 0
        interval = 1

    ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ef = max(ef, 1.3)

    next_review = datetime.now() + timedelta(days=interval)

    return UserProgress(
        user_id=progress.user_id,
        word_id=progress.word_id,
        easiness_factor=round(ef, 2),
        interval=interval,
        repetitions=reps,
        next_review=next_review,
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
) -> list[Word]:
    """Pick words for review using spaced-repetition scheduling.

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
    due: list[Word] = []
    new: list[Word] = []

    for word in all_words:
        assert word.id is not None
        progress = progress_map.get(word.id)
        if progress is None:
            new.append(word)
        elif progress.next_review <= now:
            due.append(word)

    if mode == SessionMode.LEARN_NEW:
        return new[:count]
    if mode == SessionMode.REVIEW_DUE:
        return due[:count]

    selected = due[:count]
    remaining = count - len(selected)
    if remaining > 0:
        selected.extend(new[:remaining])

    return selected[:count]
