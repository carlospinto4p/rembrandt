"""SQLite database layer for words and user progress."""

import sqlite3
from datetime import datetime
from pathlib import Path

from rembrandt.models import UserProgress, Word

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS words (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    language_from     TEXT NOT NULL,
    language_to       TEXT NOT NULL,
    word_from         TEXT NOT NULL,
    word_to           TEXT NOT NULL,
    gender            TEXT,
    conjugation_group TEXT,
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
"""

_ISO_FMT = "%Y-%m-%dT%H:%M:%S"


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
    ) -> Word:
        """Insert a single word and return it with its new id.

        :param language_from: Source language code.
        :param language_to: Target language code.
        :param word_from: Word in source language.
        :param word_to: Translation in target language.
        :param gender: Noun gender (`"m"` or `"f"`).
        :param conjugation_group: Verb conjugation group
            (`"ar"`, `"er"`, or `"ir"`).
        :return: The inserted `Word` with its assigned id.
        """
        cur = self._conn.execute(
            "INSERT INTO words "
            "(language_from, language_to, word_from, word_to,"
            " gender, conjugation_group) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                language_from, language_to,
                word_from, word_to,
                gender, conjugation_group,
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
                    "gender, conjugation_group) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        w.language_from, w.language_to,
                        w.word_from, w.word_to,
                        w.gender, w.conjugation_group,
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
            "gender, conjugation_group "
            "FROM words "
            "WHERE language_from = ? AND language_to = ?",
            (language_from, language_to),
        ).fetchall()
        return [
            Word(
                id=r["id"],
                language_from=r["language_from"],
                language_to=r["language_to"],
                word_from=r["word_from"],
                word_to=r["word_to"],
                gender=r["gender"],
                conjugation_group=r["conjugation_group"],
            )
            for r in rows
        ]

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
        return UserProgress(
            user_id=row["user_id"],
            word_id=row["word_id"],
            easiness_factor=row["easiness_factor"],
            interval=row["interval"],
            repetitions=row["repetitions"],
            next_review=datetime.strptime(
                row["next_review"], _ISO_FMT
            ),
        )

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
            row["word_id"]: UserProgress(
                user_id=row["user_id"],
                word_id=row["word_id"],
                easiness_factor=row["easiness_factor"],
                interval=row["interval"],
                repetitions=row["repetitions"],
                next_review=datetime.strptime(
                    row["next_review"], _ISO_FMT
                ),
            )
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

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
