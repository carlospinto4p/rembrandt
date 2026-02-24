"""Lesson loader — resolves word ranks to database ids."""

import json
import logging
from pathlib import Path

from rembrandt.db import Database
from rembrandt.models import Lesson, LessonProgress

logger = logging.getLogger(__name__)


def load_lessons(
    lessons_path: str | Path,
    vocab_path: str | Path,
    db: Database,
    *,
    language_from: str,
    language_to: str,
) -> list[Lesson]:
    """Load lessons from JSON, resolving word ranks to DB ids.

    Each lesson entry must have a `word_ranks` list of integer
    ranks that correspond to entries in the vocabulary file.
    Ranks that cannot be resolved (missing from vocab or DB)
    are skipped with a warning.

    :param lessons_path: Path to the lessons JSON file.
    :param vocab_path: Path to the vocabulary JSON file
        (same format as `spanish_top10000.json`).
    :param db: An open `Database` with words already loaded.
    :param language_from: Source language code.
    :param language_to: Target language code.
    :return: List of `Lesson` objects with `word_ids` populated
        and persisted in the database.
    """
    with open(lessons_path, encoding="utf-8") as f:
        raw_lessons = json.load(f)
    with open(vocab_path, encoding="utf-8") as f:
        vocab = json.load(f)

    rank_to_key: dict[int, tuple[str, str]] = {}
    for entry in vocab:
        rank_to_key[entry["rank"]] = (
            entry["definition"],
            entry["word"],
        )

    db_words = db.get_words(language_from, language_to)
    key_to_id: dict[tuple[str, str], int] = {}
    for w in db_words:
        key_to_id[(w.word_from, w.word_to)] = w.id  # type: ignore[assignment]

    lessons: list[Lesson] = []
    for entry in raw_lessons:
        word_ids: list[int] = []
        for rank in entry.get("word_ranks", []):
            key = rank_to_key.get(rank)
            if key is None:
                logger.warning(
                    "Rank %d not found in vocab file, "
                    "skipping",
                    rank,
                )
                continue
            wid = key_to_id.get(key)
            if wid is None:
                logger.warning(
                    "Word %s (rank %d) not found in DB, "
                    "skipping",
                    key,
                    rank,
                )
                continue
            word_ids.append(wid)
        lessons.append(Lesson(
            title=entry["title"],
            description=entry.get("description", ""),
            language_from=entry["language_from"],
            language_to=entry["language_to"],
            cefr=entry.get("cefr"),
            tags=entry.get("tags", []),
            word_count=len(word_ids),
            word_ids=word_ids,
        ))
    return db.add_lessons(lessons)


def lesson_progress(
    db: Database,
    user_id: str,
    lesson: Lesson,
) -> LessonProgress:
    """Compute progress statistics for a user in a lesson.

    :param db: The database instance.
    :param user_id: The user identifier.
    :param lesson: The lesson to check progress for.
    :return: A `LessonProgress` with completion and mastery
        statistics.
    """
    total = len(lesson.word_ids)
    if total == 0:
        return LessonProgress(
            lesson_id=lesson.id or 0,
            user_id=user_id,
            words_total=0,
            words_studied=0,
            words_mastered=0,
            completion_pct=0.0,
            mastery_pct=0.0,
        )

    progress_map = db.get_all_progress(
        user_id, lesson.word_ids,
    )

    studied = len(progress_map)
    mastered = sum(
        1 for p in progress_map.values()
        if p.repetitions >= 3
    )

    return LessonProgress(
        lesson_id=lesson.id or 0,
        user_id=user_id,
        words_total=total,
        words_studied=studied,
        words_mastered=mastered,
        completion_pct=round(studied / total * 100, 1),
        mastery_pct=round(mastered / total * 100, 1),
    )
