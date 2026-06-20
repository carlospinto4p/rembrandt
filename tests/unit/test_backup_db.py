"""Tests for the empty/shrink backup guard in scripts/backup_db.py."""

import importlib.util
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
