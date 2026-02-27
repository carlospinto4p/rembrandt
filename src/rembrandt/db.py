"""SQLite database layer for words and user progress."""

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from rembrandt.models import (
    AnswerHistory,
    DailyStats,
    Lesson,
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

CREATE TABLE IF NOT EXISTS answer_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       TEXT    NOT NULL,
    word_id       INTEGER NOT NULL,
    exercise_type TEXT    NOT NULL,
    correct       INTEGER NOT NULL,
    quality       INTEGER NOT NULL,
    answered_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (word_id) REFERENCES words(id)
);
"""

_ISO_FMT = "%Y-%m-%dT%H:%M:%S"


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
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${h}"


def _verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored salt$hash string."""
    salt, expected = stored.split("$", 1)
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return h == expected


def _row_to_user(r: sqlite3.Row) -> User:
    """Convert a SQLite row to a `User` model."""
    return User(
        id=r["id"],
        username=r["username"],
        display_name=r["display_name"],
        password_hash=r["password_hash"],
        created_at=datetime.fromisoformat(r["created_at"]),
    )


def _row_to_user_session(r: sqlite3.Row) -> UserSession:
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
        next_review=datetime.fromisoformat(
            r["next_review"],
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

    # -- Users --------------------------------------------------------

    def register_user(
        self,
        username: str,
        password: str,
        *,
        display_name: str | None = None,
    ) -> User:
        """Register a new user.

        :param username: Unique login name.
        :param password: Plain-text password (hashed before storage).
        :param display_name: Optional display name.
        :return: The created `User`.
        :raises ValueError: If the username already exists.
        """
        pw_hash = _hash_password(password)
        try:
            cur = self._conn.execute(
                "INSERT INTO users "
                "(username, display_name, password_hash) "
                "VALUES (?, ?, ?)",
                (username, display_name, pw_hash),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(
                f"Username already exists: {username!r}"
            )
        return User(
            id=cur.lastrowid,
            username=username,
            display_name=display_name,
            password_hash=pw_hash,
        )

    def get_user(self, username: str) -> User | None:
        """Fetch a user by username.

        :param username: The username to look up.
        :return: `User` or `None` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_user(row)

    def authenticate_user(
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
        user = self.get_user(username)
        if user is None:
            return None
        if not _verify_password(
            password, user.password_hash,
        ):
            return None
        return user

    # -- User Sessions ------------------------------------------------

    def create_session(
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
        cur = self._conn.execute(
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
        self._conn.commit()
        return UserSession(
            id=cur.lastrowid,
            user_id=user_id,
            token=token,
            created_at=now,
            expires_at=expires,
        )

    def get_session(self, token: str) -> UserSession | None:
        """Fetch a session by token.

        Returns `None` if the token does not exist or the
        session has expired.

        :param token: The session token.
        :return: `UserSession` or `None`.
        """
        row = self._conn.execute(
            "SELECT * FROM user_sessions "
            "WHERE token = ?",
            (token,),
        ).fetchone()
        if row is None:
            return None
        session = _row_to_user_session(row)
        if session.expires_at <= datetime.now():
            return None
        return session

    def delete_session(self, token: str) -> None:
        """Delete a single session by token.

        :param token: The session token to remove.
        """
        self._conn.execute(
            "DELETE FROM user_sessions WHERE token = ?",
            (token,),
        )
        self._conn.commit()

    def delete_user_sessions(self, user_id: int) -> None:
        """Delete all sessions for a user.

        :param user_id: The user's database id.
        """
        self._conn.execute(
            "DELETE FROM user_sessions "
            "WHERE user_id = ?",
            (user_id,),
        )
        self._conn.commit()

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

    def update_word(self, word: Word) -> Word:
        """Update an existing word.

        :param word: The `Word` with updated fields. The `id`
            must be set.
        :return: The updated `Word`.
        :raises ValueError: If the word id is `None` or the
            word does not exist.
        """
        if word.id is None:
            raise ValueError("Word id must be set")
        cur = self._conn.execute(
            "UPDATE words SET "
            "language_from = ?, language_to = ?, "
            "word_from = ?, word_to = ?, "
            "gender = ?, conjugation_group = ?, "
            "tags = ?, cefr = ? "
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
                word.id,
            ),
        )
        if cur.rowcount == 0:
            raise ValueError(
                f"Word not found: {word.id}"
            )
        self._conn.commit()
        return word

    def delete_word(self, word_id: int) -> None:
        """Delete a word by id.

        :param word_id: The word identifier.
        :raises ValueError: If the word does not exist.
        """
        cur = self._conn.execute(
            "DELETE FROM words WHERE id = ?",
            (word_id,),
        )
        if cur.rowcount == 0:
            raise ValueError(
                f"Word not found: {word_id}"
            )
        self._conn.commit()

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
        rows = self._conn.execute(
            "SELECT * FROM progress "
            "WHERE user_id = ? "
            f"AND word_id IN ({_in_clause(word_ids)})",
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

    def export_progress(
        self, user_id: str,
    ) -> list[dict]:
        """Export all progress rows for a user as dicts.

        Each dict contains `user_id`, `word_id`,
        `easiness_factor`, `interval`, `repetitions`, and
        `next_review` (ISO 8601 string). The result is
        JSON-serializable.

        :param user_id: The user identifier.
        :return: List of progress dicts.
        """
        rows = self._conn.execute(
            "SELECT user_id, word_id, easiness_factor, "
            "interval, repetitions, next_review "
            "FROM progress WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return [
            {
                "user_id": r["user_id"],
                "word_id": r["word_id"],
                "easiness_factor": r["easiness_factor"],
                "interval": r["interval"],
                "repetitions": r["repetitions"],
                "next_review": r["next_review"],
            }
            for r in rows
        ]

    def import_progress(
        self, records: list[dict],
    ) -> int:
        """Import progress records, upserting each one.

        Each dict must contain `user_id`, `word_id`,
        `easiness_factor`, `interval`, `repetitions`, and
        `next_review` (ISO 8601 string).

        :param records: List of progress dicts.
        :return: Number of records imported.
        :raises KeyError: If a required key is missing.
        """
        required = {
            "user_id", "word_id", "easiness_factor",
            "interval", "repetitions", "next_review",
        }
        with self._conn:
            for rec in records:
                missing = required - rec.keys()
                if missing:
                    raise KeyError(
                        f"Missing keys: {sorted(missing)}"
                    )
                self._conn.execute(
                    "INSERT INTO progress "
                    "(user_id, word_id, easiness_factor,"
                    " interval, repetitions, next_review)"
                    " VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(user_id, word_id) "
                    "DO UPDATE SET "
                    " easiness_factor "
                    "  = excluded.easiness_factor, "
                    " interval = excluded.interval, "
                    " repetitions "
                    "  = excluded.repetitions, "
                    " next_review "
                    "  = excluded.next_review",
                    (
                        rec["user_id"],
                        rec["word_id"],
                        rec["easiness_factor"],
                        rec["interval"],
                        rec["repetitions"],
                        rec["next_review"],
                    ),
                )
        return len(records)

    # -- Answer History -----------------------------------------------

    def record_answer(
        self,
        user_id: str,
        word_id: int,
        exercise_type: str,
        correct: bool,
        quality: int,
    ) -> None:
        """Record a single answer in the history log.

        :param user_id: The user identifier.
        :param word_id: The word identifier.
        :param exercise_type: The exercise type string.
        :param correct: Whether the answer was correct.
        :param quality: SM-2 quality score (0-5).
        """
        self._conn.execute(
            "INSERT INTO answer_history "
            "(user_id, word_id, exercise_type, "
            " correct, quality) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                user_id, word_id, exercise_type,
                int(correct), quality,
            ),
        )
        self._conn.commit()

    def get_answer_history(
        self,
        user_id: str,
        *,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[AnswerHistory]:
        """Fetch recent answer history for a user.

        :param user_id: The user identifier.
        :param limit: Maximum number of records to return.
        :param since: Only return answers after this datetime.
        :return: List of `AnswerHistory` records, newest first.
        """
        if since is not None:
            rows = self._conn.execute(
                "SELECT id, user_id, word_id, "
                "exercise_type, correct, quality, "
                "answered_at "
                "FROM answer_history "
                "WHERE user_id = ? "
                "AND answered_at >= ? "
                "ORDER BY answered_at DESC "
                "LIMIT ?",
                (
                    user_id,
                    since.strftime(_ISO_FMT),
                    limit,
                ),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, user_id, word_id, "
                "exercise_type, correct, quality, "
                "answered_at "
                "FROM answer_history "
                "WHERE user_id = ? "
                "ORDER BY answered_at DESC "
                "LIMIT ?",
                (user_id, limit),
            ).fetchall()
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

    def daily_stats(
        self,
        user_id: str,
        *,
        days: int = 30,
    ) -> list[DailyStats]:
        """Aggregate answer history into daily statistics.

        :param user_id: The user identifier.
        :param days: Number of past days to include.
        :return: List of `DailyStats`, most recent first.
        """
        cutoff = (
            datetime.now() - timedelta(days=days)
        ).strftime(_ISO_FMT)
        rows = self._conn.execute(
            "SELECT date(answered_at) AS day, "
            "COUNT(*) AS answers, "
            "SUM(correct) AS correct "
            "FROM answer_history "
            "WHERE user_id = ? "
            "AND answered_at >= ? "
            "GROUP BY day "
            "ORDER BY day DESC",
            (user_id, cutoff),
        ).fetchall()
        return [
            DailyStats(
                date=r["day"],
                answers=r["answers"],
                correct=r["correct"],
                accuracy_pct=round(
                    r["correct"] / r["answers"] * 100, 1,
                ),
            )
            for r in rows
        ]

    def weak_words(
        self,
        user_id: str,
        language_from: str,
        language_to: str,
        *,
        threshold: float = 0.5,
        min_attempts: int = 3,
        limit: int = 20,
    ) -> list[WeakWord]:
        """Find words the user consistently gets wrong.

        A word is "weak" when its error rate meets or exceeds
        `threshold` and it has at least `min_attempts` answers.

        :param user_id: The user identifier.
        :param language_from: Source language code.
        :param language_to: Target language code.
        :param threshold: Minimum error rate (0.0-1.0).
        :param min_attempts: Minimum answer count.
        :param limit: Maximum results to return.
        :return: List of `WeakWord`, highest error rate first.
        """
        rows = self._conn.execute(
            "SELECT w.id, w.language_from, "
            "w.language_to, w.word_from, w.word_to, "
            "w.gender, w.conjugation_group, "
            "w.tags, w.cefr, "
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
            "LIMIT ?",
            (
                user_id, language_from, language_to,
                min_attempts, threshold, limit,
            ),
        ).fetchall()
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

    # -- Lessons ------------------------------------------------------

    def _insert_lesson_words(
        self,
        lesson_id: int,
        word_ids: list[int],
    ) -> None:
        """Insert word links for a lesson.

        Must be called inside an active transaction.

        :param lesson_id: The lesson identifier.
        :param word_ids: Ordered list of word ids to link.
        """
        for pos, wid in enumerate(word_ids):
            self._conn.execute(
                "INSERT INTO lesson_words "
                "(lesson_id, word_id, position) "
                "VALUES (?, ?, ?)",
                (lesson_id, wid, pos),
            )

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
                self._insert_lesson_words(
                    lesson_id, lesson.word_ids,
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
        lw_rows = self._conn.execute(
            "SELECT lesson_id, word_id FROM lesson_words "
            "WHERE lesson_id "
            f"IN ({_in_clause(lesson_ids)}) "
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

    def update_lesson(self, lesson: Lesson) -> Lesson:
        """Update an existing lesson and its word links.

        :param lesson: The `Lesson` with updated fields. The
            `id` must be set. The `word_ids` list replaces the
            current word links entirely.
        :return: The updated `Lesson`.
        :raises ValueError: If the lesson id is `None` or the
            lesson does not exist.
        """
        if lesson.id is None:
            raise ValueError("Lesson id must be set")
        with self._conn:
            cur = self._conn.execute(
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
            if cur.rowcount == 0:
                raise ValueError(
                    f"Lesson not found: {lesson.id}"
                )
            self._conn.execute(
                "DELETE FROM lesson_words "
                "WHERE lesson_id = ?",
                (lesson.id,),
            )
            self._insert_lesson_words(
                lesson.id, lesson.word_ids,
            )
        return lesson

    def delete_lesson(self, lesson_id: int) -> None:
        """Delete a lesson and its word links.

        :param lesson_id: The lesson identifier.
        :raises ValueError: If the lesson does not exist.
        """
        with self._conn:
            self._conn.execute(
                "DELETE FROM lesson_words "
                "WHERE lesson_id = ?",
                (lesson_id,),
            )
            cur = self._conn.execute(
                "DELETE FROM lessons WHERE id = ?",
                (lesson_id,),
            )
            if cur.rowcount == 0:
                raise ValueError(
                    f"Lesson not found: {lesson_id}"
                )

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
