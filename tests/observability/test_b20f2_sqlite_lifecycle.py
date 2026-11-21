# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · SQLite 生命周期 / 权限 / 无持久句柄 / 父目录失败隔离。"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pytest

from freegraph.observability import SqliteTraceStore

from .conftest import file_mode, make_span


def _tables(database: Path) -> set[str]:
    connection = sqlite3.connect(str(database))
    try:
        return {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'index')"
            )
        }
    finally:
        connection.close()


def test_constructor_creates_nothing(tmp_path: Path) -> None:
    database = tmp_path / "deep" / "traces.sqlite3"
    SqliteTraceStore(database)
    assert not database.parent.exists()


def test_first_write_lazily_creates_parents_database_table_and_indexes(
    tmp_path: Path,
) -> None:
    database = tmp_path / "deep" / "nested" / "traces.sqlite3"
    SqliteTraceStore(database).on_span_end(make_span(run_id="r1"))
    assert database.is_file()
    names = _tables(database)
    assert "trace_entries" in names
    assert "idx_trace_run" in names


def test_query_does_not_create_database_or_table(tmp_path: Path) -> None:
    missing = tmp_path / "missing.sqlite3"
    assert SqliteTraceStore(missing).query() == []
    assert not missing.exists()

    empty = tmp_path / "empty.sqlite3"
    sqlite3.connect(str(empty)).close()
    assert SqliteTraceStore(empty).query() == []
    assert "trace_entries" not in _tables(empty)


def test_new_database_mode_is_not_wider_than_owner_only(tmp_path: Path) -> None:
    database = tmp_path / "traces.sqlite3"
    SqliteTraceStore(database).on_span_end(make_span(run_id="r1"))
    mode = file_mode(database)
    if mode is not None:
        assert mode & 0o077 == 0


def test_existing_wider_file_is_not_loosened(tmp_path: Path) -> None:
    database = tmp_path / "traces.sqlite3"
    database.write_text("", encoding="utf-8")
    if file_mode(database) is not None:
        database.chmod(0o666)
    before = file_mode(database)
    SqliteTraceStore(database).on_span_end(make_span(run_id="r1"))
    after = file_mode(database)
    if before is not None and after is not None:
        assert (after & 0o077) & ~(before & 0o077) == 0


def test_no_close_or_context_manager(tmp_path: Path) -> None:
    store = SqliteTraceStore(tmp_path / "traces.sqlite3")
    assert not hasattr(store, "close")
    assert not hasattr(store, "__enter__")
    assert not hasattr(store, "__exit__")


def test_memory_and_uri_are_rejected_at_construction(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        SqliteTraceStore(":memory:")
    with pytest.raises(ValueError):
        SqliteTraceStore("file:traces.sqlite3?mode=memory")


def test_no_persistent_handle_after_write(tmp_path: Path) -> None:
    database = tmp_path / "traces.sqlite3"
    SqliteTraceStore(database).on_span_end(make_span(run_id="r1"))
    database.rename(tmp_path / "renamed.sqlite3")


def test_parent_unwritable_is_isolated(tmp_path: Path) -> None:
    parent = tmp_path / "not-a-directory"
    parent.write_text("occupied", encoding="utf-8")
    database = parent / "traces.sqlite3"
    errors: list[BaseException] = []
    store = SqliteTraceStore(database, on_error=errors.append)
    store.on_span_end(make_span(run_id="r1"))
    assert store.write_errors == 1
    assert store.last_error is not None
    assert len(errors) == 1
    assert not database.exists()


def test_parent_failure_logs_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    parent = tmp_path / "not-a-directory"
    parent.write_text("occupied", encoding="utf-8")
    store = SqliteTraceStore(parent / "traces.sqlite3")
    with caplog.at_level(logging.WARNING):
        store.on_span_end(make_span(run_id="r1"))
    assert any("sqlite trace write failed" in record.message for record in caplog.records)
