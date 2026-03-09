"""PostgreSQL database layer for words and user progress."""

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from rembrandt.models import (
    AnswerHistory,
    CardState,
    DailyStats,
    Lesson,
    ReviewForecast,
    User,
    UserProgress,
    UserSession,
    WeakWord,
    Word,
)

_PG_SCHEMA = """\
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    display_name  TEXT,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    token      TEXT    NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS words (
    id                SERIAL PRIMARY KEY,
    language_from     TEXT NOT NULL,
    language_to       TEXT NOT NULL,
    word_from         TEXT NOT NULL,
    word_to           TEXT NOT NULL,
    gender            TEXT,
    conjugation_group TEXT,
    tags              JSONB NOT NULL DEFAULT '[]',
    cefr              TEXT,
    owner_id          INTEGER REFERENCES users(id),
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS progress (
    user_id          INTEGER NOT NULL,
    word_id          INTEGER NOT NULL,
    easiness_factor  REAL    NOT NULL DEFAULT 2.5,
    interval         INTEGER NOT NULL DEFAULT 0,
    repetitions      INTEGER NOT NULL DEFAULT 0,
    next_review      TIMESTAMP NOT NULL,
    state            TEXT    NOT NULL DEFAULT 'new',
    step_index       INTEGER NOT NULL DEFAULT 0,
    lapse_count      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, word_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (word_id) REFERENCES words(id)
);

CREATE TABLE IF NOT EXISTS lessons (
    id            SERIAL PRIMARY KEY,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    language_from TEXT NOT NULL,
    language_to   TEXT NOT NULL,
    cefr          TEXT,
    tags          JSONB NOT NULL DEFAULT '[]',
    word_count    INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL,
    word_id       INTEGER NOT NULL,
    exercise_type TEXT    NOT NULL,
    correct       BOOLEAN NOT NULL,
    quality       INTEGER NOT NULL,
    answered_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (word_id) REFERENCES words(id)
);
"""

_ISO_FMT = "%Y-%m-%dT%H:%M:%S"

_DAILY_STATS_SQL = (
    "SELECT answered_at::date AS day, "
    "COUNT(*) AS answers, "
    "SUM(CASE WHEN correct THEN 1 ELSE 0 END) AS correct "
    "FROM answer_history "
    "WHERE user_id = %s "
    "AND answered_at >= %s "
    "GROUP BY day "
    "ORDER BY day DESC"
)

_WEAK_WORDS_SQL = (
    "SELECT w.id, w.language_from, "
    "w.language_to, w.word_from, w.word_to, "
    "w.gender, w.conjugation_group, "
    "w.tags, w.cefr, w.owner_id, "
    "COUNT(*) AS attempts, "
    "SUM(CASE WHEN NOT ah.correct "
    "    THEN 1 ELSE 0 END) AS errors, "
    "MAX(ah.answered_at) AS last_attempt "
    "FROM answer_history ah "
    "JOIN words w ON w.id = ah.word_id "
    "WHERE ah.user_id = %s "
    "AND w.language_from = %s "
    "AND w.language_to = %s "
    "GROUP BY w.id, w.language_from, "
    "w.language_to, w.word_from, w.word_to, "
    "w.gender, w.conjugation_group, "
    "w.tags, w.cefr, w.owner_id "
    "HAVING COUNT(*) >= %s "
    "AND CAST(SUM(CASE WHEN NOT ah.correct "
    "    THEN 1 ELSE 0 END) AS REAL) "
    "    / COUNT(*) >= %s "
    "ORDER BY CAST(SUM(CASE WHEN NOT ah.correct "
    "    THEN 1 ELSE 0 END) AS REAL) "
    "    / COUNT(*) DESC "
    "LIMIT %s"
)


def _in_clause(ids: list) -> str:
    """Build a SQL IN-clause placeholder string.

    :param ids: List of values (length determines count).
    :return: Comma-separated `%s` placeholders,
        e.g. `"%s,%s,%s"`.
    """
    return ",".join("%s" for _ in ids)


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


def _row_to_user(r: dict) -> User:
    """Convert a dict row to a `User` model."""
    return User(
        id=r["id"],
        username=r["username"],
        display_name=r["display_name"],
        password_hash=r["password_hash"],
        created_at=r["created_at"],
    )


def _row_to_user_session(r: dict) -> UserSession:
    """Convert a dict row to a `UserSession` model."""
    return UserSession(
        id=r["id"],
        user_id=r["user_id"],
        token=r["token"],
        created_at=r["created_at"],
        expires_at=r["expires_at"],
    )


def _row_to_word(r: dict) -> Word:
    """Convert a dict row to a `Word` model."""
    tags = r["tags"]
    if isinstance(tags, str):
        tags = json.loads(tags)
    return Word(
        id=r["id"],
        language_from=r["language_from"],
        language_to=r["language_to"],
        word_from=r["word_from"],
        word_to=r["word_to"],
        gender=r["gender"],
        conjugation_group=r["conjugation_group"],
        tags=tags,
        cefr=r["cefr"],
        owner_id=r["owner_id"],
    )


def _row_to_progress(r: dict) -> UserProgress:
    """Convert a dict row to a `UserProgress` model."""
    return UserProgress(
        user_id=r["user_id"],
        word_id=r["word_id"],
        easiness_factor=r["easiness_factor"],
        interval=r["interval"],
        repetitions=r["repetitions"],
        next_review=r["next_review"],
        state=CardState(r["state"]),
        step_index=r["step_index"],
        lapse_count=r["lapse_count"],
        stability=r.get("stability"),
        difficulty=r.get("difficulty"),
    )


class PostgresDatabase:
    """PostgreSQL backend for vocabulary words and progress.

    :param dsn: PostgreSQL connection string, e.g.
        `"postgresql://rembrandt:rembrandt@localhost/rembrandt"`.
    """

    def __init__(self, dsn: str) -> None:
        self._conn = psycopg.connect(
            dsn, row_factory=dict_row, autocommit=False,
        )
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables if they do not exist."""
        with self._conn.cursor() as cur:
            for statement in _PG_SCHEMA.split(";"):
                statement = statement.strip()
                if statement:
                    cur.execute(statement)
        self._conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        """Add columns introduced after the initial schema."""
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT column_name "
                "FROM information_schema.columns "
                "WHERE table_name = 'words'"
            )
            word_cols = {
                r["column_name"] for r in cur.fetchall()
            }
            if "owner_id" not in word_cols:
                cur.execute(
                    "ALTER TABLE words "
                    "ADD COLUMN owner_id INTEGER "
                    "REFERENCES users(id)"
                )
            cur.execute(
                "SELECT column_name "
                "FROM information_schema.columns "
                "WHERE table_name = 'progress'"
            )
            prog_cols = {
                r["column_name"] for r in cur.fetchall()
            }
            if "stability" not in prog_cols:
                cur.execute(
                    "ALTER TABLE progress "
                    "ADD COLUMN stability "
                    "DOUBLE PRECISION"
                )
            if "difficulty" not in prog_cols:
                cur.execute(
                    "ALTER TABLE progress "
                    "ADD COLUMN difficulty "
                    "DOUBLE PRECISION"
                )
        self._conn.commit()

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
        :param password: Plain-text password (hashed before
            storage).
        :param display_name: Optional display name.
        :return: The created `User`.
        :raises ValueError: If the username already exists.
        """
        pw_hash = _hash_password(password)
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users "
                    "(username, display_name, password_hash) "
                    "VALUES (%s, %s, %s) RETURNING id",
                    (username, display_name, pw_hash),
                )
                row = cur.fetchone()
            self._conn.commit()
        except psycopg.errors.UniqueViolation:
            self._conn.rollback()
            raise ValueError(
                f"Username already exists: {username!r}"
            )
        return User(
            id=row["id"],
            username=username,
            display_name=display_name,
            password_hash=pw_hash,
        )

    def get_user(self, username: str) -> User | None:
        """Fetch a user by username.

        :param username: The username to look up.
        :return: `User` or `None` if not found.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
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
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_sessions "
                "(user_id, token, created_at, expires_at) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (user_id, token, now, expires),
            )
            row = cur.fetchone()
        self._conn.commit()
        return UserSession(
            id=row["id"],
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
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM user_sessions "
                "WHERE token = %s",
                (token,),
            )
            row = cur.fetchone()
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
        with self._conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_sessions "
                "WHERE token = %s",
                (token,),
            )
        self._conn.commit()

    def delete_user_sessions(self, user_id: int) -> None:
        """Delete all sessions for a user.

        :param user_id: The user's database id.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_sessions "
                "WHERE user_id = %s",
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
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO words "
                "(language_from, language_to, word_from, "
                "word_to, gender, conjugation_group, "
                "tags, cefr, owner_id) "
                "VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "RETURNING id",
                (
                    language_from, language_to,
                    word_from, word_to,
                    gender, conjugation_group,
                    Json(tags), cefr, owner_id,
                ),
            )
            row = cur.fetchone()
        self._conn.commit()
        return Word(
            id=row["id"],
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

    def add_words(
        self,
        words: list[Word],
    ) -> list[Word]:
        """Bulk-insert words in a single transaction.

        :param words: List of `Word` objects to insert (the `id`
            field is ignored and assigned by the database).
        :return: List of inserted `Word` objects with assigned
            ids.
        """
        result: list[Word] = []
        with self._conn.cursor() as cur:
            for w in words:
                cur.execute(
                    "INSERT INTO words "
                    "(language_from, language_to, "
                    "word_from, word_to, "
                    "gender, conjugation_group, "
                    "tags, cefr, owner_id) "
                    "VALUES "
                    "(%s, %s, %s, %s, %s, %s, "
                    "%s, %s, %s) "
                    "RETURNING id",
                    (
                        w.language_from, w.language_to,
                        w.word_from, w.word_to,
                        w.gender, w.conjugation_group,
                        Json(w.tags), w.cefr,
                        w.owner_id,
                    ),
                )
                row = cur.fetchone()
                result.append(
                    w.model_copy(
                        update={"id": row["id"]},
                    )
                )
        self._conn.commit()
        return result

    def get_words(
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
        :param owner_id: Filter to shared + this user's words.
        :return: List of matching `Word` objects.
        """
        sql = (
            "SELECT id, language_from, language_to, "
            "word_from, word_to, "
            "gender, conjugation_group, tags, cefr, "
            "owner_id "
            "FROM words "
            "WHERE language_from = %s "
            "AND language_to = %s"
        )
        params: list = [language_from, language_to]
        if owner_id is not None:
            sql += (
                " AND (owner_id IS NULL"
                " OR owner_id = %s)"
            )
            params.append(owner_id)
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
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
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE words SET "
                "language_from = %s, language_to = %s, "
                "word_from = %s, word_to = %s, "
                "gender = %s, conjugation_group = %s, "
                "tags = %s, cefr = %s, "
                "owner_id = %s "
                "WHERE id = %s",
                (
                    word.language_from,
                    word.language_to,
                    word.word_from,
                    word.word_to,
                    word.gender,
                    word.conjugation_group,
                    Json(word.tags),
                    word.cefr,
                    word.owner_id,
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
        with self._conn.cursor() as cur:
            cur.execute(
                "DELETE FROM words WHERE id = %s",
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
        user_id: int,
        word_id: int,
    ) -> UserProgress | None:
        """Fetch progress for a user-word pair.

        :param user_id: The user's database id.
        :param word_id: The word identifier.
        :return: `UserProgress` or `None` if no record exists.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM progress "
                "WHERE user_id = %s AND word_id = %s",
                (user_id, word_id),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return _row_to_progress(row)

    def get_all_progress(
        self,
        user_id: int,
        word_ids: list[int],
    ) -> dict[int, UserProgress]:
        """Fetch progress for multiple words in a single query.

        :param user_id: The user's database id.
        :param word_ids: List of word identifiers.
        :return: Dict mapping `word_id` to `UserProgress` for
            words that have a progress record.
        """
        if not word_ids:
            return {}
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM progress "
                "WHERE user_id = %s "
                f"AND word_id IN ({_in_clause(word_ids)})",
                [user_id, *word_ids],
            )
            rows = cur.fetchall()
        return {
            row["word_id"]: _row_to_progress(row)
            for row in rows
        }

    def upsert_progress(self, progress: UserProgress) -> None:
        """Insert or update progress for a user-word pair.

        :param progress: The `UserProgress` to persist.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO progress "
                "(user_id, word_id, easiness_factor, "
                " interval, repetitions, next_review, "
                " state, step_index, lapse_count, "
                " stability, difficulty) "
                "VALUES "
                "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                " ON CONFLICT(user_id, word_id) "
                "DO UPDATE SET"
                " easiness_factor "
                "  = EXCLUDED.easiness_factor, "
                " interval = EXCLUDED.interval, "
                " repetitions = EXCLUDED.repetitions, "
                " next_review = EXCLUDED.next_review, "
                " state = EXCLUDED.state, "
                " step_index = EXCLUDED.step_index, "
                " lapse_count = EXCLUDED.lapse_count, "
                " stability = EXCLUDED.stability, "
                " difficulty = EXCLUDED.difficulty",
                (
                    progress.user_id,
                    progress.word_id,
                    progress.easiness_factor,
                    progress.interval,
                    progress.repetitions,
                    progress.next_review,
                    progress.state.value,
                    progress.step_index,
                    progress.lapse_count,
                    progress.stability,
                    progress.difficulty,
                ),
            )
        self._conn.commit()

    def export_progress(
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
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, word_id, easiness_factor,"
                " interval, repetitions, next_review, "
                "state, step_index, lapse_count "
                "FROM progress WHERE user_id = %s",
                (user_id,),
            )
            rows = cur.fetchall()
        return [
            {
                "user_id": r["user_id"],
                "word_id": r["word_id"],
                "easiness_factor": r["easiness_factor"],
                "interval": r["interval"],
                "repetitions": r["repetitions"],
                "next_review": r["next_review"].strftime(
                    _ISO_FMT,
                ),
                "state": r["state"],
                "step_index": r["step_index"],
                "lapse_count": r["lapse_count"],
            }
            for r in rows
        ]

    def import_progress(
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
        with self._conn.cursor() as cur:
            for rec in records:
                missing = required - rec.keys()
                if missing:
                    raise KeyError(
                        f"Missing keys: {sorted(missing)}"
                    )
                state = rec.get("state", "review")
                step_index = rec.get("step_index", 0)
                lapse_count = rec.get("lapse_count", 0)
                cur.execute(
                    "INSERT INTO progress "
                    "(user_id, word_id, easiness_factor,"
                    " interval, repetitions, next_review,"
                    " state, step_index, lapse_count)"
                    " VALUES "
                    "(%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    " ON CONFLICT(user_id, word_id) "
                    "DO UPDATE SET "
                    " easiness_factor "
                    "  = EXCLUDED.easiness_factor, "
                    " interval = EXCLUDED.interval, "
                    " repetitions "
                    "  = EXCLUDED.repetitions, "
                    " next_review "
                    "  = EXCLUDED.next_review, "
                    " state = EXCLUDED.state, "
                    " step_index "
                    "  = EXCLUDED.step_index, "
                    " lapse_count "
                    "  = EXCLUDED.lapse_count",
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
                    ),
                )
        self._conn.commit()
        return len(records)

    # -- Answer History -----------------------------------------------

    def record_answer(
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
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO answer_history "
                "(user_id, word_id, exercise_type, "
                " correct, quality) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    user_id, word_id, exercise_type,
                    correct, quality,
                ),
            )
        self._conn.commit()

    def get_answer_history(
        self,
        user_id: int,
        *,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[AnswerHistory]:
        """Fetch recent answer history for a user.

        :param user_id: The user's database id.
        :param limit: Maximum number of records to return.
        :param since: Only return answers after this datetime.
        :return: List of `AnswerHistory` records, newest first.
        """
        sql = (
            "SELECT id, user_id, word_id, "
            "exercise_type, correct, quality, "
            "answered_at "
            "FROM answer_history "
            "WHERE user_id = %s "
        )
        params: list = [user_id]
        if since is not None:
            sql += "AND answered_at >= %s "
            params.append(since)
        sql += (
            "ORDER BY answered_at DESC, id DESC "
            "LIMIT %s"
        )
        params.append(limit)
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [
            AnswerHistory(
                id=r["id"],
                user_id=r["user_id"],
                word_id=r["word_id"],
                exercise_type=r["exercise_type"],
                correct=r["correct"],
                quality=r["quality"],
                answered_at=r["answered_at"],
            )
            for r in rows
        ]

    def daily_stats(
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
        cutoff = datetime.now() - timedelta(days=days)
        with self._conn.cursor() as cur:
            cur.execute(
                _DAILY_STATS_SQL, (user_id, cutoff),
            )
            rows = cur.fetchall()
        return [
            DailyStats(
                date=str(r["day"]),
                answers=r["answers"],
                correct=r["correct"],
                accuracy_pct=round(
                    r["correct"] / r["answers"] * 100,
                    1,
                ),
            )
            for r in rows
        ]

    def weak_words(
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

        A word is "weak" when its error rate meets or exceeds
        `threshold` and it has at least `min_attempts` answers.

        :param user_id: The user's database id.
        :param language_from: Source language code.
        :param language_to: Target language code.
        :param threshold: Minimum error rate (0.0-1.0).
        :param min_attempts: Minimum answer count.
        :param limit: Maximum results to return.
        :return: List of `WeakWord`, highest error rate first.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                _WEAK_WORDS_SQL,
                (
                    user_id, language_from, language_to,
                    min_attempts, threshold, limit,
                ),
            )
            rows = cur.fetchall()
        return [
            WeakWord(
                word=_row_to_word(r),
                attempts=r["attempts"],
                errors=r["errors"],
                error_rate=round(
                    r["errors"] / r["attempts"], 2,
                ),
                last_attempt=r["last_attempt"],
            )
            for r in rows
        ]

    def retention_rate(
        self,
        user_id: int,
        *,
        days: int = 30,
    ) -> float:
        """Calculate the overall retention rate from answer history.

        :param user_id: The user's database id.
        :param days: Number of past days to include.
        :return: Percentage of correct answers (0.0-100.0),
            or 0.0 if no answers exist.
        """
        cutoff = datetime.now() - timedelta(days=days)
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN correct THEN 1 ELSE 0 "
                "END) AS correct "
                "FROM answer_history "
                "WHERE user_id = %s "
                "AND answered_at >= %s",
                (user_id, cutoff),
            )
            row = cur.fetchone()
        total = row["total"]
        if not total:
            return 0.0
        return round(row["correct"] / total * 100, 1)

    def forecast(
        self,
        user_id: int,
        *,
        days: int = 7,
    ) -> list[ReviewForecast]:
        """Predict upcoming review workload per day.

        Counts scheduled reviews from the progress table,
        grouped by date. Past-due cards are included in
        today's count.

        :param user_id: The user's database id.
        :param days: Number of future days to forecast.
        :return: List of `ReviewForecast`, one per day,
            in chronological order.
        """
        today = datetime.now().date()
        horizon = today + timedelta(days=days)
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT DATE(next_review) AS day, "
                "COUNT(*) AS cnt "
                "FROM progress "
                "WHERE user_id = %s "
                "AND state != %s "
                "AND DATE(next_review) <= %s "
                "GROUP BY day "
                "ORDER BY day",
                (
                    user_id,
                    CardState.SUSPENDED.value,
                    horizon,
                ),
            )
            rows = cur.fetchall()
        by_day: dict[str, int] = {}
        for r in rows:
            by_day[str(r["day"])] = r["cnt"]
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

    def _insert_lesson_words(
        self,
        cur: psycopg.Cursor,
        lesson_id: int,
        word_ids: list[int],
    ) -> None:
        """Insert word links for a lesson.

        Must be called inside an active transaction.

        :param cur: Active database cursor.
        :param lesson_id: The lesson identifier.
        :param word_ids: Ordered list of word ids to link.
        """
        for pos, wid in enumerate(word_ids):
            cur.execute(
                "INSERT INTO lesson_words "
                "(lesson_id, word_id, position) "
                "VALUES (%s, %s, %s)",
                (lesson_id, wid, pos),
            )

    def add_lesson(self, lesson: Lesson) -> Lesson:
        """Insert a lesson and link its words.

        :param lesson: The `Lesson` to insert. The `word_ids`
            list links the lesson to existing words in the
            database.
        :return: The inserted `Lesson` with its assigned id.
        """
        return self.add_lessons([lesson])[0]

    def add_lessons(
        self, lessons: list[Lesson],
    ) -> list[Lesson]:
        """Bulk-insert lessons in a single transaction.

        :param lessons: List of `Lesson` objects to insert.
        :return: List of inserted `Lesson` objects with
            assigned ids.
        """
        result: list[Lesson] = []
        with self._conn.cursor() as cur:
            for lesson in lessons:
                cur.execute(
                    "INSERT INTO lessons "
                    "(title, description, language_from,"
                    " language_to, cefr, tags, word_count)"
                    " VALUES "
                    "(%s, %s, %s, %s, %s, %s, %s) "
                    "RETURNING id",
                    (
                        lesson.title,
                        lesson.description,
                        lesson.language_from,
                        lesson.language_to,
                        lesson.cefr,
                        Json(lesson.tags),
                        lesson.word_count,
                    ),
                )
                row = cur.fetchone()
                lesson_id = row["id"]
                self._insert_lesson_words(
                    cur, lesson_id, lesson.word_ids,
                )
                result.append(
                    lesson.model_copy(
                        update={"id": lesson_id},
                    )
                )
        self._conn.commit()
        return result

    def get_lessons(
        self,
        language_from: str,
        language_to: str,
        *,
        cefr: str | None = None,
        tag: str | None = None,
    ) -> list[Lesson]:
        """Return lessons for a language pair with optional
        filters.

        :param language_from: Source language code.
        :param language_to: Target language code.
        :param cefr: Filter by CEFR level.
        :param tag: Filter by topic tag.
        :return: List of matching `Lesson` objects with
            `word_ids` populated.
        """
        clauses = [
            "language_from = %s",
            "language_to = %s",
        ]
        params: list = [language_from, language_to]
        if cefr is not None:
            clauses.append("cefr = %s")
            params.append(cefr)
        if tag is not None:
            clauses.append("tags @> %s::jsonb")
            params.append(json.dumps([tag]))
        where = " AND ".join(clauses)
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, description, "
                "language_from, language_to, cefr, "
                "tags, word_count "
                f"FROM lessons WHERE {where} "
                "ORDER BY id",
                params,
            )
            rows = cur.fetchall()
        if not rows:
            return []
        lesson_ids = [r["id"] for r in rows]
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT lesson_id, word_id "
                "FROM lesson_words "
                "WHERE lesson_id "
                f"IN ({_in_clause(lesson_ids)}) "
                "ORDER BY position",
                lesson_ids,
            )
            lw_rows = cur.fetchall()
        word_map: dict[int, list[int]] = {}
        for lw in lw_rows:
            word_map.setdefault(
                lw["lesson_id"], [],
            ).append(lw["word_id"])
        return [
            Lesson(
                id=r["id"],
                title=r["title"],
                description=r["description"],
                language_from=r["language_from"],
                language_to=r["language_to"],
                cefr=r["cefr"],
                tags=(
                    r["tags"]
                    if isinstance(r["tags"], list)
                    else json.loads(r["tags"])
                ),
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
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, description, "
                "language_from, language_to, cefr, "
                "tags, word_count "
                "FROM lessons WHERE id = %s",
                (lesson_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT word_id FROM lesson_words "
                "WHERE lesson_id = %s "
                "ORDER BY position",
                (lesson_id,),
            )
            word_rows = cur.fetchall()
        tags = row["tags"]
        if isinstance(tags, str):
            tags = json.loads(tags)
        return Lesson(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            language_from=row["language_from"],
            language_to=row["language_to"],
            cefr=row["cefr"],
            tags=tags,
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
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE lessons SET "
                "title = %s, description = %s, "
                "language_from = %s, language_to = %s, "
                "cefr = %s, tags = %s, word_count = %s "
                "WHERE id = %s",
                (
                    lesson.title,
                    lesson.description,
                    lesson.language_from,
                    lesson.language_to,
                    lesson.cefr,
                    Json(lesson.tags),
                    lesson.word_count,
                    lesson.id,
                ),
            )
            if cur.rowcount == 0:
                raise ValueError(
                    f"Lesson not found: {lesson.id}"
                )
            cur.execute(
                "DELETE FROM lesson_words "
                "WHERE lesson_id = %s",
                (lesson.id,),
            )
            self._insert_lesson_words(
                cur, lesson.id, lesson.word_ids,
            )
        self._conn.commit()
        return lesson

    def delete_lesson(self, lesson_id: int) -> None:
        """Delete a lesson and its word links.

        :param lesson_id: The lesson identifier.
        :raises ValueError: If the lesson does not exist.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                "DELETE FROM lesson_words "
                "WHERE lesson_id = %s",
                (lesson_id,),
            )
            cur.execute(
                "DELETE FROM lessons WHERE id = %s",
                (lesson_id,),
            )
            if cur.rowcount == 0:
                raise ValueError(
                    f"Lesson not found: {lesson_id}"
                )
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> "PostgresDatabase":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
