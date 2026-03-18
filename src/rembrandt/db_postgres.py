"""Async PostgreSQL backend for concepts and user progress."""

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta

import psycopg
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Json

from rembrandt.models import (
    AnswerHistory,
    CardState,
    ConversationStage,
    ConversationState,
    Concept,
    DailyStats,
    ReviewForecast,
    SessionSnapshot,
    Topic,
    User,
    UserProgress,
    UserSession,
    WeakConcept,
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

CREATE TABLE IF NOT EXISTS concepts (
    id         SERIAL PRIMARY KEY,
    front      TEXT NOT NULL,
    back       TEXT NOT NULL,
    context    TEXT NOT NULL DEFAULT '',
    tags       JSONB NOT NULL DEFAULT '[]',
    owner_id   INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS progress (
    user_id          INTEGER NOT NULL,
    concept_id       INTEGER NOT NULL,
    easiness_factor  REAL    NOT NULL DEFAULT 2.5,
    interval         INTEGER NOT NULL DEFAULT 0,
    repetitions      INTEGER NOT NULL DEFAULT 0,
    next_review      TIMESTAMP NOT NULL,
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
    id            SERIAL PRIMARY KEY,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    tags          JSONB NOT NULL DEFAULT '[]',
    concept_count INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS topic_concepts (
    topic_id   INTEGER NOT NULL,
    concept_id INTEGER NOT NULL,
    position   INTEGER NOT NULL,
    PRIMARY KEY (topic_id, concept_id),
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    FOREIGN KEY (concept_id) REFERENCES concepts(id)
);

CREATE TABLE IF NOT EXISTS answer_history (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL,
    concept_id    INTEGER NOT NULL,
    exercise_type TEXT    NOT NULL,
    correct       BOOLEAN NOT NULL,
    quality       INTEGER NOT NULL,
    answered_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (concept_id) REFERENCES concepts(id)
);

CREATE TABLE IF NOT EXISTS session_snapshots (
    user_id   INTEGER NOT NULL,
    key       TEXT    NOT NULL DEFAULT '',
    data      TEXT    NOT NULL,
    saved_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, key),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS conversation_states (
    user_id    INTEGER NOT NULL,
    key        TEXT    NOT NULL DEFAULT '',
    stage      TEXT    NOT NULL DEFAULT 'idle',
    data       TEXT    NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, key),
    FOREIGN KEY (user_id) REFERENCES users(id)
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

_WEAK_CONCEPTS_SQL = (
    "SELECT c.id, c.front, c.back, "
    "c.context, c.tags, c.owner_id, "
    "COUNT(*) AS attempts, "
    "SUM(CASE WHEN NOT ah.correct "
    "    THEN 1 ELSE 0 END) AS errors, "
    "MAX(ah.answered_at) AS last_attempt "
    "FROM answer_history ah "
    "JOIN concepts c ON c.id = ah.concept_id "
    "WHERE ah.user_id = %s "
    "GROUP BY c.id, c.front, c.back, "
    "c.context, c.tags, c.owner_id "
    "HAVING COUNT(*) >= %s "
    "AND CAST(SUM(CASE WHEN NOT ah.correct "
    "    THEN 1 ELSE 0 END) AS REAL) "
    "    / COUNT(*) >= %s "
    "ORDER BY CAST(SUM(CASE WHEN NOT ah.correct "
    "    THEN 1 ELSE 0 END) AS REAL) "
    "    / COUNT(*) DESC "
    "LIMIT %s"
)

_WEAK_CONCEPTS_TAGGED_SQL = (
    "SELECT c.id, c.front, c.back, "
    "c.context, c.tags, c.owner_id, "
    "COUNT(*) AS attempts, "
    "SUM(CASE WHEN NOT ah.correct "
    "    THEN 1 ELSE 0 END) AS errors, "
    "MAX(ah.answered_at) AS last_attempt "
    "FROM answer_history ah "
    "JOIN concepts c ON c.id = ah.concept_id "
    "WHERE ah.user_id = %s "
    "AND c.tags @> %s "
    "GROUP BY c.id, c.front, c.back, "
    "c.context, c.tags, c.owner_id "
    "HAVING COUNT(*) >= %s "
    "AND CAST(SUM(CASE WHEN NOT ah.correct "
    "    THEN 1 ELSE 0 END) AS REAL) "
    "    / COUNT(*) >= %s "
    "ORDER BY CAST(SUM(CASE WHEN NOT ah.correct "
    "    THEN 1 ELSE 0 END) AS REAL) "
    "    / COUNT(*) DESC "
    "LIMIT %s"
)


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


def _row_to_concept(r: dict) -> Concept:
    """Convert a PostgreSQL row to a `Concept` model."""
    tags = r["tags"]
    if isinstance(tags, str):
        tags = json.loads(tags)
    return Concept(
        id=r["id"],
        front=r["front"],
        back=r["back"],
        context=r["context"],
        tags=tags,
        owner_id=r["owner_id"],
    )


class PostgresDatabase:
    """Async PostgreSQL backend for concepts and progress.

    Use the async `connect` classmethod to create instances:

    .. code-block:: python

        db = await PostgresDatabase.connect(dsn)

    :param conn: An open `AsyncConnection`.
    """

    def __init__(
        self, conn: AsyncConnection,
    ) -> None:
        self._conn = conn

    @classmethod
    async def connect(
        cls, dsn: str,
    ) -> "PostgresDatabase":
        """Create and initialise a new `PostgresDatabase`.

        :param dsn: PostgreSQL connection string.
        :return: An open `PostgresDatabase` instance.
        """
        conn = await AsyncConnection.connect(
            dsn, row_factory=dict_row, autocommit=True,
        )
        for stmt in _PG_SCHEMA.split(";"):
            stmt = stmt.strip()
            if stmt:
                await conn.execute(stmt)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_progress_user_state "
            "ON progress(user_id, state)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_answer_user_concept "
            "ON answer_history(user_id, concept_id)"
        )
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
        :param password: Plain-text password.
        :param display_name: Optional display name.
        :return: The created `User`.
        :raises ValueError: If the username already exists.
        """
        pw_hash = _hash_password(password)
        try:
            row = await (await self._conn.execute(
                "INSERT INTO users "
                "(username, display_name, password_hash) "
                "VALUES (%s, %s, %s) RETURNING id",
                (username, display_name, pw_hash),
            )).fetchone()
        except psycopg.errors.UniqueViolation:
            raise ValueError(
                f"Username already exists: {username!r}"
            )
        return User(
            id=row["id"],
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
        row = await (await self._conn.execute(
            "SELECT * FROM users WHERE username = %s",
            (username,),
        )).fetchone()
        if row is None:
            return None
        return User(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            password_hash=row["password_hash"],
            created_at=row["created_at"],
        )

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
        row = await (await self._conn.execute(
            "INSERT INTO user_sessions "
            "(user_id, token, created_at, expires_at) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (user_id, token, now, expires),
        )).fetchone()
        return UserSession(
            id=row["id"],
            user_id=user_id,
            token=token,
            created_at=now,
            expires_at=expires,
        )

    async def get_session(
        self, token: str,
    ) -> UserSession | None:
        """Fetch a session by token.

        :param token: The session token.
        :return: `UserSession` or `None`.
        """
        row = await (await self._conn.execute(
            "SELECT * FROM user_sessions "
            "WHERE token = %s",
            (token,),
        )).fetchone()
        if row is None:
            return None
        session = UserSession(
            id=row["id"],
            user_id=row["user_id"],
            token=row["token"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )
        if session.expires_at <= datetime.now():
            return None
        return session

    async def delete_session(
        self, token: str,
    ) -> None:
        """Delete a single session by token."""
        await self._conn.execute(
            "DELETE FROM user_sessions "
            "WHERE token = %s",
            (token,),
        )

    async def delete_user_sessions(
        self, user_id: int,
    ) -> None:
        """Delete all sessions for a user."""
        await self._conn.execute(
            "DELETE FROM user_sessions "
            "WHERE user_id = %s",
            (user_id,),
        )

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
        """Insert a single concept.

        :param front: The prompt shown to the learner.
        :param back: The expected answer.
        :param context: Optional explanation or notes.
        :param tags: Grouping tags.
        :param owner_id: User who owns this concept.
        :return: The inserted `Concept` with its assigned id.
        """
        tags = tags or []
        row = await (await self._conn.execute(
            "INSERT INTO concepts "
            "(front, back, context, tags, owner_id) "
            "VALUES (%s, %s, %s, %s, %s) "
            "RETURNING id",
            (
                front, back, context,
                Json(tags), owner_id,
            ),
        )).fetchone()
        return Concept(
            id=row["id"],
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
        """Bulk-insert concepts.

        :param concepts: List of `Concept` objects to insert.
        :return: List of inserted `Concept` objects with
            assigned ids.
        """
        result: list[Concept] = []
        for c in concepts:
            row = await (await self._conn.execute(
                "INSERT INTO concepts "
                "(front, back, context, tags, owner_id)"
                " VALUES (%s, %s, %s, %s, %s) "
                "RETURNING id",
                (
                    c.front, c.back, c.context,
                    Json(c.tags), c.owner_id,
                ),
            )).fetchone()
            result.append(
                c.model_copy(
                    update={"id": row["id"]},
                )
            )
        return result

    async def get_concepts(
        self,
        *,
        tag: str | None = None,
        owner_id: int | None = None,
    ) -> list[Concept]:
        """Return concepts, optionally filtered by tag.

        :param tag: Filter by tag.
        :param owner_id: Filter to shared + this user's
            concepts.
        :return: List of matching `Concept` objects.
        """
        clauses: list[str] = []
        params: list = []
        if tag is not None:
            clauses.append("tags @> %s")
            params.append(Json([tag]))
        if owner_id is not None:
            clauses.append(
                "(owner_id IS NULL OR owner_id = %s)"
            )
            params.append(owner_id)
        sql = (
            "SELECT id, front, back, context, "
            "tags, owner_id FROM concepts"
        )
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        rows = await (await self._conn.execute(
            sql, params,
        )).fetchall()
        return [_row_to_concept(r) for r in rows]

    async def update_concept(
        self, concept: Concept,
    ) -> Concept:
        """Update an existing concept.

        :param concept: The `Concept` with updated fields.
        :return: The updated `Concept`.
        :raises ValueError: If the concept id is `None` or
            the concept does not exist.
        """
        if concept.id is None:
            raise ValueError("Concept id must be set")
        result = await self._conn.execute(
            "UPDATE concepts SET "
            "front = %s, back = %s, context = %s, "
            "tags = %s, owner_id = %s "
            "WHERE id = %s",
            (
                concept.front,
                concept.back,
                concept.context,
                Json(concept.tags),
                concept.owner_id,
                concept.id,
            ),
        )
        if result.rowcount == 0:
            raise ValueError(
                f"Concept not found: {concept.id}"
            )
        return concept

    async def delete_concept(
        self, concept_id: int,
    ) -> None:
        """Delete a concept by id.

        :param concept_id: The concept identifier.
        :raises ValueError: If the concept does not exist.
        """
        result = await self._conn.execute(
            "DELETE FROM concepts WHERE id = %s",
            (concept_id,),
        )
        if result.rowcount == 0:
            raise ValueError(
                f"Concept not found: {concept_id}"
            )

    # -- Progress -----------------------------------------------------

    async def get_progress(
        self,
        user_id: int,
        concept_id: int,
    ) -> UserProgress | None:
        """Fetch progress for a user-concept pair.

        :param user_id: The user's database id.
        :param concept_id: The concept identifier.
        :return: `UserProgress` or `None`.
        """
        row = await (await self._conn.execute(
            "SELECT * FROM progress "
            "WHERE user_id = %s AND concept_id = %s",
            (user_id, concept_id),
        )).fetchone()
        if row is None:
            return None
        return UserProgress(
            user_id=row["user_id"],
            concept_id=row["concept_id"],
            easiness_factor=row["easiness_factor"],
            interval=row["interval"],
            repetitions=row["repetitions"],
            next_review=row["next_review"],
            state=CardState(row["state"]),
            step_index=row["step_index"],
            lapse_count=row["lapse_count"],
            stability=row.get("stability"),
            difficulty=row.get("difficulty"),
        )

    async def get_all_progress(
        self,
        user_id: int,
        concept_ids: list[int],
    ) -> dict[int, UserProgress]:
        """Fetch progress for multiple concepts.

        :param user_id: The user's database id.
        :param concept_ids: List of concept identifiers.
        :return: Dict mapping `concept_id` to
            `UserProgress`.
        """
        if not concept_ids:
            return {}
        placeholders = ",".join(
            "%s" for _ in concept_ids
        )
        rows = await (await self._conn.execute(
            "SELECT * FROM progress "
            "WHERE user_id = %s "
            f"AND concept_id IN ({placeholders})",
            [user_id, *concept_ids],
        )).fetchall()
        return {
            row["concept_id"]: UserProgress(
                user_id=row["user_id"],
                concept_id=row["concept_id"],
                easiness_factor=row["easiness_factor"],
                interval=row["interval"],
                repetitions=row["repetitions"],
                next_review=row["next_review"],
                state=CardState(row["state"]),
                step_index=row["step_index"],
                lapse_count=row["lapse_count"],
                stability=row.get("stability"),
                difficulty=row.get("difficulty"),
            )
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
            "VALUES "
            "(%s, %s, %s, %s, %s, %s, %s, %s, %s, "
            " %s, %s) "
            "ON CONFLICT(user_id, concept_id) "
            "DO UPDATE SET "
            " easiness_factor = EXCLUDED.easiness_factor,"
            " interval       = EXCLUDED.interval, "
            " repetitions    = EXCLUDED.repetitions, "
            " next_review    = EXCLUDED.next_review, "
            " state          = EXCLUDED.state, "
            " step_index     = EXCLUDED.step_index, "
            " lapse_count    = EXCLUDED.lapse_count, "
            " stability      = EXCLUDED.stability, "
            " difficulty     = EXCLUDED.difficulty",
            (
                progress.user_id,
                progress.concept_id,
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

    async def export_progress(
        self, user_id: int,
    ) -> list[dict]:
        """Export all progress rows for a user as dicts.

        :param user_id: The user's database id.
        :return: List of progress dicts.
        """
        rows = await (await self._conn.execute(
            "SELECT user_id, concept_id, "
            "easiness_factor, "
            "interval, repetitions, next_review, "
            "state, step_index, lapse_count, "
            "stability, difficulty "
            "FROM progress WHERE user_id = %s",
            (user_id,),
        )).fetchall()
        return [
            {
                "user_id": r["user_id"],
                "concept_id": r["concept_id"],
                "easiness_factor": r["easiness_factor"],
                "interval": r["interval"],
                "repetitions": r["repetitions"],
                "next_review": (
                    r["next_review"].isoformat()
                ),
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
            nr = rec["next_review"]
            if isinstance(nr, str):
                nr = datetime.fromisoformat(nr)
            await self._conn.execute(
                "INSERT INTO progress "
                "(user_id, concept_id, easiness_factor,"
                " interval, repetitions, next_review,"
                " state, step_index, lapse_count,"
                " stability, difficulty)"
                " VALUES "
                "(%s, %s, %s, %s, %s, %s, "
                " %s, %s, %s, %s, %s)"
                " ON CONFLICT(user_id, concept_id) "
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
                "  = EXCLUDED.lapse_count, "
                " stability "
                "  = EXCLUDED.stability, "
                " difficulty "
                "  = EXCLUDED.difficulty",
                (
                    rec["user_id"],
                    rec["concept_id"],
                    rec["easiness_factor"],
                    rec["interval"],
                    rec["repetitions"],
                    nr,
                    state,
                    step_index,
                    lapse_count,
                    stability,
                    difficulty,
                ),
            )
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
        """Record a single answer in the history log."""
        await self._conn.execute(
            "INSERT INTO answer_history "
            "(user_id, concept_id, exercise_type, "
            " correct, quality) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                user_id, concept_id, exercise_type,
                correct, quality,
            ),
        )

    async def get_answer_history(
        self,
        user_id: int,
        *,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[AnswerHistory]:
        """Fetch recent answer history for a user."""
        sql = (
            "SELECT id, user_id, concept_id, "
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
        rows = await (await self._conn.execute(
            sql, params,
        )).fetchall()
        return [
            AnswerHistory(
                id=r["id"],
                user_id=r["user_id"],
                concept_id=r["concept_id"],
                exercise_type=r["exercise_type"],
                correct=r["correct"],
                quality=r["quality"],
                answered_at=r["answered_at"],
            )
            for r in rows
        ]

    async def daily_stats(
        self,
        user_id: int,
        *,
        days: int = 30,
    ) -> list[DailyStats]:
        """Aggregate answer history into daily statistics."""
        cutoff = datetime.now() - timedelta(days=days)
        rows = await (await self._conn.execute(
            _DAILY_STATS_SQL, (user_id, cutoff),
        )).fetchall()
        return [
            DailyStats(
                date=r["day"].isoformat(),
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
        """Find concepts the user consistently gets wrong."""
        if tag is not None:
            rows = await (await self._conn.execute(
                _WEAK_CONCEPTS_TAGGED_SQL,
                (
                    user_id, Json([tag]),
                    min_attempts, threshold, limit,
                ),
            )).fetchall()
        else:
            rows = await (await self._conn.execute(
                _WEAK_CONCEPTS_SQL,
                (
                    user_id,
                    min_attempts, threshold, limit,
                ),
            )).fetchall()
        return [
            WeakConcept(
                concept=_row_to_concept(r),
                attempts=r["attempts"],
                errors=r["errors"],
                error_rate=round(
                    r["errors"] / r["attempts"], 2,
                ),
                last_attempt=r["last_attempt"],
            )
            for r in rows
        ]

    async def retention_rate(
        self,
        user_id: int,
        *,
        days: int = 30,
    ) -> float:
        """Calculate the overall retention rate."""
        cutoff = datetime.now() - timedelta(days=days)
        row = await (await self._conn.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN correct THEN 1 ELSE 0 END) "
            "AS correct "
            "FROM answer_history "
            "WHERE user_id = %s AND answered_at >= %s",
            (user_id, cutoff),
        )).fetchone()
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
        """Predict upcoming review workload per day."""
        today = datetime.now().date()
        horizon = today + timedelta(days=days)
        rows = await (await self._conn.execute(
            "SELECT next_review::date AS day, "
            "COUNT(*) AS cnt "
            "FROM progress "
            "WHERE user_id = %s "
            "AND state != %s "
            "AND next_review::date <= %s "
            "GROUP BY day ORDER BY day",
            (
                user_id,
                CardState.SUSPENDED.value,
                horizon,
            ),
        )).fetchall()
        by_day: dict[str, int] = {}
        for r in rows:
            by_day[r["day"].isoformat()] = r["cnt"]
        today_str = today.isoformat()
        result: list[ReviewForecast] = []
        overdue = sum(
            cnt for d, cnt in by_day.items()
            if d < today_str
        )
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

    async def add_topic(
        self, topic: Topic,
    ) -> Topic:
        """Insert a topic and link its concepts."""
        return (await self.add_topics([topic]))[0]

    async def add_topics(
        self, topics: list[Topic],
    ) -> list[Topic]:
        """Bulk-insert topics."""
        result: list[Topic] = []
        for topic in topics:
            row = await (await self._conn.execute(
                "INSERT INTO topics "
                "(title, description, tags, "
                " concept_count) "
                "VALUES (%s, %s, %s, %s) "
                "RETURNING id",
                (
                    topic.title,
                    topic.description,
                    Json(topic.tags),
                    topic.concept_count,
                ),
            )).fetchone()
            topic_id = row["id"]
            for pos, cid in enumerate(
                topic.concept_ids
            ):
                await self._conn.execute(
                    "INSERT INTO topic_concepts "
                    "(topic_id, concept_id, position) "
                    "VALUES (%s, %s, %s)",
                    (topic_id, cid, pos),
                )
            result.append(
                topic.model_copy(
                    update={"id": topic_id},
                )
            )
        return result

    async def get_topics(
        self,
        *,
        tag: str | None = None,
    ) -> list[Topic]:
        """Return topics, optionally filtered by tag."""
        clauses: list[str] = []
        params: list = []
        if tag is not None:
            clauses.append("tags @> %s")
            params.append(Json([tag]))
        where = (
            " WHERE " + " AND ".join(clauses)
            if clauses else ""
        )
        rows = await (await self._conn.execute(
            "SELECT id, title, description, "
            "tags, concept_count "
            f"FROM topics{where} "
            "ORDER BY id",
            params,
        )).fetchall()
        if not rows:
            return []
        topic_ids = [r["id"] for r in rows]
        placeholders = ",".join(
            "%s" for _ in topic_ids
        )
        tc_rows = await (await self._conn.execute(
            "SELECT topic_id, concept_id "
            "FROM topic_concepts "
            f"WHERE topic_id IN ({placeholders}) "
            "ORDER BY position",
            topic_ids,
        )).fetchall()
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
                tags=(
                    r["tags"]
                    if isinstance(r["tags"], list)
                    else json.loads(r["tags"])
                ),
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
        """Fetch a single topic by id."""
        row = await (await self._conn.execute(
            "SELECT id, title, description, "
            "tags, concept_count "
            "FROM topics WHERE id = %s",
            (topic_id,),
        )).fetchone()
        if row is None:
            return None
        tc_rows = await (await self._conn.execute(
            "SELECT concept_id FROM topic_concepts "
            "WHERE topic_id = %s ORDER BY position",
            (topic_id,),
        )).fetchall()
        tags = row["tags"]
        if isinstance(tags, str):
            tags = json.loads(tags)
        return Topic(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            tags=tags,
            concept_count=row["concept_count"],
            concept_ids=[
                r["concept_id"] for r in tc_rows
            ],
        )

    async def update_topic(
        self, topic: Topic,
    ) -> Topic:
        """Update an existing topic."""
        if topic.id is None:
            raise ValueError("Topic id must be set")
        result = await self._conn.execute(
            "UPDATE topics SET "
            "title = %s, description = %s, "
            "tags = %s, concept_count = %s "
            "WHERE id = %s",
            (
                topic.title,
                topic.description,
                Json(topic.tags),
                topic.concept_count,
                topic.id,
            ),
        )
        if result.rowcount == 0:
            raise ValueError(
                f"Topic not found: {topic.id}"
            )
        await self._conn.execute(
            "DELETE FROM topic_concepts "
            "WHERE topic_id = %s",
            (topic.id,),
        )
        for pos, cid in enumerate(topic.concept_ids):
            await self._conn.execute(
                "INSERT INTO topic_concepts "
                "(topic_id, concept_id, position) "
                "VALUES (%s, %s, %s)",
                (topic.id, cid, pos),
            )
        return topic

    async def delete_topic(
        self, topic_id: int,
    ) -> None:
        """Delete a topic and its concept links."""
        await self._conn.execute(
            "DELETE FROM topic_concepts "
            "WHERE topic_id = %s",
            (topic_id,),
        )
        result = await self._conn.execute(
            "DELETE FROM topics WHERE id = %s",
            (topic_id,),
        )
        if result.rowcount == 0:
            raise ValueError(
                f"Topic not found: {topic_id}"
            )

    # -- Session Snapshots / Conversation State -----------------------

    async def save_session_snapshot(
        self,
        snapshot: SessionSnapshot,
        key: str = "",
    ) -> None:
        """Persist a session snapshot."""
        await self._conn.execute(
            "INSERT INTO session_snapshots "
            "(user_id, key, data, saved_at) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT(user_id, key) "
            "DO UPDATE SET "
            "data = EXCLUDED.data, "
            "saved_at = EXCLUDED.saved_at",
            (
                snapshot.user_id,
                key,
                snapshot.model_dump_json(),
                snapshot.saved_at,
            ),
        )

    async def get_session_snapshot(
        self,
        user_id: int,
        key: str = "",
    ) -> SessionSnapshot | None:
        """Load a previously saved session snapshot."""
        row = await (await self._conn.execute(
            "SELECT data FROM session_snapshots "
            "WHERE user_id = %s AND key = %s",
            (user_id, key),
        )).fetchone()
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
        """Delete a saved session snapshot."""
        result = await self._conn.execute(
            "DELETE FROM session_snapshots "
            "WHERE user_id = %s AND key = %s",
            (user_id, key),
        )
        return result.rowcount > 0

    async def save_conversation_state(
        self,
        state: ConversationState,
    ) -> None:
        """Persist a conversation state."""
        await self._conn.execute(
            "INSERT INTO conversation_states "
            "(user_id, key, stage, data, updated_at) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT(user_id, key) "
            "DO UPDATE SET "
            "stage = EXCLUDED.stage, "
            "data = EXCLUDED.data, "
            "updated_at = EXCLUDED.updated_at",
            (
                state.user_id,
                state.key,
                state.stage.value,
                json.dumps(state.data),
                state.updated_at,
            ),
        )

    async def get_conversation_state(
        self,
        user_id: int,
        key: str = "",
    ) -> ConversationState | None:
        """Load a conversation state."""
        row = await (await self._conn.execute(
            "SELECT user_id, key, stage, data, "
            "updated_at "
            "FROM conversation_states "
            "WHERE user_id = %s AND key = %s",
            (user_id, key),
        )).fetchone()
        if row is None:
            return None
        data = row["data"]
        if isinstance(data, str):
            data = json.loads(data)
        return ConversationState(
            user_id=row["user_id"],
            key=row["key"],
            stage=ConversationStage(row["stage"]),
            data=data,
            updated_at=row["updated_at"],
        )

    async def delete_conversation_state(
        self,
        user_id: int,
        key: str = "",
    ) -> bool:
        """Delete a conversation state."""
        result = await self._conn.execute(
            "DELETE FROM conversation_states "
            "WHERE user_id = %s AND key = %s",
            (user_id, key),
        )
        return result.rowcount > 0

    async def close(self) -> None:
        """Close the database connection."""
        await self._conn.close()

    async def __aenter__(self) -> "PostgresDatabase":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()
