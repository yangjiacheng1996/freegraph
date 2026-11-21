# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · US5：``SqliteTraceStore`` 写侧（与 B20F1 同语义）。"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pytest

from freegraph.observability import SqliteTraceStore

from .conftest import make_record, make_span

SPAN_FIELDS = {
    "kind",
    "id",
    "name",
    "attributes",
    "parent",
    "start_time",
    "end_time",
    "context",
    "thread_id",
    "run_id",
    "node",
    "checkpoint_id",
}

RECORD_FIELDS = {
    "kind",
    "span_id",
    "task_id",
    "run_id",
    "thread_id",
    "checkpoint_id",
    "node",
    "superstep",
    "triggers",
    "concurrency_group",
    "barrier_groups",
    "input_state",
    "output_state",
    "error",
}


def test_constructor_has_no_side_effect(tmp_path: Path) -> None:
    target = tmp_path / "never" / "traces.sqlite3"
    SqliteTraceStore(target)
    assert not target.parent.exists()


def test_on_span_start_writes_nothing(tmp_path: Path) -> None:
    target = tmp_path / "traces.sqlite3"
    store = SqliteTraceStore(target)
    store.on_span_start(make_span(end_time=None))
    assert not target.exists()
    assert store.write_errors == 0
    assert store.current_span() is None


def test_start_snapshot_is_not_written_and_creates_nothing(tmp_path: Path) -> None:
    target = tmp_path / "traces.sqlite3"
    store = SqliteTraceStore(target)
    store.on_span_end(make_span(end_time=None))
    assert not target.exists()
    assert store.query() == []
    assert store.write_errors == 0


def test_span_and_record_rows_have_frozen_field_sets(tmp_path: Path) -> None:
    target = tmp_path / "traces.sqlite3"
    store = SqliteTraceStore(target)
    span = make_span(id="s1", run_id="r1")
    record = make_record(span_id="s1", run_id="r1")
    store.on_trace_record(record)
    store.on_span_end(span)
    rows = store.query()
    assert len(rows) == 2
    span_row = next(row for row in rows if row["kind"] == "span")
    record_row = next(row for row in rows if row["kind"] == "trace_record")
    assert set(span_row) == SPAN_FIELDS
    assert set(record_row) == RECORD_FIELDS
    assert record_row["span_id"] == span_row["id"]


def test_unsafe_run_id_is_rejected_without_file(tmp_path: Path) -> None:
    target = tmp_path / "traces.sqlite3"
    store = SqliteTraceStore(target)
    store.on_span_end(make_span(run_id="bad.id"))
    assert store.write_errors == 1
    assert store.last_error is not None
    assert not target.exists()


def test_append_across_runs(tmp_path: Path) -> None:
    target = tmp_path / "traces.sqlite3"
    store = SqliteTraceStore(target)
    store.on_span_end(make_span(id="a", run_id="run-A"))
    store.on_span_end(make_span(id="b", run_id="run-B"))
    rows = store.query()
    assert {row["run_id"] for row in rows} == {"run-A", "run-B"}


def test_failure_diagnostics_four_ways(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    occupied = tmp_path / "occupied"
    occupied.write_text("occupied", encoding="utf-8")
    errors: list[BaseException] = []
    store = SqliteTraceStore(occupied, on_error=errors.append)
    before = store.write_errors
    with caplog.at_level(logging.WARNING):
        store.on_span_end(make_span(run_id="r1"))
    assert store.write_errors == before + 1
    assert store.last_error and ":" in store.last_error
    assert errors and len(errors) == 1
    assert any("sqlite trace write failed" in record.message for record in caplog.records)


def test_no_retry_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "traces.sqlite3"
    store = SqliteTraceStore(target)
    calls: list[str] = []

    def fake_connect(*args: object, **kwargs: object):
        calls.append(str(args[0]))
        raise sqlite3.OperationalError("boom")

    monkeypatch.setattr(sqlite3, "connect", fake_connect)
    store.on_span_end(make_span(run_id="r1"))
    assert len(calls) == 1
    assert store.write_errors == 1


def test_base_exception_is_not_swallowed(tmp_path: Path) -> None:
    occupied = tmp_path / "occupied"
    occupied.write_text("occupied", encoding="utf-8")

    def on_error(exc: BaseException) -> None:
        raise KeyboardInterrupt("stop")

    store = SqliteTraceStore(occupied, on_error=on_error)
    with pytest.raises(KeyboardInterrupt):
        store.on_span_end(make_span(run_id="r1"))


def test_per_instance_lock_identity(tmp_path: Path) -> None:
    store_a = SqliteTraceStore(tmp_path / "a.sqlite3")
    store_b = SqliteTraceStore(tmp_path / "b.sqlite3")
    assert store_a._lock is not store_b._lock  # noqa: SLF001


def test_same_store_can_write_multiple_runs(tmp_path: Path) -> None:
    target = tmp_path / "traces.sqlite3"
    store = SqliteTraceStore(target)
    for index in range(3):
        store.on_span_end(make_span(id=f"s{index}", run_id=f"r{index}"))
    assert len(store.query()) == 3
    assert store.write_errors == 0
