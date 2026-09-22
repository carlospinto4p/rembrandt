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
import time
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


#: A leftover temp file must be untouched this long before a later run
#: deletes it. A live backup writes continuously, so a day is
#: unmistakably stale.
_STALE_TMP_AGE_S = 86_400


def _tmp_sibling(dest: Path) -> Path:
    """Return this process's private temp path beside *dest*.

    The pid is in the name so two runs backing up the same database
    cannot write the same temp file. That collision broke
    knowledge_graph_news's nightly backup on 2026-09-22, when a retired
    systemd unit was left installed beside its replacement and both ran
    the identical command at 02:00.

    :param dest: Final destination path.
    :return: ``<dest>.<pid>.tmp`` in the destination's directory.
    """
    return dest.with_name(f"{dest.name}.{os.getpid()}.tmp")


def _sweep_stale_tmp(dest: Path, keep: Path) -> None:
    """Delete temp siblings of *dest* left behind by a killed run.

    A per-process temp name is never reused, so nothing reclaims the
    file when a run dies between creating it and renaming it. Covers the
    older fixed ``<dest>.tmp`` form too, which has no reclaimer once
    every run writes a pid-suffixed name. Failures are swallowed: a
    concurrent run may sweep the same file, and cleanup must never fail
    the backup it precedes.

    :param dest: Destination whose temp siblings are considered.
    :param keep: This run's own temp path, never deleted.
    """
    cutoff = time.time() - _STALE_TMP_AGE_S
    candidates = [
        *dest.parent.glob(f"{dest.name}.*.tmp"),
        dest.with_name(dest.name + ".tmp"),
    ]
    for old in candidates:
        if old == keep:
            continue
        try:
            if old.is_file() and old.stat().st_mtime < cutoff:
                old.unlink()
        except OSError:
            continue


def backup_one(
    src_path: Path, dest_dir: Path, *, allow_shrink: bool = False
) -> Path:
    """Write a consistent snapshot of one DB into ``dest_dir``.

    :param src_path: Path to the live source database.
    :param dest_dir: Directory to write the snapshot into.
    :param allow_shrink: Permit a snapshot far smaller than the existing
        backup (off by default) — the override for a legitimate shrink.
    :return: Path to the written snapshot.
    :raises SystemExit: When the source is missing/empty, or the new
        snapshot would dangerously shrink the existing backup.
    """
    if not src_path.exists():
        raise SystemExit(f"error: source database not found at {src_path}")
    if src_path.stat().st_size == 0:
        raise SystemExit(
            f"error: refusing backup — source database is empty: {src_path}"
        )

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src_path.name
    tmp = _tmp_sibling(dest)
    _sweep_stale_tmp(dest, tmp)

    src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(tmp))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    # Guard before the atomic rename: a backup any smaller than the one
    # already saved signals truncation/data loss, so refuse it. Exiting
    # non-zero fires the unit's OnFailure alarm. --allow-shrink overrides.
    new_size = tmp.stat().st_size
    if dest.exists() and dest.stat().st_size:
        old_size = dest.stat().st_size
        if new_size < old_size and not allow_shrink:
            tmp.unlink(missing_ok=True)
            pct = new_size / old_size * 100
            raise SystemExit(
                f"error: refusing backup — new snapshot ({new_size} bytes) "
                f"is smaller than the existing backup ({old_size} bytes) — "
                f"{pct:.1f}% of it — at {dest}. Pass --allow-shrink if the "
                "shrink is expected."
            )

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
    p.add_argument(
        "--allow-shrink",
        action="store_true",
        help="Permit a snapshot far smaller than the existing backup "
        "(needed when the source legitimately shrank).",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    backup_one(args.db, args.dest, allow_shrink=args.allow_shrink)


if __name__ == "__main__":
    main()
