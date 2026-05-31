"""Consistent SQLite snapshot for off-machine backup.

Copies the live rembrandt database to a destination directory using
SQLite's online backup API.  Unlike a plain file copy, the backup API
produces a transactionally consistent snapshot even while a session is
mid-write, and folds any ``-wal`` / ``-shm`` sidecar state into a
single self-contained file.  The snapshot is written to a temporary
file in the destination and then atomically renamed, so Dropbox never
observes a half-written database.

Destination resolution (highest priority first):

1. ``--dest`` CLI flag
2. ``REMBRANDT_BACKUP_DEST`` environment variable
3. Built-in default: ``~/Dropbox/home/development/db/rembrandt``

The default source database is ``data_science.db`` at the project
root.  Pass ``--db`` to override.

Usage::

    uv run python scripts/backup_db.py

    # Custom source
    uv run python scripts/backup_db.py --db /path/to/other.db

    # Custom destination
    REMBRANDT_BACKUP_DEST=/mnt/nas uv run python scripts/backup_db.py
"""

import argparse
import logging
import os
import sqlite3
from pathlib import Path

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_PROJECT_ROOT = Path(__file__).parent.parent

DEFAULT_DB = _PROJECT_ROOT / "data_science.db"

DEFAULT_DEST = (
    Path.home() / "Dropbox" / "home" / "development" / "db" / "rembrandt"
)


def _effective_dest() -> Path:
    env = os.environ.get("REMBRANDT_BACKUP_DEST")
    return Path(env) if env else DEFAULT_DEST


def backup_one(src_path: Path, dest_dir: Path) -> Path:
    """Write a consistent snapshot of one DB into ``dest_dir``.

    :param src_path: Path to the live source database.
    :param dest_dir: Directory to write the snapshot into.
    :return: Path to the written snapshot.
    :raises SystemExit: When the source database does not exist.
    """
    if not src_path.exists():
        raise SystemExit(f"error: source database not found at {src_path}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src_path.name
    tmp = dest.with_name(dest.name + ".tmp")

    src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(tmp))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    os.replace(tmp, dest)
    size = dest.stat().st_size
    logger.info("Snapshot written: %s -> %s (%d bytes)", src_path, dest, size)
    return dest


def _build_parser() -> argparse.ArgumentParser:
    effective = _effective_dest()
    p = argparse.ArgumentParser(
        description=(
            "Write a consistent SQLite snapshot to a backup directory "
            "using the online backup API."
        ),
    )
    p.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"Source database to snapshot (default: {DEFAULT_DB}).",
    )
    p.add_argument(
        "--dest",
        type=Path,
        default=effective,
        help=f"Destination directory (default: {effective}).",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    backup_one(args.db, args.dest)


if __name__ == "__main__":
    main()
