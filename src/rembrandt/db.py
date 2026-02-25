"""SQLite database layer for words and user progress."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from rembrandt.models import Lesson, UserProgress, Word

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS words (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    language_from     TEXT NOT NULL,
    language_to       TEXT NOT NULL,
    word_from         TEXT NOT NULL,
    word_to           TEXT NOT NULL,
    gender            TEXT,
    conjugation_group TEXT,
    tags              TEXT NOT NULL DEFAULT '[]',
    cefr              TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS progress (
    user_id          TEXT    NOT NULL,
    word_id          INTEGER NOT NULL,
    easiness_factor  REAL    NOT NULL DEFAULT 2.5,
    interval         INTEGER NOT NULL DEFAULT 0,
    repetitions      INTEGER NOT NULL DEFAULT 0,
    next_review      TEXT    NOT NULL,
    PRIMARY KEY (user_id, word_id),
    FOREIGN KEY (word_id) REFERENCES words(id)
);

CREATE TABLE IF NOT EXISTS lessons (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    language_from TEXT NOT NULL,
    language_to   TEXT NOT NULL,
    cefr          TEXT,
    tags          TEXT NOT NULL DEFAULT '[]',
    word_count    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lesson_words (
    lesson_id INTEGER NOT NULL,
    word_id   INTEGER NOT NULL,
    position  INTEGER NOT NULL,
    PRIMARY KEY (lesson_id, word_id),
    FOREIGN KEY (lesson_id) REFERENCES lessons(id),
    FOREIGN KEY (word_id)   REFERENCES words(id)
);
"""

_ISO_FMT = "%Y-%m-%dT%H:%M:%S"


def _row_to_word(r: sqlite3.Row) -> Word:
    """Convert a SQLite row to a `Word` model."""
    return Word(
        id=r["id"],
        language_from=r["language_from"],
        language_to=r["language_to"],
        word_from=r["word_from"],
        word_to=r["word_to"],
        gender=r["gender"],
        conjugation_group=r["conjugation_group"],
        tags=json.loads(r["tags"]),
        cefr=r["cefr"],
    )


def _row_to_progress(r: sqlite3.Row) -> UserProgress:
    """Convert a SQLite row to a `UserProgress` model."""
    return UserProgress(
        user_id=r["user_id"],
        word_id=r["word_id"],
        easiness_factor=r["easiness_factor"],
        interval=r["interval"],
        repetitions=r["repetitions"],
        next_review=datetime.strptime(
            r["next_review"], _ISO_FMT
        ),
    )


class Database:
    """Thin SQLite wrapper for vocabulary words and progress.

    :param path: Path to the SQLite database file.
        Use `":memory:"` for an in-memory database.
    """

    def __init__(self, path: str | Path) -> None:
        self._conn = sqlite3.connect(
            str(path),
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    # -- Words --------------------------------------------------------

    def add_word(
        self,
        language_from: str,
        language_to: str,
        word_from: str,
        word_to: str,
        *,
        gender: str | None = None,
        conjugation_group: str | None = None,
        tags: list[str] | None = None,
        cefr: str | None = None,
    ) -> Word:
        """Insert a single word and return it with its new id.

        :param language_from: Source language code.
        :param language_to: Target language code.
        :param word_from: Word in source language.
        :param word_to: Translation in target language.
        :param gender: Noun gender (`"m"` or `"f"`).
        :param conjugation_group: Verb conjugation group
            (`"ar"`, `"er"`, or `"ir"`).
        :param tags: Topic tags.
        :param cefr: CEFR level (`"A1"` through `"C2"`).
        :return: The inserted `Word` with its assigned id.
        """
        tags = tags or []
        cur = self._conn.execute(
            "INSERT INTO words "
            "(language_from, language_to, word_from, word_to,"
            " gender, conjugation_group, tags, cefr) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                language_from, language_to,
                word_from, word_to,
                gender, conjugation_group,
                json.dumps(tags),
                cefr,
            ),
        )
        self._conn.commit()
        return Word(
            id=cur.lastrowid,
            language_from=language_from,
            language_to=language_to,
            word_from=word_from,
            word_to=word_to,
            gender=gender,
            conjugation_group=conjugation_group,
            tags=tags,
            cefr=cefr,
        )

    def add_words(
        self,
        words: list[Word],
    ) -> list[Word]:
        """Bulk-insert words in a single transaction.

        :param words: List of `Word` objects to insert (the `id`
            field is ignored and assigned by the database).
        :return: List of inserted `Word` objects with assigned ids.
        """
        result: list[Word] = []
        with self._conn:
            for w in words:
                cur = self._conn.execute(
                    "INSERT INTO words "
                    "(language_from, language_to, "
                    "word_from, word_to, "
                    "gender, conjugation_group, tags, cefr) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        w.language_from, w.language_to,
                        w.word_from, w.word_to,
                        w.gender, w.conjugation_group,
                        json.dumps(w.tags),
                        w.cefr,
                    ),
                )
                result.append(
                    w.model_copy(update={"id": cur.lastrowid})
                )
        return result

    def get_words(
        self,
        language_from: str,
        language_to: str,
    ) -> list[Word]:
        """Return all words for a language pair.

        :param language_from: Source language code.
        :param language_to: Target language code.
        :return: List of matching `Word` objects.
        """
        rows = self._conn.execute(
            "SELECT id, language_from, language_to, "
            "word_from, word_to, "
            "gender, conjugation_group, tags, cefr "
            "FROM words "
            "WHERE language_from = ? AND language_to = ?",
            (language_from, language_to),
        ).fetchall()
        return [_row_to_word(r) for r in rows]

    # -- Progress -----------------------------------------------------

    def get_progress(
        self,
        user_id: str,
        word_id: int,
    ) -> UserProgress | None:
        """Fetch progress for a user-word pair.

        :param user_id: The user identifier.
        :param word_id: The word identifier.
        :return: `UserProgress` or `None` if no record exists.
        """
        row = self._conn.execute(
            "SELECT * FROM progress "
            "WHERE user_id = ? AND word_id = ?",
            (user_id, word_id),
        ).fetchone()
        if row is None:
            return None
        return _row_to_progress(row)

    def get_all_progress(
        self,
        user_id: str,
        word_ids: list[int],
    ) -> dict[int, UserProgress]:
        """Fetch progress for multiple words in a single query.

        :param user_id: The user identifier.
        :param word_ids: List of word identifiers.
        :return: Dict mapping `word_id` to `UserProgress` for
            words that have a progress record.
        """
        if not word_ids:
            return {}
        placeholders = ",".join("?" for _ in word_ids)
        rows = self._conn.execute(
            "SELECT * FROM progress "
            f"WHERE user_id = ? AND word_id IN ({placeholders})",
            [user_id, *word_ids],
        ).fetchall()
        return {
            row["word_id"]: _row_to_progress(row)
            for row in rows
        }

    def upsert_progress(self, progress: UserProgress) -> None:
        """Insert or update progress for a user-word pair.

        :param progress: The `UserProgress` to persist.
        """
        self._conn.execute(
            "INSERT INTO progress "
            "(user_id, word_id, easiness_factor, "
            " interval, repetitions, next_review) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, word_id) DO UPDATE SET "
            " easiness_factor = excluded.easiness_factor, "
            " interval         = excluded.interval, "
            " repetitions      = excluded.repetitions, "
            " next_review      = excluded.next_review",
            (
                progress.user_id,
                progress.word_id,
                progress.easiness_factor,
                progress.interval,
                progress.repetitions,
                progress.next_review.strftime(_ISO_FMT),
            ),
        )
        self._conn.commit()

    # -- Lessons ------------------------------------------------------

    def add_lesson(self, lesson: Lesson) -> Lesson:
        """Insert a lesson and link its words.

        :param lesson: The `Lesson` to insert. The `word_ids` list
            links the lesson to existing words in the database.
        :return: The inserted `Lesson` with its assigned id.
        """
        return self.add_lessons([lesson])[0]

    def add_lessons(
        self, lessons: list[Lesson],
    ) -> list[Lesson]:
        """Bulk-insert lessons in a single transaction.

        :param lessons: List of `Lesson` objects to insert.
        :return: List of inserted `Lesson` objects with assigned
            ids.
        """
        result: list[Lesson] = []
        with self._conn:
            for lesson in lessons:
                cur = self._conn.execute(
                    "INSERT INTO lessons "
                    "(title, description, language_from,"
                    " language_to, cefr, tags, word_count) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        lesson.title,
                        lesson.description,
                        lesson.language_from,
                        lesson.language_to,
                        lesson.cefr,
                        json.dumps(lesson.tags),
                        lesson.word_count,
                    ),
                )
                lesson_id = cur.lastrowid
                for pos, wid in enumerate(lesson.word_ids):
                    self._conn.execute(
                        "INSERT INTO lesson_words "
                        "(lesson_id, word_id, position) "
                        "VALUES (?, ?, ?)",
                        (lesson_id, wid, pos),
                    )
                result.append(
                    lesson.model_copy(
                        update={"id": lesson_id}
                    )
                )
        return result

    def get_lessons(
        self,
        language_from: str,
        language_to: str,
        *,
        cefr: str | None = None,
        tag: str | None = None,
    ) -> list[Lesson]:
        """Return lessons for a language pair with optional filters.

        :param language_from: Source language code.
        :param language_to: Target language code.
        :param cefr: Filter by CEFR level.
        :param tag: Filter by topic tag.
        :return: List of matching `Lesson` objects with `word_ids`
            populated.
        """
        clauses = [
            "language_from = ?",
            "language_to = ?",
        ]
        params: list[str] = [language_from, language_to]
        if cefr is not None:
            clauses.append("cefr = ?")
            params.append(cefr)
        if tag is not None:
            clauses.append(
                "EXISTS (SELECT 1 FROM json_each(tags) "
                "WHERE json_each.value = ?)"
            )
            params.append(tag)
        where = " AND ".join(clauses)
        rows = self._conn.execute(
            "SELECT id, title, description, language_from,"
            " language_to, cefr, tags, word_count "
            f"FROM lessons WHERE {where} "
            "ORDER BY id",
            params,
        ).fetchall()
        if not rows:
            return []
        lesson_ids = [r["id"] for r in rows]
        placeholders = ",".join("?" for _ in lesson_ids)
        lw_rows = self._conn.execute(
            "SELECT lesson_id, word_id FROM lesson_words "
            f"WHERE lesson_id IN ({placeholders}) "
            "ORDER BY position",
            lesson_ids,
        ).fetchall()
        word_map: dict[int, list[int]] = {}
        for lw in lw_rows:
            word_map.setdefault(
                lw["lesson_id"], []
            ).append(lw["word_id"])
        return [
            Lesson(
                id=r["id"],
                title=r["title"],
                description=r["description"],
                language_from=r["language_from"],
                language_to=r["language_to"],
                cefr=r["cefr"],
                tags=json.loads(r["tags"]),
                word_count=r["word_count"],
                word_ids=word_map.get(r["id"], []),
            )
            for r in rows
        ]

    def get_lesson(self, lesson_id: int) -> Lesson | None:
        """Fetch a single lesson by id.

        :param lesson_id: The lesson identifier.
        :return: `Lesson` with `word_ids` populated, or `None`
            if not found.
        """
        row = self._conn.execute(
            "SELECT id, title, description, language_from,"
            " language_to, cefr, tags, word_count "
            "FROM lessons WHERE id = ?",
            (lesson_id,),
        ).fetchone()
        if row is None:
            return None
        word_rows = self._conn.execute(
            "SELECT word_id FROM lesson_words "
            "WHERE lesson_id = ? ORDER BY position",
            (lesson_id,),
        ).fetchall()
        return Lesson(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            language_from=row["language_from"],
            language_to=row["language_to"],
            cefr=row["cefr"],
            tags=json.loads(row["tags"]),
            word_count=row["word_count"],
            word_ids=[r["word_id"] for r in word_rows],
        )

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
