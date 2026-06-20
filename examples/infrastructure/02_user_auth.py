"""User registration, authentication, and session tokens.

Demonstrates the user management API: registering users,
authenticating with credentials, creating login sessions,
and validating/revoking session tokens.

Usage::

    uv run python examples/infrastructure/02_user_auth.py
"""

import asyncio
from pathlib import Path

from rembrandt import Database

_DB_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "user_auth.db"
)


async def main() -> None:
    # Start fresh each run
    _DB_PATH.unlink(missing_ok=True)
    db = await Database.connect(_DB_PATH)

    # --- Register users ---
    alice = await db.register_user(
        "alice",
        "s3cret",
        display_name="Alice",
    )
    bob = await db.register_user(
        "bob",
        "hunter2",
    )
    print(f"Registered: {alice.username} (id={alice.id})")
    print(f"Registered: {bob.username} (id={bob.id})")

    # --- Authenticate ---
    user = await db.authenticate_user(
        "alice",
        "s3cret",
    )
    print(f"\nLogin OK: {user.username}" if user else "FAIL")

    bad = await db.authenticate_user(
        "alice",
        "wrong",
    )
    print(f"Bad password: {'rejected' if bad is None else 'BUG'}")

    # --- Session tokens ---
    session = await db.create_session(
        alice.id,
        ttl_hours=1,
    )
    print(f"\nSession token: {session.token[:16]}...")
    print(f"Expires at: {session.expires_at:%Y-%m-%d %H:%M}")

    # Validate token
    found = await db.get_session(session.token)
    print(f"Token valid: {found is not None}")

    # Revoke token
    await db.delete_session(session.token)
    found = await db.get_session(session.token)
    print(f"After revoke: {found is None}")

    # Bulk revoke
    s1 = await db.create_session(bob.id)
    s2 = await db.create_session(bob.id)
    await db.delete_user_sessions(bob.id)
    r1 = await db.get_session(s1.token)
    r2 = await db.get_session(s2.token)
    print(f"\nBulk revoke Bob's sessions: {r1 is None and r2 is None}")

    await db.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
