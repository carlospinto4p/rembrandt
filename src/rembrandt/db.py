"""Async SQLite database layer for concepts and user progress."""

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
    ConceptTranslation,
    ConversationStage,
    ConversationState,
    Concept,
    DailyStats,
    Language,
    ReviewForecast,
    SessionSnapshot,
    Topic,
    User,
    UserProgress,
    UserSession,
    WeakConcept,
)

_BASE_SCHEMA = """\
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

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

CREATE TABLE IF NOT EXISTS concepts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    front      TEXT NOT NULL,
    back       TEXT NOT NULL,
    context    TEXT NOT NULL DEFAULT '',
    tags       TEXT NOT NULL DEFAULT '[]',
    owner_id   INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS progress (
    user_id          INTEGER NOT NULL,
    concept_id       INTEGER NOT NULL,
    easiness_factor  REAL    NOT NULL DEFAULT 2.5,
    interval         INTEGER NOT NULL DEFAULT 0,
    repetitions      INTEGER NOT NULL DEFAULT 0,
    next_review      TEXT    NOT NULL,
    state            TEXT    NOT NULL DEFAULT 'new',
    step_index       INTEGER NOT NULL DEFAULT 0,
    lapse_count      INTEGER NOT NULL DEFAULT 0,
    stability        REAL,
    difficulty       REAL,
    PRIMARY KEY (user_id, concept_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (concept_id) REFERENCES concepts(id)
);

CREATE TABLE IF NOT EXISTS topics (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    tags          TEXT NOT NULL DEFAULT '[]',
    concept_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS topic_concepts (
    topic_id   INTEGER NOT NULL,
    concept_id INTEGER NOT NULL,
    position   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (topic_id, concept_id),
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    FOREIGN KEY (concept_id) REFERENCES concepts(id)
);

CREATE TABLE IF NOT EXISTS answer_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    concept_id    INTEGER NOT NULL,
    exercise_type TEXT    NOT NULL,
    correct       INTEGER NOT NULL,
    quality       INTEGER NOT NULL,
    answered_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (concept_id) REFERENCES concepts(id)
);

CREATE TABLE IF NOT EXISTS session_snapshots (
    user_id   INTEGER NOT NULL,
    key       TEXT    NOT NULL DEFAULT '',
    data      TEXT    NOT NULL,
    saved_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, key),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS conversation_states (
    user_id    INTEGER NOT NULL,
    key        TEXT    NOT NULL DEFAULT '',
    stage      TEXT    NOT NULL DEFAULT 'idle',
    data       TEXT    NOT NULL DEFAULT '{}',
    updated_at TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, key),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_concepts_tags
    ON concepts(tags);
CREATE INDEX IF NOT EXISTS idx_progress_user_state
    ON progress(user_id, state);
CREATE INDEX IF NOT EXISTS idx_answer_user_concept
    ON answer_history(user_id, concept_id);
"""

# Each migration is a SQL script applied in order.  The list
# index corresponds to the target schema version (1-based).
# Append new migrations here — never modify existing ones.
_MIGRATIONS: list[str] = [
    # --- Migration 1: multi-language translations ---
    """\
CREATE TABLE IF NOT EXISTS languages (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS concept_translations (
    concept_id    INTEGER NOT NULL,
    language_code TEXT    NOT NULL,
    front         TEXT    NOT NULL,
    back          TEXT    NOT NULL,
    context       TEXT    NOT NULL DEFAULT '',
    PRIMARY KEY (concept_id, language_code),
    FOREIGN KEY (concept_id) REFERENCES concepts(id),
    FOREIGN KEY (language_code) REFERENCES languages(code)
);

CREATE INDEX IF NOT EXISTS idx_translations_lang
    ON concept_translations(language_code);
""",
]


async def _get_schema_version(
    conn: aiosqlite.Connection,
) -> int:
    """Return the current schema version (0 if unset)."""
    cursor = await conn.execute(
        "SELECT version FROM schema_version "
        "LIMIT 1",
    )
    row = await cursor.fetchone()
    if row is None:
        return 0
    return row[0]


async def _set_schema_version(
    conn: aiosqlite.Connection,
    version: int,
) -> None:
    """Persist the schema version."""
    await conn.execute(
        "DELETE FROM schema_version",
    )
    await conn.execute(
        "INSERT INTO schema_version (version) "
        "VALUES (?)",
        (version,),
    )


async def _apply_migrations(
    conn: aiosqlite.Connection,
) -> None:
    """Run pending schema migrations."""
    current = await _get_schema_version(conn)
    for i, sql in enumerate(
        _MIGRATIONS[current:], start=current + 1,
    ):
        await conn.executescript(sql)
        await _set_schema_version(conn, i)
        await conn.commit()

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

_WEAK_CONCEPTS_SQL = (
    "SELECT c.id, c.front, c.back, "
    "c.context, c.tags, c.owner_id, "
    "COUNT(*) AS attempts, "
    "SUM(CASE WHEN ah.correct = 0 "
    "    THEN 1 ELSE 0 END) AS errors, "
    "MAX(ah.answered_at) AS last_attempt "
    "FROM answer_history ah "
    "JOIN concepts c ON c.id = ah.concept_id "
    "WHERE ah.user_id = ? "
    "GROUP BY ah.concept_id "
    "HAVING attempts >= ? "
    "AND CAST(errors AS REAL) "
    "    / attempts >= ? "
    "ORDER BY CAST(errors AS REAL) "
    "    / attempts DESC "
    "LIMIT ?"
)

_WEAK_CONCEPTS_TAGGED_SQL = (
    "SELECT c.id, c.front, c.back, "
    "c.context, c.tags, c.owner_id, "
    "COUNT(*) AS attempts, "
    "SUM(CASE WHEN ah.correct = 0 "
    "    THEN 1 ELSE 0 END) AS errors, "
    "MAX(ah.answered_at) AS last_attempt "
    "FROM answer_history ah "
    "JOIN concepts c ON c.id = ah.concept_id "
    "WHERE ah.user_id = ? "
    "AND EXISTS (SELECT 1 FROM json_each(c.tags) "
    "    WHERE json_each.value = ?) "
    "GROUP BY ah.concept_id "
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


def _row_to_concept(r: aiosqlite.Row) -> Concept:
    """Convert a SQLite row to a `Concept` model."""
    return Concept(
        id=r["id"],
        front=r["front"],
        back=r["back"],
        context=r["context"],
        tags=json.loads(r["tags"]),
        owner_id=r["owner_id"],
    )


def _row_to_language(r: aiosqlite.Row) -> Language:
    """Convert a SQLite row to a `Language` model."""
    return Language(code=r["code"], name=r["name"])


def _row_to_translation(
    r: aiosqlite.Row,
) -> ConceptTranslation:
    """Convert a SQLite row to a `ConceptTranslation`."""
    return ConceptTranslation(
        concept_id=r["concept_id"],
        language_code=r["language_code"],
        front=r["front"],
        back=r["back"],
        context=r["context"],
    )


def _row_to_progress(r: aiosqlite.Row) -> UserProgress:
    """Convert a SQLite row to a `UserProgress` model."""
    return UserProgress(
        user_id=r["user_id"],
        concept_id=r["concept_id"],
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
    """Async SQLite backend for concepts and progress.

    Use the async `connect` classmethod to create instances:

    .. code-block:: python

        db = await Database.connect("study.db")

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

        Creates the base schema if needed, then applies any
        pending migrations so that existing databases are
        upgraded automatically.

        :param path: Path to the SQLite database file.
            Use `":memory:"` for an in-memory database.
        :return: An open `Database` instance.
        """
        conn = await aiosqlite.connect(str(path))
        conn.row_factory = aiosqlite.Row
        await conn.executescript(_BASE_SCHEMA)
        await _apply_migrations(conn)
        return cls(conn)

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

    # -- Concepts -----------------------------------------------------

    async def add_concept(
        self,
        front: str,
        back: str,
        *,
        context: str = "",
        tags: list[str] | None = None,
        owner_id: int | None = None,
    ) -> Concept:
        """Insert a single concept and return it with its id.

        :param front: The prompt shown to the learner.
        :param back: The expected answer.
        :param context: Optional explanation or notes.
        :param tags: Grouping tags.
        :param owner_id: User who owns this concept. `None`
            for shared concepts visible to all users.
        :return: The inserted `Concept` with its assigned id.
        """
        tags = tags or []
        cursor = await self._conn.execute(
            "INSERT INTO concepts "
            "(front, back, context, tags, owner_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                front, back, context,
                json.dumps(tags),
                owner_id,
            ),
        )
        await self._conn.commit()
        return Concept(
            id=cursor.lastrowid,
            front=front,
            back=back,
            context=context,
            tags=tags,
            owner_id=owner_id,
        )

    async def add_concepts(
        self,
        concepts: list[Concept],
    ) -> list[Concept]:
        """Bulk-insert concepts in a single transaction.

        :param concepts: List of `Concept` objects to insert
            (the `id` field is ignored and assigned by the
            database).
        :return: List of inserted `Concept` objects with
            assigned ids.
        """
        result: list[Concept] = []
        for c in concepts:
            cursor = await self._conn.execute(
                "INSERT INTO concepts "
                "(front, back, context, tags, owner_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    c.front, c.back, c.context,
                    json.dumps(c.tags),
                    c.owner_id,
                ),
            )
            result.append(
                c.model_copy(
                    update={"id": cursor.lastrowid},
                )
            )
        await self._conn.commit()
        return result

    async def get_concepts(
        self,
        *,
        tag: str | None = None,
        owner_id: int | None = None,
    ) -> list[Concept]:
        """Return concepts, optionally filtered by tag.

        When `owner_id` is provided, returns shared concepts
        (``owner_id IS NULL``) plus concepts owned by that
        user. When omitted, returns all concepts regardless
        of owner.

        :param tag: Filter by tag. When `None`, returns all.
        :param owner_id: Filter to shared + this user's
            concepts.
        :return: List of matching `Concept` objects.
        """
        clauses: list[str] = []
        params: list = []
        if tag is not None:
            clauses.append(
                "EXISTS (SELECT 1 FROM json_each(tags) "
                "WHERE json_each.value = ?)"
            )
            params.append(tag)
        if owner_id is not None:
            clauses.append(
                "(owner_id IS NULL OR owner_id = ?)"
            )
            params.append(owner_id)
        sql = (
            "SELECT id, front, back, context, "
            "tags, owner_id FROM concepts"
        )
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        cursor = await self._conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [_row_to_concept(r) for r in rows]

    async def update_concept(
        self, concept: Concept,
    ) -> Concept:
        """Update an existing concept.

        :param concept: The `Concept` with updated fields.
            The `id` must be set.
        :return: The updated `Concept`.
        :raises ValueError: If the concept id is `None` or
            the concept does not exist.
        """
        if concept.id is None:
            raise ValueError("Concept id must be set")
        cursor = await self._conn.execute(
            "UPDATE concepts SET "
            "front = ?, back = ?, context = ?, "
            "tags = ?, owner_id = ? "
            "WHERE id = ?",
            (
                concept.front,
                concept.back,
                concept.context,
                json.dumps(concept.tags),
                concept.owner_id,
                concept.id,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                f"Concept not found: {concept.id}"
            )
        await self._conn.commit()
        return concept

    async def delete_concept(
        self, concept_id: int,
    ) -> None:
        """Delete a concept by id.

        :param concept_id: The concept identifier.
        :raises ValueError: If the concept does not exist.
        """
        cursor = await self._conn.execute(
            "DELETE FROM concepts WHERE id = ?",
            (concept_id,),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                f"Concept not found: {concept_id}"
            )
        await self._conn.commit()

    # -- Languages ----------------------------------------------------

    async def add_language(
        self, code: str, name: str,
    ) -> Language:
        """Register a new language.

        :param code: ISO 639-1 code (e.g. `"en"`).
        :param name: Human-readable name (e.g. `"English"`).
        :return: The created `Language`.
        :raises ValueError: If the code already exists.
        """
        try:
            await self._conn.execute(
                "INSERT INTO languages (code, name) "
                "VALUES (?, ?)",
                (code, name),
            )
            await self._conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(
                f"Language already exists: {code!r}"
            )
        return Language(code=code, name=name)

    async def get_languages(self) -> list[Language]:
        """Fetch all registered languages.

        :return: List of `Language` models ordered by code.
        """
        cursor = await self._conn.execute(
            "SELECT * FROM languages ORDER BY code",
        )
        rows = await cursor.fetchall()
        return [_row_to_language(r) for r in rows]

    async def get_language(
        self, code: str,
    ) -> Language | None:
        """Fetch a language by code.

        :param code: ISO 639-1 code.
        :return: `Language` or `None` if not found.
        """
        cursor = await self._conn.execute(
            "SELECT * FROM languages WHERE code = ?",
            (code,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_language(row)

    async def delete_language(
        self, code: str,
    ) -> None:
        """Delete a language and all its translations.

        :param code: ISO 639-1 code.
        :raises ValueError: If the language does not exist.
        """
        cursor = await self._conn.execute(
            "DELETE FROM languages WHERE code = ?",
            (code,),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                f"Language not found: {code!r}"
            )
        await self._conn.execute(
            "DELETE FROM concept_translations "
            "WHERE language_code = ?",
            (code,),
        )
        await self._conn.commit()

    # -- Concept Translations -----------------------------------------

    async def add_translation(
        self,
        concept_id: int,
        language_code: str,
        front: str,
        back: str,
        context: str = "",
    ) -> ConceptTranslation:
        """Add a translation for a concept.

        :param concept_id: The concept to translate.
        :param language_code: ISO 639-1 code of the target
            language.
        :param front: Translated prompt.
        :param back: Translated answer.
        :param context: Translated explanation or notes.
        :return: The created `ConceptTranslation`.
        :raises ValueError: If a translation for this
            concept/language pair already exists.
        """
        try:
            await self._conn.execute(
                "INSERT INTO concept_translations "
                "(concept_id, language_code, "
                "front, back, context) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    concept_id, language_code,
                    front, back, context,
                ),
            )
            await self._conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(
                "Translation already exists: "
                f"concept {concept_id}, "
                f"language {language_code!r}"
            )
        return ConceptTranslation(
            concept_id=concept_id,
            language_code=language_code,
            front=front,
            back=back,
            context=context,
        )

    async def get_translations(
        self, concept_id: int,
    ) -> list[ConceptTranslation]:
        """Fetch all translations for a concept.

        :param concept_id: The concept identifier.
        :return: List of `ConceptTranslation` models.
        """
        cursor = await self._conn.execute(
            "SELECT * FROM concept_translations "
            "WHERE concept_id = ? "
            "ORDER BY language_code",
            (concept_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_translation(r) for r in rows]

    async def get_translation(
        self,
        concept_id: int,
        language_code: str,
    ) -> ConceptTranslation | None:
        """Fetch a single translation.

        :param concept_id: The concept identifier.
        :param language_code: ISO 639-1 code.
        :return: `ConceptTranslation` or `None`.
        """
        cursor = await self._conn.execute(
            "SELECT * FROM concept_translations "
            "WHERE concept_id = ? "
            "AND language_code = ?",
            (concept_id, language_code),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_translation(row)

    async def update_translation(
        self, translation: ConceptTranslation,
    ) -> ConceptTranslation:
        """Update an existing translation.

        :param translation: The translation with updated
            fields.
        :return: The updated `ConceptTranslation`.
        :raises ValueError: If the translation does not
            exist.
        """
        cursor = await self._conn.execute(
            "UPDATE concept_translations "
            "SET front = ?, back = ?, context = ? "
            "WHERE concept_id = ? "
            "AND language_code = ?",
            (
                translation.front,
                translation.back,
                translation.context,
                translation.concept_id,
                translation.language_code,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                "Translation not found: "
                f"concept {translation.concept_id}, "
                f"language "
                f"{translation.language_code!r}"
            )
        await self._conn.commit()
        return translation

    async def delete_translation(
        self,
        concept_id: int,
        language_code: str,
    ) -> None:
        """Delete a translation.

        :param concept_id: The concept identifier.
        :param language_code: ISO 639-1 code.
        :raises ValueError: If the translation does not
            exist.
        """
        cursor = await self._conn.execute(
            "DELETE FROM concept_translations "
            "WHERE concept_id = ? "
            "AND language_code = ?",
            (concept_id, language_code),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                "Translation not found: "
                f"concept {concept_id}, "
                f"language {language_code!r}"
            )
        await self._conn.commit()

    # -- Progress -----------------------------------------------------

    async def get_progress(
        self,
        user_id: int,
        concept_id: int,
    ) -> UserProgress | None:
        """Fetch progress for a user-concept pair.

        :param user_id: The user's database id.
        :param concept_id: The concept identifier.
        :return: `UserProgress` or `None` if no record
            exists.
        """
        cursor = await self._conn.execute(
            "SELECT * FROM progress "
            "WHERE user_id = ? AND concept_id = ?",
            (user_id, concept_id),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_progress(row)

    async def get_all_progress(
        self,
        user_id: int,
        concept_ids: list[int],
    ) -> dict[int, UserProgress]:
        """Fetch progress for multiple concepts in one query.

        :param user_id: The user's database id.
        :param concept_ids: List of concept identifiers.
        :return: Dict mapping `concept_id` to `UserProgress`
            for concepts that have a progress record.
        """
        if not concept_ids:
            return {}
        cursor = await self._conn.execute(
            "SELECT * FROM progress "
            "WHERE user_id = ? "
            "AND concept_id IN "
            f"({_in_clause(concept_ids)})",
            [user_id, *concept_ids],
        )
        rows = await cursor.fetchall()
        return {
            row["concept_id"]: _row_to_progress(row)
            for row in rows
        }

    async def upsert_progress(
        self, progress: UserProgress,
    ) -> None:
        """Insert or update progress for a user-concept pair.

        :param progress: The `UserProgress` to persist.
        """
        await self._conn.execute(
            "INSERT INTO progress "
            "(user_id, concept_id, easiness_factor, "
            " interval, repetitions, next_review, "
            " state, step_index, lapse_count, "
            " stability, difficulty) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, concept_id) "
            "DO UPDATE SET "
            " easiness_factor = excluded.easiness_factor,"
            " interval       = excluded.interval, "
            " repetitions    = excluded.repetitions, "
            " next_review    = excluded.next_review, "
            " state          = excluded.state, "
            " step_index     = excluded.step_index, "
            " lapse_count    = excluded.lapse_count, "
            " stability      = excluded.stability, "
            " difficulty     = excluded.difficulty",
            (
                progress.user_id,
                progress.concept_id,
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

        :param user_id: The user's database id.
        :return: List of progress dicts.
        """
        cursor = await self._conn.execute(
            "SELECT user_id, concept_id, "
            "easiness_factor, "
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
                "concept_id": r["concept_id"],
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

        :param records: List of progress dicts.
        :return: Number of records imported.
        :raises KeyError: If a required key is missing.
        """
        required = {
            "user_id", "concept_id", "easiness_factor",
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
                "(user_id, concept_id, easiness_factor,"
                " interval, repetitions, next_review,"
                " state, step_index, lapse_count,"
                " stability, difficulty)"
                " VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(user_id, concept_id) "
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
                    rec["concept_id"],
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
        concept_id: int,
        exercise_type: str,
        correct: bool,
        quality: int,
    ) -> None:
        """Record a single answer in the history log.

        :param user_id: The user's database id.
        :param concept_id: The concept identifier.
        :param exercise_type: The exercise type string.
        :param correct: Whether the answer was correct.
        :param quality: SM-2 quality score (0-5).
        """
        await self._conn.execute(
            "INSERT INTO answer_history "
            "(user_id, concept_id, exercise_type, "
            " correct, quality) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                user_id, concept_id, exercise_type,
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
            "SELECT id, user_id, concept_id, "
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
                concept_id=r["concept_id"],
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

    async def weak_concepts(
        self,
        user_id: int,
        *,
        tag: str | None = None,
        threshold: float = 0.5,
        min_attempts: int = 3,
        limit: int = 20,
    ) -> list[WeakConcept]:
        """Find concepts the user consistently gets wrong.

        :param user_id: The user's database id.
        :param tag: Optional tag filter.
        :param threshold: Minimum error rate (0.0-1.0).
        :param min_attempts: Minimum answer count.
        :param limit: Maximum results to return.
        :return: List of `WeakConcept`, highest error rate
            first.
        """
        if tag is not None:
            cursor = await self._conn.execute(
                _WEAK_CONCEPTS_TAGGED_SQL,
                (
                    user_id, tag,
                    min_attempts, threshold, limit,
                ),
            )
        else:
            cursor = await self._conn.execute(
                _WEAK_CONCEPTS_SQL,
                (
                    user_id,
                    min_attempts, threshold, limit,
                ),
            )
        rows = await cursor.fetchall()
        return [
            WeakConcept(
                concept=Concept(
                    id=r["id"],
                    front=r["front"],
                    back=r["back"],
                    context=r["context"],
                    tags=json.loads(r["tags"]),
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

    # -- Topics -------------------------------------------------------

    async def _insert_topic_concepts(
        self,
        topic_id: int,
        concept_ids: list[int],
    ) -> None:
        """Insert concept links for a topic.

        :param topic_id: The topic identifier.
        :param concept_ids: Ordered list of concept ids.
        """
        for pos, cid in enumerate(concept_ids):
            await self._conn.execute(
                "INSERT INTO topic_concepts "
                "(topic_id, concept_id, position) "
                "VALUES (?, ?, ?)",
                (topic_id, cid, pos),
            )

    async def add_topic(
        self, topic: Topic,
    ) -> Topic:
        """Insert a topic and link its concepts.

        :param topic: The `Topic` to insert.
        :return: The inserted `Topic` with its assigned id.
        """
        return (await self.add_topics([topic]))[0]

    async def add_topics(
        self, topics: list[Topic],
    ) -> list[Topic]:
        """Bulk-insert topics in a single transaction.

        :param topics: List of `Topic` objects to insert.
        :return: List of inserted `Topic` objects with
            assigned ids.
        """
        result: list[Topic] = []
        for topic in topics:
            cursor = await self._conn.execute(
                "INSERT INTO topics "
                "(title, description, tags, "
                " concept_count) "
                "VALUES (?, ?, ?, ?)",
                (
                    topic.title,
                    topic.description,
                    json.dumps(topic.tags),
                    topic.concept_count,
                ),
            )
            topic_id = cursor.lastrowid
            await self._insert_topic_concepts(
                topic_id, topic.concept_ids,
            )
            result.append(
                topic.model_copy(
                    update={"id": topic_id},
                )
            )
        await self._conn.commit()
        return result

    async def get_topics(
        self,
        *,
        tag: str | None = None,
    ) -> list[Topic]:
        """Return topics, optionally filtered by tag.

        :param tag: Filter by topic tag.
        :return: List of matching `Topic` objects with
            `concept_ids` populated.
        """
        clauses: list[str] = []
        params: list[str] = []
        if tag is not None:
            clauses.append(
                "EXISTS (SELECT 1 FROM json_each(tags) "
                "WHERE json_each.value = ?)"
            )
            params.append(tag)
        where = (
            " WHERE " + " AND ".join(clauses)
            if clauses else ""
        )
        cursor = await self._conn.execute(
            "SELECT id, title, description, "
            "tags, concept_count "
            f"FROM topics{where} "
            "ORDER BY id",
            params,
        )
        rows = await cursor.fetchall()
        if not rows:
            return []
        topic_ids = [r["id"] for r in rows]
        cursor = await self._conn.execute(
            "SELECT topic_id, concept_id "
            "FROM topic_concepts "
            "WHERE topic_id "
            f"IN ({_in_clause(topic_ids)}) "
            "ORDER BY position",
            topic_ids,
        )
        tc_rows = await cursor.fetchall()
        concept_map: dict[int, list[int]] = {}
        for tc in tc_rows:
            concept_map.setdefault(
                tc["topic_id"], []
            ).append(tc["concept_id"])
        return [
            Topic(
                id=r["id"],
                title=r["title"],
                description=r["description"],
                tags=json.loads(r["tags"]),
                concept_count=r["concept_count"],
                concept_ids=concept_map.get(
                    r["id"], [],
                ),
            )
            for r in rows
        ]

    async def get_topic(
        self, topic_id: int,
    ) -> Topic | None:
        """Fetch a single topic by id.

        :param topic_id: The topic identifier.
        :return: `Topic` with `concept_ids` populated, or
            `None` if not found.
        """
        cursor = await self._conn.execute(
            "SELECT id, title, description, "
            "tags, concept_count "
            "FROM topics WHERE id = ?",
            (topic_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        cursor = await self._conn.execute(
            "SELECT concept_id FROM topic_concepts "
            "WHERE topic_id = ? ORDER BY position",
            (topic_id,),
        )
        concept_rows = await cursor.fetchall()
        return Topic(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            tags=json.loads(row["tags"]),
            concept_count=row["concept_count"],
            concept_ids=[
                r["concept_id"] for r in concept_rows
            ],
        )

    async def update_topic(
        self, topic: Topic,
    ) -> Topic:
        """Update an existing topic and its concept links.

        :param topic: The `Topic` with updated fields.
        :return: The updated `Topic`.
        :raises ValueError: If the topic id is `None` or
            the topic does not exist.
        """
        if topic.id is None:
            raise ValueError("Topic id must be set")
        cursor = await self._conn.execute(
            "UPDATE topics SET "
            "title = ?, description = ?, "
            "tags = ?, concept_count = ? "
            "WHERE id = ?",
            (
                topic.title,
                topic.description,
                json.dumps(topic.tags),
                topic.concept_count,
                topic.id,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                f"Topic not found: {topic.id}"
            )
        await self._conn.execute(
            "DELETE FROM topic_concepts "
            "WHERE topic_id = ?",
            (topic.id,),
        )
        await self._insert_topic_concepts(
            topic.id, topic.concept_ids,
        )
        await self._conn.commit()
        return topic

    async def delete_topic(
        self, topic_id: int,
    ) -> None:
        """Delete a topic and its concept links.

        :param topic_id: The topic identifier.
        :raises ValueError: If the topic does not exist.
        """
        await self._conn.execute(
            "DELETE FROM topic_concepts "
            "WHERE topic_id = ?",
            (topic_id,),
        )
        cursor = await self._conn.execute(
            "DELETE FROM topics WHERE id = ?",
            (topic_id,),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                f"Topic not found: {topic_id}"
            )
        await self._conn.commit()

    async def save_session_snapshot(
        self,
        snapshot: SessionSnapshot,
        key: str = "",
    ) -> None:
        """Persist a session snapshot.

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

    async def save_conversation_state(
        self,
        state: ConversationState,
    ) -> None:
        """Persist a conversation state.

        :param state: The conversation state to save.
        """
        await self._conn.execute(
            "INSERT OR REPLACE INTO conversation_states "
            "(user_id, key, stage, data, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                state.user_id,
                state.key,
                state.stage.value,
                json.dumps(state.data),
                state.updated_at.strftime(_ISO_FMT),
            ),
        )
        await self._conn.commit()

    async def get_conversation_state(
        self,
        user_id: int,
        key: str = "",
    ) -> ConversationState | None:
        """Load a conversation state.

        :param user_id: The user's database id.
        :param key: Conversation key (e.g. a chat id).
        :return: The `ConversationState`, or `None` if
            none exists.
        """
        cursor = await self._conn.execute(
            "SELECT user_id, key, stage, data, "
            "updated_at "
            "FROM conversation_states "
            "WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return ConversationState(
            user_id=row["user_id"],
            key=row["key"],
            stage=ConversationStage(row["stage"]),
            data=json.loads(row["data"]),
            updated_at=datetime.fromisoformat(
                row["updated_at"],
            ),
        )

    async def delete_conversation_state(
        self,
        user_id: int,
        key: str = "",
    ) -> bool:
        """Delete a conversation state.

        :param user_id: The user's database id.
        :param key: Conversation key (e.g. a chat id).
        :return: `True` if a state was deleted,
            `False` if none existed.
        """
        cursor = await self._conn.execute(
            "DELETE FROM conversation_states "
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


async def import_concepts_csv(
    db: "Database",
    path: str | Path,
    *,
    front_col: str = "front",
    back_col: str = "back",
    delimiter: str | None = None,
    owner_id: int | None = None,
) -> list[Concept]:
    """Import concepts from a CSV or TSV file.

    The file must have a header row. The `front_col` and
    `back_col` columns are required. Optional columns
    (`context`, `tags`) are read when present.

    The `tags` column, if present, should contain a
    comma-separated list of tags (e.g. `"math,calculus"`).

    :param db: The database to import into.
    :param path: Path to the CSV/TSV file.
    :param front_col: Column name for the prompt.
    :param back_col: Column name for the answer.
    :param delimiter: Field delimiter. When `None`,
        auto-detected from the file extension (`.tsv` → tab,
        `.csv` and others → comma).
    :param owner_id: Owner id for imported concepts.
    :return: List of inserted `Concept` objects with assigned
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
        for col in (front_col, back_col):
            if col not in fields:
                raise ValueError(
                    f"Required column {col!r} not found "
                    f"in {path.name}. "
                    f"Available: {fields}"
                )
        concepts: list[Concept] = []
        for row in reader:
            tags_raw = row.get("tags", "")
            tags = (
                [t.strip() for t in tags_raw.split(",")
                 if t.strip()]
                if tags_raw else []
            )
            concepts.append(Concept(
                front=row[front_col],
                back=row[back_col],
                context=row.get("context", ""),
                tags=tags,
                owner_id=owner_id,
            ))
    return await db.add_concepts(concepts)
