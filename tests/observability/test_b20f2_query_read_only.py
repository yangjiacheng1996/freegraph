# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · 只读 / 无副作用：缺失存储、目录是文件、哈希不变、不建文件 / 表。"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from freegraph.observability import FileTraceStore, SqliteTraceStore

from .conftest import make_record, make_span


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _store_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.rglob("*") if path.is_file())


def test_missing_directory_and_database_return_empty_without_creating(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "traces"
    database = tmp_path / "missing.sqlite3"
    assert FileTraceStore(directory).query() == []
    assert SqliteTraceStore(database).query() == []
    assert not directory.exists()
    assert not database.exists()


def test_directory_path_that_is_a_regular_file_raises(tmp_path: Path) -> None:
    occupied = tmp_path / "occupied"
    occupied.write_text("keep", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        FileTraceStore(occupied).query()
    assert occupied.read_text(encoding="utf-8") == "keep"
    with pytest.raises(sqlite3.DatabaseError):
        SqliteTraceStore(occupied).query()
    assert occupied.read_text(encoding="utf-8") == "keep"


def test_jsonl_query_preserves_file_hashes(tmp_path: Path) -> None:
    directory = tmp_path / "traces"
    store = FileTraceStore(directory)
    store.on_span_end(make_span(id="s1", run_id="r1"))
    store.on_trace_record(make_record(span_id="s1", run_id="r1"))
    before = {path: _sha(path) for path in _store_files(directory)}
    store.query()
    after = {path: _sha(path) for path in _store_files(directory)}
    assert before == after


def test_sqlite_query_preserves_file_hash(tmp_path: Path) -> None:
    database = tmp_path / "traces.sqlite3"
    store = SqliteTraceStore(database)
    store.on_span_end(make_span(id="s1", run_id="r1"))
    before = _sha(database)
    store.query()
    assert _sha(database) == before


def test_corrupt_jsonl_is_not_modified(tmp_path: Path) -> None:
    directory = tmp_path / "traces"
    directory.mkdir()
    path = directory / "trace-r1.jsonl"
    path.write_text("{bad json\n", encoding="utf-8")
    before = _sha(path)
    assert FileTraceStore(directory).query() == []
    assert _sha(path) == before


def test_incompatible_sqlite_table_is_not_modified(tmp_path: Path) -> None:
    database = tmp_path / "traces.sqlite3"
    connection = sqlite3.connect(str(database))
    try:
        connection.execute("CREATE TABLE trace_entries (seq INTEGER, kind TEXT)")
        connection.commit()
    finally:
        connection.close()
    before = _sha(database)
    assert SqliteTraceStore(database).query() == []
    assert _sha(database) == before


def test_jsonl_query_does_not_follow_symlink_target(tmp_path: Path) -> None:
    directory = tmp_path / "traces"
    directory.mkdir()
    outside = tmp_path / "outside.jsonl"
    outside.write_text(
        json.dumps(
            {
                "kind": "span",
                "id": "outside",
                "name": "a",
                "attributes": {},
                "parent": None,
                "start_time": "2026-11-21T12:00:00.000000000+00:00",
                "end_time": "2026-11-21T12:00:00.000000000+00:00",
                "context": {},
                "thread_id": "t-1",
                "run_id": "r1",
                "node": "a",
                "checkpoint_id": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    before = _sha(outside)
    try:
        (directory / "trace-r1.jsonl").symlink_to(outside)
    except OSError as exc:  # Windows 无符号链接权限
        pytest.skip(f"symlink unsupported: {exc}")
    assert FileTraceStore(directory).query() == []
    assert _sha(outside) == before
