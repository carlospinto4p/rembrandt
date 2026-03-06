"""User registration, authentication, and session tokens.

Demonstrates the user management API: registering users,
authenticating with credentials, creating login sessions,
and validating/revoking session tokens.

Usage::

    uv run python examples/infrastructure/02_user_auth.py
"""

from pathlib import Path

from rembrandt import Database

_DB_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "user_auth.db"
)


def main() -> None:
    # Start fresh each run
    _DB_PATH.unlink(missing_ok=True)
    db = Database(_DB_PATH)

    # --- Register users ---
    alice = db.register_user(
        "alice", "s3cret", display_name="Alice",
    )
    bob = db.register_user("bob", "hunter2")
    print(f"Registered: {alice.username} (id={alice.id})")
    print(f"Registered: {bob.username} (id={bob.id})")

    # --- Authenticate ---
    user = db.authenticate_user("alice", "s3cret")
    print(f"\nLogin OK: {user.username}" if user else "FAIL")

    bad = db.authenticate_user("alice", "wrong")
    print(f"Bad password: {'rejected' if bad is None else 'BUG'}")

    # --- Session tokens ---
    session = db.create_session(alice.id, ttl_hours=1)
    print(f"\nSession token: {session.token[:16]}...")
    print(f"Expires at: {session.expires_at:%Y-%m-%d %H:%M}")

    # Validate token
    found = db.get_session(session.token)
    print(f"Token valid: {found is not None}")

    # Revoke token
    db.delete_session(session.token)
    found = db.get_session(session.token)
    print(f"After revoke: {found is None}")

    # Bulk revoke
    s1 = db.create_session(bob.id)
    s2 = db.create_session(bob.id)
    db.delete_user_sessions(bob.id)
    print(
        f"\nBulk revoke Bob's sessions: "
        f"{db.get_session(s1.token) is None and db.get_session(s2.token) is None}"
    )

    db.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
