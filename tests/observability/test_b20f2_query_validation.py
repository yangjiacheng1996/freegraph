# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · 类型校验 / 时间错误 / 读取前校验。"""

from __future__ import annotations

from pathlib import Path

import pytest

from freegraph.contracts import TraceQuery
from freegraph.observability import FileTraceStore, SqliteTraceStore


def test_query_must_be_trace_query_or_none(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    for bad in ({"run_id": "r1"}, "r1", 1, object()):
        with pytest.raises(TypeError):
            store.query(bad)  # type: ignore[arg-type]


def test_each_field_must_be_str_or_none(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    bad_queries = (
        TraceQuery(run_id=123),  # type: ignore[arg-type]
        TraceQuery(thread_id=123),  # type: ignore[arg-type]
        TraceQuery(node=["b"]),  # type: ignore[arg-type]
        TraceQuery(start_time=123),  # type: ignore[arg-type]
        TraceQuery(end_time=1.2),  # type: ignore[arg-type]
    )
    for query in bad_queries:
        with pytest.raises(TypeError):
            store.query(query)


def test_valid_string_but_bad_time_raises_value_error(tmp_path: Path) -> None:
    for store in (
        FileTraceStore(tmp_path / "traces"),
        SqliteTraceStore(tmp_path / "traces.sqlite3"),
    ):
        with pytest.raises(ValueError):
            store.query(TraceQuery(start_time="not-a-time"))
        with pytest.raises(ValueError):
            store.query(TraceQuery(end_time="2026-99-99T99:99:99Z"))


def test_inverted_range_returns_empty(tmp_path: Path) -> None:
    for store in (
        FileTraceStore(tmp_path / "traces"),
        SqliteTraceStore(tmp_path / "traces.sqlite3"),
    ):
        assert (
            store.query(
                TraceQuery(
                    start_time="2026-11-22T00:00:00Z",
                    end_time="2026-11-21T00:00:00Z",
                )
            )
            == []
        )


def test_validation_happens_before_any_read(tmp_path: Path) -> None:
    occupied = tmp_path / "not-a-directory"
    occupied.write_text("occupied", encoding="utf-8")
    file_store = FileTraceStore(occupied)
    with pytest.raises(TypeError):
        file_store.query({"run_id": "r1"})  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        file_store.query(TraceQuery(start_time="bad-time"))

    database_dir = tmp_path / "db-is-a-directory"
    database_dir.mkdir()
    sqlite_store = SqliteTraceStore(database_dir)
    with pytest.raises(TypeError):
        sqlite_store.query({"run_id": "r1"})  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        sqlite_store.query(TraceQuery(end_time="bad-time"))
