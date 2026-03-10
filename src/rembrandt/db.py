"""Async SQLite database layer for words and user progress."""

import csv
import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite

from rembrandt.models import (
    AnswerHistory,
    CardState,
    DailyStats,
    Lesson,
    ReviewForecast,
    SessionSnapshot,
    User,
    UserProgress,
    UserSession,
    WeakWord,
    Word,
)

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    display_name  TEXT,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    token      TEXT    NOT NULL UNIQUE,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

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
    owner_id          INTEGER,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS progress (
    user_id          INTEGER NOT NULL,
    word_id          INTEGER NOT NULL,
    easiness_factor  REAL    NOT NULL DEFAULT 2.5,
    interval         INTEGER NOT NULL DEFAULT 0,
    repetitions      INTEGER NOT NULL DEFAULT 0,
    next_review      TEXT    NOT NULL,
    state            TEXT    NOT NULL DEFAULT 'new',
    step_index       INTEGER NOT NULL DEFAULT 0,
    lapse_count      INTEGER NOT NULL DEFAULT 0,
    stability        REAL,
    difficulty       REAL,
    PRIMARY KEY (user_id, word_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
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
    word_count    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS lesson_words (
    lesson_id INTEGER NOT NULL,
    word_id   INTEGER NOT NULL,
    position  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (lesson_id, word_id),
    FOREIGN KEY (lesson_id) REFERENCES lessons(id),
    FOREIGN KEY (word_id) REFERENCES words(id)
);

CREATE TABLE IF NOT EXISTS answer_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    word_id       INTEGER NOT NULL,
    exercise_type TEXT    NOT NULL,
    correct       INTEGER NOT NULL,
    quality       INTEGER NOT NULL,
    answered_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (word_id) REFERENCES words(id)
);

CREATE TABLE IF NOT EXISTS session_snapshots (
    user_id   INTEGER NOT NULL,
    key       TEXT    NOT NULL DEFAULT '',
    data      TEXT    NOT NULL,
    saved_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, key),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

_ISO_FMT = "%Y-%m-%dT%H:%M:%S"

_DAILY_STATS_SQL = (
    "SELECT date(answered_at) AS day, "
    "COUNT(*) AS answers, "
    "SUM(correct) AS correct "
    "FROM answer_history "
    "WHERE user_id = ? "
    "AND answered_at >= ? "
    "GROUP BY day "
    "ORDER BY day DESC"
)

_WEAK_WORDS_SQL = (
    "SELECT w.id, w.language_from, "
    "w.language_to, w.word_from, w.word_to, "
    "w.gender, w.conjugation_group, "
    "w.tags, w.cefr, w.owner_id, "
    "COUNT(*) AS attempts, "
    "SUM(CASE WHEN ah.correct = 0 "
    "    THEN 1 ELSE 0 END) AS errors, "
    "MAX(ah.answered_at) AS last_attempt "
    "FROM answer_history ah "
    "JOIN words w ON w.id = ah.word_id "
    "WHERE ah.user_id = ? "
    "AND w.language_from = ? "
    "AND w.language_to = ? "
    "GROUP BY ah.word_id "
    "HAVING attempts >= ? "
    "AND CAST(errors AS REAL) "
    "    / attempts >= ? "
    "ORDER BY CAST(errors AS REAL) "
    "    / attempts DESC "
    "LIMIT ?"
)


def _in_clause(ids: list) -> str:
    """Build a SQL IN-clause placeholder string.

    :param ids: List of values (length determines count).
    :return: Comma-separated `?` placeholders,
        e.g. `"?,?,?"`.
    """
    return ",".join("?" for _ in ids)


def _hash_password(password: str) -> str:
    """Hash a password with a random salt using SHA-256."""
    salt = os.urandom(16).hex()
    h = hashlib.sha256(
        f"{salt}{password}".encode(),
    ).hexdigest()
    return f"{salt}${h}"


def _verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored salt$hash string."""
    salt, expected = stored.split("$", 1)
    h = hashlib.sha256(
        f"{salt}{password}".encode(),
    ).hexdigest()
    return h == expected


def _row_to_user(r: aiosqlite.Row) -> User:
    """Convert a SQLite row to a `User` model."""
    return User(
        id=r["id"],
        username=r["username"],
        display_name=r["display_name"],
        password_hash=r["password_hash"],
        created_at=datetime.fromisoformat(
            r["created_at"],
        ),
    )


def _row_to_user_session(
    r: aiosqlite.Row,
) -> UserSession:
    """Convert a SQLite row to a `UserSession` model."""
    return UserSession(
        id=r["id"],
        user_id=r["user_id"],
        token=r["token"],
        created_at=datetime.fromisoformat(
            r["created_at"],
        ),
        expires_at=datetime.fromisoformat(
            r["expires_at"],
        ),
    )


def _row_to_word(r: aiosqlite.Row) -> Word:
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
        owner_id=r["owner_id"],
    )


def _row_to_progress(r: aiosqlite.Row) -> UserProgress:
    """Convert a SQLite row to a `UserProgress` model."""
    return UserProgress(
        user_id=r["user_id"],
        word_id=r["word_id"],
        easiness_factor=r["easiness_factor"],
        interval=r["interval"],
        repetitions=r["repetitions"],
        next_review=datetime.fromisoformat(
            r["next_review"],
        ),
        state=CardState(r["state"]),
        step_index=r["step_index"],
        lapse_count=r["lapse_count"],
        stability=r["stability"],
        difficulty=r["difficulty"],
    )


class Database:
    """Async SQLite backend for vocabulary words and progress.

    Use the async `connect` classmethod to create instances:

    .. code-block:: python

        db = await Database.connect("vocab.db")

    :param path: Path to the SQLite database file.
        Use `":memory:"` for an in-memory database.
    """

    def __init__(
        self, conn: aiosqlite.Connection,
    ) -> None:
        self._conn = conn

    @classmethod
    async def connect(
        cls, path: str | Path,
    ) -> "Database":
        """Create and initialise a new `Database`.

        :param path: Path to the SQLite database file.
            Use `":memory:"` for an in-memory database.
        :return: An open `Database` instance.
        """
        conn = await aiosqlite.connect(str(path))
        conn.row_factory = aiosqlite.Row
        await conn.executescript(_SCHEMA)
        db = cls(conn)
        await db._migrate()
        return db

    async def _migrate(self) -> None:
        """Add columns introduced after the initial schema."""
        cursor = await self._conn.execute(
            "PRAGMA table_info(progress)"
        )
        rows = await cursor.fetchall()
        cols = {row[1] for row in rows}
        if "state" not in cols:
            await self._conn.execute(
                "ALTER TABLE progress "
                "ADD COLUMN state TEXT "
                "NOT NULL DEFAULT 'review'"
            )
        if "step_index" not in cols:
            await self._conn.execute(
                "ALTER TABLE progress "
                "ADD COLUMN step_index INTEGER "
                "NOT NULL DEFAULT 0"
            )
        if "lapse_count" not in cols:
            await self._conn.execute(
                "ALTER TABLE progress "
                "ADD COLUMN lapse_count INTEGER "
                "NOT NULL DEFAULT 0"
            )
        if "stability" not in cols:
            await self._conn.execute(
                "ALTER TABLE progress "
                "ADD COLUMN stability REAL"
            )
        if "difficulty" not in cols:
            await self._conn.execute(
                "ALTER TABLE progress "
                "ADD COLUMN difficulty REAL"
            )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_words_langs "
            "ON words(language_from, language_to)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_progress_user_state "
            "ON progress(user_id, state)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_answer_user_word "
            "ON answer_history(user_id, word_id)"
        )
        await self._conn.commit()
        await self._migrate_words_owner_id()
        await self._migrate_user_id_to_int()

    async def _migrate_words_owner_id(self) -> None:
        """Add owner_id column to words table."""
        cursor = await self._conn.execute(
            "PRAGMA table_info(words)"
        )
        rows = await cursor.fetchall()
        cols = {row[1] for row in rows}
        if "owner_id" not in cols:
            await self._conn.execute(
                "ALTER TABLE words "
                "ADD COLUMN owner_id INTEGER "
                "REFERENCES users(id)"
            )
            await self._conn.commit()

    async def _migrate_user_id_to_int(self) -> None:
        """Migrate user_id from TEXT to INTEGER."""
        cursor = await self._conn.execute(
            "PRAGMA table_info(progress)"
        )
        col_info = await cursor.fetchall()
        col_types = {row[1]: row[2] for row in col_info}
        if col_types.get("user_id", "").upper() != "TEXT":
            return
        await self._conn.executescript("""
            CREATE TABLE progress_new (
                user_id INTEGER NOT NULL,
                word_id INTEGER NOT NULL,
                easiness_factor REAL NOT NULL DEFAULT 2.5,
                interval INTEGER NOT NULL DEFAULT 0,
                repetitions INTEGER NOT NULL DEFAULT 0,
                next_review TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'new',
                step_index INTEGER NOT NULL DEFAULT 0,
                lapse_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, word_id),
                FOREIGN KEY (user_id)
                    REFERENCES users(id),
                FOREIGN KEY (word_id)
                    REFERENCES words(id)
            );
            INSERT INTO progress_new
                SELECT CAST(user_id AS INTEGER),
                    word_id, easiness_factor,
                    interval, repetitions,
                    next_review, state,
                    step_index, lapse_count
                FROM progress;
            DROP TABLE progress;
            ALTER TABLE progress_new
                RENAME TO progress;

            CREATE TABLE answer_history_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                word_id INTEGER NOT NULL,
                exercise_type TEXT NOT NULL,
                correct INTEGER NOT NULL,
                quality INTEGER NOT NULL,
                answered_at TEXT NOT NULL
                    DEFAULT (datetime('now')),
                FOREIGN KEY (user_id)
                    REFERENCES users(id),
                FOREIGN KEY (word_id)
                    REFERENCES words(id)
            );
            INSERT INTO answer_history_new
                SELECT id,
                    CAST(user_id AS INTEGER),
                    word_id, exercise_type,
                    correct, quality, answered_at
                FROM answer_history;
            DROP TABLE answer_history;
            ALTER TABLE answer_history_new
                RENAME TO answer_history;
        """)

    # -- Users --------------------------------------------------------

    async def register_user(
        self,
        username: str,
        password: str,
        *,
        display_name: str | None = None,
    ) -> User:
        """Register a new user.

        :param username: Unique login name.
        :param password: Plain-text password (hashed before
            storage).
        :param display_name: Optional display name.
        :return: The created `User`.
        :raises ValueError: If the username already exists.
        """
        pw_hash = _hash_password(password)
        try:
            cursor = await self._conn.execute(
                "INSERT INTO users "
                "(username, display_name, password_hash) "
                "VALUES (?, ?, ?)",
                (username, display_name, pw_hash),
            )
            await self._conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(
                f"Username already exists: {username!r}"
            )
        return User(
            id=cursor.lastrowid,
            username=username,
            display_name=display_name,
            password_hash=pw_hash,
        )

    async def get_user(
        self, username: str,
    ) -> User | None:
        """Fetch a user by username.

        :param username: The username to look up.
        :return: `User` or `None` if not found.
        """
        cursor = await self._conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_user(row)

    async def authenticate_user(
        self,
        username: str,
        password: str,
    ) -> User | None:
        """Authenticate a user by username and password.

        :param username: The username.
        :param password: The plain-text password.
        :return: `User` if credentials are valid, `None`
            otherwise.
        """
        user = await self.get_user(username)
        if user is None:
            return None
        if not _verify_password(
            password, user.password_hash,
        ):
            return None
        return user

    # -- User Sessions ------------------------------------------------

    async def create_session(
        self,
        user_id: int,
        *,
        ttl_hours: int = 24,
    ) -> UserSession:
        """Create a new login session for a user.

        :param user_id: The user's database id.
        :param ttl_hours: Hours until the session expires.
        :return: The created `UserSession`.
        """
        token = secrets.token_hex(32)
        now = datetime.now()
        expires = now + timedelta(hours=ttl_hours)
        cursor = await self._conn.execute(
            "INSERT INTO user_sessions "
            "(user_id, token, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (
                user_id,
                token,
                now.strftime(_ISO_FMT),
                expires.strftime(_ISO_FMT),
            ),
        )
        await self._conn.commit()
        return UserSession(
            id=cursor.lastrowid,
            user_id=user_id,
            token=token,
            created_at=now,
            expires_at=expires,
        )

    async def get_session(
        self, token: str,
    ) -> UserSession | None:
        """Fetch a session by token.

        Returns `None` if the token does not exist or the
        session has expired.

        :param token: The session token.
        :return: `UserSession` or `None`.
        """
        cursor = await self._conn.execute(
            "SELECT * FROM user_sessions "
            "WHERE token = ?",
            (token,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        session = _row_to_user_session(row)
        if session.expires_at <= datetime.now():
            return None
        return session

    async def delete_session(self, token: str) -> None:
        """Delete a single session by token.

        :param token: The session token to remove.
        """
        await self._conn.execute(
            "DELETE FROM user_sessions WHERE token = ?",
            (token,),
        )
        await self._conn.commit()

    async def delete_user_sessions(
        self, user_id: int,
    ) -> None:
        """Delete all sessions for a user.

        :param user_id: The user's database id.
        """
        await self._conn.execute(
            "DELETE FROM user_sessions "
            "WHERE user_id = ?",
            (user_id,),
        )
        await self._conn.commit()

    # -- Words --------------------------------------------------------

    async def add_word(
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
        owner_id: int | None = None,
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
        :param owner_id: User who owns this word. `None` for
            shared words visible to all users.
        :return: The inserted `Word` with its assigned id.
        """
        tags = tags or []
        cursor = await self._conn.execute(
            "INSERT INTO words "
            "(language_from, language_to, word_from, "
            "word_to, gender, conjugation_group, tags, "
            "cefr, owner_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                language_from, language_to,
                word_from, word_to,
                gender, conjugation_group,
                json.dumps(tags),
                cefr,
                owner_id,
            ),
        )
        await self._conn.commit()
        return Word(
            id=cursor.lastrowid,
            language_from=language_from,
            language_to=language_to,
            word_from=word_from,
            word_to=word_to,
            gender=gender,
            conjugation_group=conjugation_group,
            tags=tags,
            cefr=cefr,
            owner_id=owner_id,
        )

    async def add_words(
        self,
        words: list[Word],
    ) -> list[Word]:
        """Bulk-insert words in a single transaction.

        :param words: List of `Word` objects to insert (the
            `id` field is ignored and assigned by the
            database).
        :return: List of inserted `Word` objects with
            assigned ids.
        """
        result: list[Word] = []
        for w in words:
            cursor = await self._conn.execute(
                "INSERT INTO words "
                "(language_from, language_to, "
                "word_from, word_to, "
                "gender, conjugation_group, tags,"
                " cefr, owner_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    w.language_from, w.language_to,
                    w.word_from, w.word_to,
                    w.gender, w.conjugation_group,
                    json.dumps(w.tags),
                    w.cefr,
                    w.owner_id,
                ),
            )
            result.append(
                w.model_copy(
                    update={"id": cursor.lastrowid},
                )
            )
        await self._conn.commit()
        return result

    async def get_words(
        self,
        language_from: str,
        language_to: str,
        *,
        owner_id: int | None = None,
    ) -> list[Word]:
        """Return words for a language pair.

        When `owner_id` is provided, returns shared words
        (``owner_id IS NULL``) plus words owned by that user.
        When omitted, returns all words regardless of owner.

        :param language_from: Source language code.
        :param language_to: Target language code.
        :param owner_id: Filter to shared + this user's
            words.
        :return: List of matching `Word` objects.
        """
        sql = (
            "SELECT id, language_from, language_to, "
            "word_from, word_to, "
            "gender, conjugation_group, tags, cefr, "
            "owner_id "
            "FROM words "
            "WHERE language_from = ? AND language_to = ?"
        )
        params: list = [language_from, language_to]
        if owner_id is not None:
            sql += (
                " AND (owner_id IS NULL"
                " OR owner_id = ?)"
            )
            params.append(owner_id)
        cursor = await self._conn.execute(
            sql, params,
        )
        rows = await cursor.fetchall()
        return [_row_to_word(r) for r in rows]

    async def update_word(self, word: Word) -> Word:
        """Update an existing word.

        :param word: The `Word` with updated fields. The `id`
            must be set.
        :return: The updated `Word`.
        :raises ValueError: If the word id is `None` or the
            word does not exist.
        """
        if word.id is None:
            raise ValueError("Word id must be set")
        cursor = await self._conn.execute(
            "UPDATE words SET "
            "language_from = ?, language_to = ?, "
            "word_from = ?, word_to = ?, "
            "gender = ?, conjugation_group = ?, "
            "tags = ?, cefr = ?, owner_id = ? "
            "WHERE id = ?",
            (
                word.language_from,
                word.language_to,
                word.word_from,
                word.word_to,
                word.gender,
                word.conjugation_group,
                json.dumps(word.tags),
                word.cefr,
                word.owner_id,
                word.id,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                f"Word not found: {word.id}"
            )
        await self._conn.commit()
        return word

    async def delete_word(self, word_id: int) -> None:
        """Delete a word by id.

        :param word_id: The word identifier.
        :raises ValueError: If the word does not exist.
        """
        cursor = await self._conn.execute(
            "DELETE FROM words WHERE id = ?",
            (word_id,),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                f"Word not found: {word_id}"
            )
        await self._conn.commit()

    # -- Progress -----------------------------------------------------

    async def get_progress(
        self,
        user_id: int,
        word_id: int,
    ) -> UserProgress | None:
        """Fetch progress for a user-word pair.

        :param user_id: The user's database id.
        :param word_id: The word identifier.
        :return: `UserProgress` or `None` if no record
            exists.
        """
        cursor = await self._conn.execute(
            "SELECT * FROM progress "
            "WHERE user_id = ? AND word_id = ?",
            (user_id, word_id),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_progress(row)

    async def get_all_progress(
        self,
        user_id: int,
        word_ids: list[int],
    ) -> dict[int, UserProgress]:
        """Fetch progress for multiple words in one query.

        :param user_id: The user's database id.
        :param word_ids: List of word identifiers.
        :return: Dict mapping `word_id` to `UserProgress`
            for words that have a progress record.
        """
        if not word_ids:
            return {}
        cursor = await self._conn.execute(
            "SELECT * FROM progress "
            "WHERE user_id = ? "
            f"AND word_id IN ({_in_clause(word_ids)})",
            [user_id, *word_ids],
        )
        rows = await cursor.fetchall()
        return {
            row["word_id"]: _row_to_progress(row)
            for row in rows
        }

    async def upsert_progress(
        self, progress: UserProgress,
    ) -> None:
        """Insert or update progress for a user-word pair.

        :param progress: The `UserProgress` to persist.
        """
        await self._conn.execute(
            "INSERT INTO progress "
            "(user_id, word_id, easiness_factor, "
            " interval, repetitions, next_review, "
            " state, step_index, lapse_count, "
            " stability, difficulty) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, word_id) DO UPDATE SET "
            " easiness_factor = excluded.easiness_factor, "
            " interval         = excluded.interval, "
            " repetitions      = excluded.repetitions, "
            " next_review      = excluded.next_review, "
            " state            = excluded.state, "
            " step_index       = excluded.step_index, "
            " lapse_count      = excluded.lapse_count, "
            " stability        = excluded.stability, "
            " difficulty        = excluded.difficulty",
            (
                progress.user_id,
                progress.word_id,
                progress.easiness_factor,
                progress.interval,
                progress.repetitions,
                progress.next_review.strftime(_ISO_FMT),
                progress.state.value,
                progress.step_index,
                progress.lapse_count,
                progress.stability,
                progress.difficulty,
            ),
        )
        await self._conn.commit()

    async def export_progress(
        self, user_id: int,
    ) -> list[dict]:
        """Export all progress rows for a user as dicts.

        Each dict contains `user_id`, `word_id`,
        `easiness_factor`, `interval`, `repetitions`,
        `next_review` (ISO 8601 string), `state`, and
        `step_index`. The result is JSON-serializable.

        :param user_id: The user's database id.
        :return: List of progress dicts.
        """
        cursor = await self._conn.execute(
            "SELECT user_id, word_id, easiness_factor, "
            "interval, repetitions, next_review, "
            "state, step_index, lapse_count, "
            "stability, difficulty "
            "FROM progress WHERE user_id = ?",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "user_id": r["user_id"],
                "word_id": r["word_id"],
                "easiness_factor": r["easiness_factor"],
                "interval": r["interval"],
                "repetitions": r["repetitions"],
                "next_review": r["next_review"],
                "state": r["state"],
                "step_index": r["step_index"],
                "lapse_count": r["lapse_count"],
                "stability": r["stability"],
                "difficulty": r["difficulty"],
            }
            for r in rows
        ]

    async def import_progress(
        self, records: list[dict],
    ) -> int:
        """Import progress records, upserting each one.

        Each dict must contain `user_id`, `word_id`,
        `easiness_factor`, `interval`, `repetitions`, and
        `next_review` (ISO 8601 string). The keys `state`
        and `step_index` are optional and default to
        `"review"` and `0` respectively.

        :param records: List of progress dicts.
        :return: Number of records imported.
        :raises KeyError: If a required key is missing.
        """
        required = {
            "user_id", "word_id", "easiness_factor",
            "interval", "repetitions", "next_review",
        }
        for rec in records:
            missing = required - rec.keys()
            if missing:
                raise KeyError(
                    f"Missing keys: {sorted(missing)}"
                )
            state = rec.get("state", "review")
            step_index = rec.get("step_index", 0)
            lapse_count = rec.get("lapse_count", 0)
            stability = rec.get("stability")
            difficulty = rec.get("difficulty")
            await self._conn.execute(
                "INSERT INTO progress "
                "(user_id, word_id, easiness_factor,"
                " interval, repetitions, next_review,"
                " state, step_index, lapse_count,"
                " stability, difficulty)"
                " VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(user_id, word_id) "
                "DO UPDATE SET "
                " easiness_factor "
                "  = excluded.easiness_factor, "
                " interval = excluded.interval, "
                " repetitions "
                "  = excluded.repetitions, "
                " next_review "
                "  = excluded.next_review, "
                " state = excluded.state, "
                " step_index "
                "  = excluded.step_index, "
                " lapse_count "
                "  = excluded.lapse_count, "
                " stability "
                "  = excluded.stability, "
                " difficulty "
                "  = excluded.difficulty",
                (
                    rec["user_id"],
                    rec["word_id"],
                    rec["easiness_factor"],
                    rec["interval"],
                    rec["repetitions"],
                    rec["next_review"],
                    state,
                    step_index,
                    lapse_count,
                    stability,
                    difficulty,
                ),
            )
        await self._conn.commit()
        return len(records)

    # -- Answer History -----------------------------------------------

    async def record_answer(
        self,
        user_id: int,
        word_id: int,
        exercise_type: str,
        correct: bool,
        quality: int,
    ) -> None:
        """Record a single answer in the history log.

        :param user_id: The user's database id.
        :param word_id: The word identifier.
        :param exercise_type: The exercise type string.
        :param correct: Whether the answer was correct.
        :param quality: SM-2 quality score (0-5).
        """
        await self._conn.execute(
            "INSERT INTO answer_history "
            "(user_id, word_id, exercise_type, "
            " correct, quality) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                user_id, word_id, exercise_type,
                int(correct), quality,
            ),
        )
        await self._conn.commit()

    async def get_answer_history(
        self,
        user_id: int,
        *,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[AnswerHistory]:
        """Fetch recent answer history for a user.

        :param user_id: The user's database id.
        :param limit: Maximum number of records to return.
        :param since: Only return answers after this
            datetime.
        :return: List of `AnswerHistory` records, newest
            first.
        """
        sql = (
            "SELECT id, user_id, word_id, "
            "exercise_type, correct, quality, "
            "answered_at "
            "FROM answer_history "
            "WHERE user_id = ? "
        )
        params: list[int | str] = [user_id]
        if since is not None:
            sql += "AND answered_at >= ? "
            params.append(since.strftime(_ISO_FMT))
        sql += (
            "ORDER BY answered_at DESC, id DESC "
            "LIMIT ?"
        )
        params.append(limit)
        cursor = await self._conn.execute(
            sql, params,
        )
        rows = await cursor.fetchall()
        return [
            AnswerHistory(
                id=r["id"],
                user_id=r["user_id"],
                word_id=r["word_id"],
                exercise_type=r["exercise_type"],
                correct=bool(r["correct"]),
                quality=r["quality"],
                answered_at=datetime.fromisoformat(
                    r["answered_at"],
                ),
            )
            for r in rows
        ]

    async def daily_stats(
        self,
        user_id: int,
        *,
        days: int = 30,
    ) -> list[DailyStats]:
        """Aggregate answer history into daily statistics.

        :param user_id: The user's database id.
        :param days: Number of past days to include.
        :return: List of `DailyStats`, most recent first.
        """
        cutoff = (
            datetime.now() - timedelta(days=days)
        ).strftime(_ISO_FMT)
        cursor = await self._conn.execute(
            _DAILY_STATS_SQL, (user_id, cutoff),
        )
        rows = await cursor.fetchall()
        return [
            DailyStats(
                date=r["day"],
                answers=r["answers"],
                correct=r["correct"],
                accuracy_pct=round(
                    r["correct"] / r["answers"] * 100,
                    1,
                ),
            )
            for r in rows
        ]

    async def weak_words(
        self,
        user_id: int,
        language_from: str,
        language_to: str,
        *,
        threshold: float = 0.5,
        min_attempts: int = 3,
        limit: int = 20,
    ) -> list[WeakWord]:
        """Find words the user consistently gets wrong.

        A word is "weak" when its error rate meets or
        exceeds `threshold` and it has at least
        `min_attempts` answers.

        :param user_id: The user's database id.
        :param language_from: Source language code.
        :param language_to: Target language code.
        :param threshold: Minimum error rate (0.0-1.0).
        :param min_attempts: Minimum answer count.
        :param limit: Maximum results to return.
        :return: List of `WeakWord`, highest error rate
            first.
        """
        cursor = await self._conn.execute(
            _WEAK_WORDS_SQL,
            (
                user_id, language_from, language_to,
                min_attempts, threshold, limit,
            ),
        )
        rows = await cursor.fetchall()
        return [
            WeakWord(
                word=Word(
                    id=r["id"],
                    language_from=r["language_from"],
                    language_to=r["language_to"],
                    word_from=r["word_from"],
                    word_to=r["word_to"],
                    gender=r["gender"],
                    conjugation_group=(
                        r["conjugation_group"]
                    ),
                    tags=json.loads(r["tags"]),
                    cefr=r["cefr"],
                    owner_id=r["owner_id"],
                ),
                attempts=r["attempts"],
                errors=r["errors"],
                error_rate=round(
                    r["errors"] / r["attempts"], 2,
                ),
                last_attempt=datetime.fromisoformat(
                    r["last_attempt"],
                ),
            )
            for r in rows
        ]

    async def retention_rate(
        self,
        user_id: int,
        *,
        days: int = 30,
    ) -> float:
        """Calculate the overall retention rate.

        :param user_id: The user's database id.
        :param days: Number of past days to include.
        :return: Percentage of correct answers (0.0-100.0),
            or 0.0 if no answers exist.
        """
        cutoff = (
            datetime.now() - timedelta(days=days)
        ).strftime(_ISO_FMT)
        cursor = await self._conn.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN correct THEN 1 ELSE 0 END) "
            "AS correct "
            "FROM answer_history "
            "WHERE user_id = ? AND answered_at >= ?",
            (user_id, cutoff),
        )
        row = await cursor.fetchone()
        total = row["total"]
        if not total:
            return 0.0
        return round(row["correct"] / total * 100, 1)

    async def forecast(
        self,
        user_id: int,
        *,
        days: int = 7,
    ) -> list[ReviewForecast]:
        """Predict upcoming review workload per day.

        :param user_id: The user's database id.
        :param days: Number of future days to forecast.
        :return: List of `ReviewForecast`, one per day,
            in chronological order.
        """
        today = datetime.now().date()
        horizon = today + timedelta(days=days)
        cursor = await self._conn.execute(
            "SELECT DATE(next_review) AS day, "
            "COUNT(*) AS cnt "
            "FROM progress "
            "WHERE user_id = ? "
            "AND state != ? "
            "AND DATE(next_review) <= ? "
            "GROUP BY day "
            "ORDER BY day",
            (
                user_id,
                CardState.SUSPENDED.value,
                horizon.isoformat(),
            ),
        )
        rows = await cursor.fetchall()
        by_day: dict[str, int] = {}
        for r in rows:
            by_day[r["day"]] = r["cnt"]
        today_str = today.isoformat()
        result: list[ReviewForecast] = []
        overdue = 0
        for day_str, cnt in by_day.items():
            if day_str < today_str:
                overdue += cnt
        for offset in range(days):
            d = today + timedelta(days=offset)
            d_str = d.isoformat()
            count = by_day.get(d_str, 0)
            if offset == 0:
                count += overdue
            result.append(
                ReviewForecast(
                    date=d_str, due_count=count,
                )
            )
        return result

    # -- Lessons ------------------------------------------------------

    async def _insert_lesson_words(
        self,
        lesson_id: int,
        word_ids: list[int],
    ) -> None:
        """Insert word links for a lesson.

        :param lesson_id: The lesson identifier.
        :param word_ids: Ordered list of word ids to link.
        """
        for pos, wid in enumerate(word_ids):
            await self._conn.execute(
                "INSERT INTO lesson_words "
                "(lesson_id, word_id, position) "
                "VALUES (?, ?, ?)",
                (lesson_id, wid, pos),
            )

    async def add_lesson(
        self, lesson: Lesson,
    ) -> Lesson:
        """Insert a lesson and link its words.

        :param lesson: The `Lesson` to insert.
        :return: The inserted `Lesson` with its assigned id.
        """
        return (await self.add_lessons([lesson]))[0]

    async def add_lessons(
        self, lessons: list[Lesson],
    ) -> list[Lesson]:
        """Bulk-insert lessons in a single transaction.

        :param lessons: List of `Lesson` objects to insert.
        :return: List of inserted `Lesson` objects with
            assigned ids.
        """
        result: list[Lesson] = []
        for lesson in lessons:
            cursor = await self._conn.execute(
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
            lesson_id = cursor.lastrowid
            await self._insert_lesson_words(
                lesson_id, lesson.word_ids,
            )
            result.append(
                lesson.model_copy(
                    update={"id": lesson_id},
                )
            )
        await self._conn.commit()
        return result

    async def get_lessons(
        self,
        language_from: str,
        language_to: str,
        *,
        cefr: str | None = None,
        tag: str | None = None,
    ) -> list[Lesson]:
        """Return lessons for a language pair.

        :param language_from: Source language code.
        :param language_to: Target language code.
        :param cefr: Filter by CEFR level.
        :param tag: Filter by topic tag.
        :return: List of matching `Lesson` objects with
            `word_ids` populated.
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
        cursor = await self._conn.execute(
            "SELECT id, title, description, "
            "language_from, language_to, cefr, "
            "tags, word_count "
            f"FROM lessons WHERE {where} "
            "ORDER BY id",
            params,
        )
        rows = await cursor.fetchall()
        if not rows:
            return []
        lesson_ids = [r["id"] for r in rows]
        cursor = await self._conn.execute(
            "SELECT lesson_id, word_id "
            "FROM lesson_words "
            "WHERE lesson_id "
            f"IN ({_in_clause(lesson_ids)}) "
            "ORDER BY position",
            lesson_ids,
        )
        lw_rows = await cursor.fetchall()
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

    async def get_lesson(
        self, lesson_id: int,
    ) -> Lesson | None:
        """Fetch a single lesson by id.

        :param lesson_id: The lesson identifier.
        :return: `Lesson` with `word_ids` populated, or
            `None` if not found.
        """
        cursor = await self._conn.execute(
            "SELECT id, title, description, "
            "language_from, language_to, cefr, "
            "tags, word_count "
            "FROM lessons WHERE id = ?",
            (lesson_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        cursor = await self._conn.execute(
            "SELECT word_id FROM lesson_words "
            "WHERE lesson_id = ? ORDER BY position",
            (lesson_id,),
        )
        word_rows = await cursor.fetchall()
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

    async def update_lesson(
        self, lesson: Lesson,
    ) -> Lesson:
        """Update an existing lesson and its word links.

        :param lesson: The `Lesson` with updated fields.
        :return: The updated `Lesson`.
        :raises ValueError: If the lesson id is `None` or
            the lesson does not exist.
        """
        if lesson.id is None:
            raise ValueError("Lesson id must be set")
        cursor = await self._conn.execute(
            "UPDATE lessons SET "
            "title = ?, description = ?, "
            "language_from = ?, language_to = ?, "
            "cefr = ?, tags = ?, word_count = ? "
            "WHERE id = ?",
            (
                lesson.title,
                lesson.description,
                lesson.language_from,
                lesson.language_to,
                lesson.cefr,
                json.dumps(lesson.tags),
                lesson.word_count,
                lesson.id,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                f"Lesson not found: {lesson.id}"
            )
        await self._conn.execute(
            "DELETE FROM lesson_words "
            "WHERE lesson_id = ?",
            (lesson.id,),
        )
        await self._insert_lesson_words(
            lesson.id, lesson.word_ids,
        )
        await self._conn.commit()
        return lesson

    async def delete_lesson(
        self, lesson_id: int,
    ) -> None:
        """Delete a lesson and its word links.

        :param lesson_id: The lesson identifier.
        :raises ValueError: If the lesson does not exist.
        """
        await self._conn.execute(
            "DELETE FROM lesson_words "
            "WHERE lesson_id = ?",
            (lesson_id,),
        )
        cursor = await self._conn.execute(
            "DELETE FROM lessons WHERE id = ?",
            (lesson_id,),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                f"Lesson not found: {lesson_id}"
            )
        await self._conn.commit()

    async def save_session_snapshot(
        self,
        snapshot: SessionSnapshot,
        key: str = "",
    ) -> None:
        """Persist a session snapshot.

        Replaces any existing snapshot for the same
        `(user_id, key)` pair.

        :param snapshot: The snapshot to save.
        :param key: Optional key to distinguish multiple
            snapshots per user (e.g. a chat id).
        """
        await self._conn.execute(
            "INSERT OR REPLACE INTO session_snapshots "
            "(user_id, key, data, saved_at) "
            "VALUES (?, ?, ?, ?)",
            (
                snapshot.user_id,
                key,
                snapshot.model_dump_json(),
                snapshot.saved_at.strftime(_ISO_FMT),
            ),
        )
        await self._conn.commit()

    async def get_session_snapshot(
        self,
        user_id: int,
        key: str = "",
    ) -> SessionSnapshot | None:
        """Load a previously saved session snapshot.

        :param user_id: The user's database id.
        :param key: Optional key matching the one used
            when saving.
        :return: The `SessionSnapshot`, or `None` if no
            snapshot exists.
        """
        cursor = await self._conn.execute(
            "SELECT data FROM session_snapshots "
            "WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return SessionSnapshot.model_validate_json(
            row["data"],
        )

    async def delete_session_snapshot(
        self,
        user_id: int,
        key: str = "",
    ) -> bool:
        """Delete a saved session snapshot.

        :param user_id: The user's database id.
        :param key: Optional key matching the one used
            when saving.
        :return: `True` if a snapshot was deleted,
            `False` if none existed.
        """
        cursor = await self._conn.execute(
            "DELETE FROM session_snapshots "
            "WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def close(self) -> None:
        """Close the database connection."""
        await self._conn.close()

    async def __aenter__(self) -> "Database":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()


_CSV_DELIMITERS = {".csv": ",", ".tsv": "\t"}


async def import_words_csv(
    db: "Database",
    path: str | Path,
    language_from: str,
    language_to: str,
    *,
    word_from_col: str = "word_from",
    word_to_col: str = "word_to",
    delimiter: str | None = None,
    owner_id: int | None = None,
) -> list[Word]:
    """Import words from a CSV or TSV file.

    The file must have a header row. The `word_from_col` and
    `word_to_col` columns are required. Optional columns
    (`gender`, `conjugation_group`, `tags`, `cefr`) are read
    when present.

    The `tags` column, if present, should contain a
    comma-separated list of tags (e.g. `"food,travel"`).

    :param db: The database to import into.
    :param path: Path to the CSV/TSV file.
    :param language_from: Source language code.
    :param language_to: Target language code.
    :param word_from_col: Column name for the source word.
    :param word_to_col: Column name for the translation.
    :param delimiter: Field delimiter. When `None`,
        auto-detected from the file extension (`.tsv` → tab,
        `.csv` and others → comma).
    :param owner_id: Owner id for imported words.
    :return: List of inserted `Word` objects with assigned
        ids.
    :raises FileNotFoundError: If the file does not exist.
    :raises ValueError: If required columns are missing.
    """
    path = Path(path)
    if delimiter is None:
        delimiter = _CSV_DELIMITERS.get(
            path.suffix.lower(), ","
        )
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        fields = reader.fieldnames or []
        for col in (word_from_col, word_to_col):
            if col not in fields:
                raise ValueError(
                    f"Required column {col!r} not found "
                    f"in {path.name}. "
                    f"Available: {fields}"
                )
        words: list[Word] = []
        for row in reader:
            tags_raw = row.get("tags", "")
            tags = (
                [t.strip() for t in tags_raw.split(",")
                 if t.strip()]
                if tags_raw else []
            )
            words.append(Word(
                language_from=language_from,
                language_to=language_to,
                word_from=row[word_from_col],
                word_to=row[word_to_col],
                gender=row.get("gender") or None,
                conjugation_group=(
                    row.get("conjugation_group") or None
                ),
                tags=tags,
                cefr=row.get("cefr") or None,
                owner_id=owner_id,
            ))
    return await db.add_words(words)
