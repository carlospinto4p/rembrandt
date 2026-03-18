"""Topic loader and progress calculation."""

import json
import logging
from pathlib import Path

from rembrandt.db import Database
from rembrandt.models import CardState, Topic, TopicProgress

logger = logging.getLogger(__name__)

# Minimum SM-2 repetitions to consider a concept mastered
MASTERY_REPETITIONS = 3


async def load_topics(
    path: str | Path,
    db: Database,
) -> list[Topic]:
    """Load topics from a JSON file.

    Each entry must have `title`, `description`, and
    `concept_ids` (list of database concept ids).

    :param path: Path to the topics JSON file.
    :param db: An open `Database` with concepts already
        loaded.
    :return: List of `Topic` objects persisted in the
        database.
    """
    with open(path, encoding="utf-8") as f:
        raw_topics = json.load(f)

    topics: list[Topic] = []
    for entry in raw_topics:
        concept_ids = entry.get("concept_ids", [])
        topics.append(Topic(
            title=entry["title"],
            description=entry.get("description", ""),
            tags=entry.get("tags", []),
            concept_count=len(concept_ids),
            concept_ids=concept_ids,
        ))
    return await db.add_topics(topics)


async def topic_progress(
    db: Database,
    user_id: int,
    topic: Topic,
) -> TopicProgress:
    """Compute progress statistics for a user in a topic.

    :param db: The database instance.
    :param user_id: The user's database id.
    :param topic: The topic to check progress for.
    :return: A `TopicProgress` with completion and mastery
        statistics.
    """
    total = len(topic.concept_ids)
    if total == 0:
        return TopicProgress(
            topic_id=topic.id or 0,
            user_id=user_id,
            concepts_total=0,
            concepts_studied=0,
            concepts_mastered=0,
            completion_pct=0.0,
            mastery_pct=0.0,
        )

    progress_map = await db.get_all_progress(
        user_id, topic.concept_ids,
    )

    studied = len(progress_map)
    mastered = sum(
        1 for p in progress_map.values()
        if p.state == CardState.REVIEW
        and p.repetitions >= MASTERY_REPETITIONS
    )

    return TopicProgress(
        topic_id=topic.id or 0,
        user_id=user_id,
        concepts_total=total,
        concepts_studied=studied,
        concepts_mastered=mastered,
        completion_pct=round(studied / total * 100, 1),
        mastery_pct=round(mastered / total * 100, 1),
    )
