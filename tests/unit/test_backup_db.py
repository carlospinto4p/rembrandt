"""Tests for the empty/shrink backup guard in scripts/backup_db.py."""

import importlib.util
import os
import sqlite3
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "backup_db.py"


def _load():
    spec = importlib.util.spec_from_file_location("backup_db", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_sqlite(path: Path, rows: int = 50) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    conn.executemany(
        "INSERT INTO t (v) VALUES (?)", [(f"row-{i}",) for i in range(rows)]
    )
    conn.commit()
    conn.close()


def test_backup_one_writes_snapshot(tmp_path):
    mod = _load()
    src = tmp_path / "data.db"
    _make_sqlite(src)
    out = mod.backup_one(src, tmp_path / "dest")
    assert out.stat().st_size > 0


def test_backup_one_refuses_missing_source(tmp_path):
    mod = _load()
    with pytest.raises(SystemExit):
        mod.backup_one(tmp_path / "nope.db", tmp_path / "dest")


def test_backup_one_refuses_empty_source(tmp_path):
    mod = _load()
    src = tmp_path / "empty.db"
    src.touch()
    with pytest.raises(SystemExit):
        mod.backup_one(src, tmp_path / "dest")


def test_backup_one_refuses_shrink_and_preserves_backup(tmp_path):
    mod = _load()
    src = tmp_path / "data.db"
    _make_sqlite(src, rows=5)
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    existing = dest_dir / "data.db"
    existing.write_bytes(b"x" * 5_000_000)
    with pytest.raises(SystemExit):
        mod.backup_one(src, dest_dir)
    assert existing.stat().st_size == 5_000_000
    assert not (dest_dir / "data.db.tmp").exists()


def test_backup_one_refuses_even_slightly_smaller(tmp_path):
    mod = _load()
    src = tmp_path / "data.db"
    _make_sqlite(src, rows=50)
    snap = mod.backup_one(src, tmp_path / "probe").stat().st_size
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    existing = dest_dir / "data.db"
    existing.write_bytes(b"x" * (snap + 1))  # one byte larger
    with pytest.raises(SystemExit):
        mod.backup_one(src, dest_dir)
    assert existing.stat().st_size == snap + 1


def test_backup_one_allow_shrink_overwrites(tmp_path):
    mod = _load()
    src = tmp_path / "data.db"
    _make_sqlite(src, rows=5)
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    (dest_dir / "data.db").write_bytes(b"x" * 5_000_000)
    out = mod.backup_one(src, dest_dir, allow_shrink=True)
    assert out.stat().st_size < 5_000_000


# ── temp-file naming and sweep ────────────────────────────────────────


def test_backup_one_leaves_no_temp_file(tmp_path):
    mod = _load()
    src = tmp_path / "data.db"
    _make_sqlite(src)
    dest_dir = tmp_path / "dest"
    mod.backup_one(src, dest_dir)
    assert list(dest_dir.glob("*.tmp")) == []


def test_tmp_sibling_carries_the_pid(tmp_path):
    """Two runs backing up one database must not share a temp file."""
    mod = _load()
    dest = tmp_path / "data.db"
    assert mod._tmp_sibling(dest) == tmp_path / f"data.db.{os.getpid()}.tmp"


def test_sweep_removes_stale_sibling(tmp_path):
    mod = _load()
    dest = tmp_path / "data.db"
    stale = tmp_path / "data.db.999.tmp"
    stale.write_text("abandoned")
    os.utime(stale, (0, 0))
    mod._sweep_stale_tmp(dest, mod._tmp_sibling(dest))
    assert not stale.exists()


def test_sweep_removes_stale_legacy_fixed_name(tmp_path):
    """The old `<dest>.tmp` form has no reclaimer once every run writes
    a pid-suffixed name."""
    mod = _load()
    dest = tmp_path / "data.db"
    legacy = tmp_path / "data.db.tmp"
    legacy.write_text("abandoned")
    os.utime(legacy, (0, 0))
    mod._sweep_stale_tmp(dest, mod._tmp_sibling(dest))
    assert not legacy.exists()


def test_sweep_keeps_a_fresh_sibling(tmp_path):
    """A concurrent run's temp file is not stale, and deleting it would
    break the collision this naming prevents."""
    mod = _load()
    dest = tmp_path / "data.db"
    live = tmp_path / "data.db.999.tmp"
    live.write_text("in progress")
    mod._sweep_stale_tmp(dest, mod._tmp_sibling(dest))
    assert live.exists()


def test_sweep_leaves_the_destination_alone(tmp_path):
    mod = _load()
    dest = tmp_path / "data.db"
    dest.write_text("the backup")
    os.utime(dest, (0, 0))
    mod._sweep_stale_tmp(dest, mod._tmp_sibling(dest))
    assert dest.read_text() == "the backup"
