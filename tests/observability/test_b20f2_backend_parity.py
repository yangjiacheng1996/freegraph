# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · US5 / A6 / SC-006：JSONL 与 SQLite 对同一查询逐条等价。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from freegraph.contracts import TraceQuery
from freegraph.observability import FileTraceStore, SqliteTraceStore

from .conftest import (
    assert_rows_equal,
    make_record,
    make_span,
    query_by_kind,
    seed_events,
)

T0 = "2026-11-21T12:00:00.000000000+00:00"
T1 = "2026-11-21T12:00:01.000000000+00:00"
T2 = "2026-11-21T12:00:02.000000000+00:00"


def _seed(store: object) -> None:
    spans = (
        make_span(id="a1", name="a", run_id="run-A", node="a", thread_id="t-1", start_time=T0),
        make_span(id="a2", name="chat", run_id="run-A", node="a", thread_id="t-1", start_time=T1),
        make_span(id="b1", name="b", run_id="run-B", node="b", thread_id="t-2", start_time=T2),
        make_span(id="start-only", name="a", run_id="run-A", node="a", end_time=None),
    )
    records = (
        make_record(span_id="a1", run_id="run-A", node="a", thread_id="t-1", superstep=0),
        make_record(span_id="a2", run_id="run-A", node="a", thread_id="t-1", superstep=1),
        make_record(span_id="b1", run_id="run-B", node="b", thread_id="t-2", superstep=0),
        make_record(
            span_id="lost",
            run_id="run-A",
            node="a",
            thread_id="t-1",
            superstep=2,
            input_state={"x": 1},
            output_state={"x": 2},
            error=RuntimeError("boom"),
        ),
    )
    seed_events(store, spans=spans, records=records)  # type: ignore[arg-type]


@pytest.fixture
def both(tmp_path: Path) -> tuple[FileTraceStore, SqliteTraceStore]:
    jsonl = FileTraceStore(tmp_path / "traces")
    sqlite = SqliteTraceStore(tmp_path / "traces.sqlite3")
    _seed(jsonl)
    _seed(sqlite)
    return jsonl, sqlite


def test_empty_filter_parity(both: tuple[FileTraceStore, SqliteTraceStore]) -> None:
    jsonl, sqlite = both
    assert_rows_equal(jsonl.query(), sqlite.query())


def test_run_and_thread_parity(both: tuple[FileTraceStore, SqliteTraceStore]) -> None:
    jsonl, sqlite = both
    for query in (TraceQuery(run_id="run-A"), TraceQuery(thread_id="t-2")):
        assert_rows_equal(jsonl.query(query), sqlite.query(query))


def test_node_and_time_parity(both: tuple[FileTraceStore, SqliteTraceStore]) -> None:
    jsonl, sqlite = both
    for query in (
        TraceQuery(node="a"),
        TraceQuery(start_time=T0, end_time=T1),
        TraceQuery(start_time=T2),
    ):
        assert_rows_equal(jsonl.query(query), sqlite.query(query))


def test_combination_parity(both: tuple[FileTraceStore, SqliteTraceStore]) -> None:
    jsonl, sqlite = both
    query = TraceQuery(run_id="run-A", thread_id="t-1", node="a", start_time=T0)
    assert_rows_equal(jsonl.query(query), sqlite.query(query))


def test_json_serialisable_for_both(both: tuple[FileTraceStore, SqliteTraceStore]) -> None:
    jsonl, sqlite = both
    for store in (jsonl, sqlite):
        assert json.loads(json.dumps(store.query())) == store.query()


def test_nested_values_round_trip(both: tuple[FileTraceStore, SqliteTraceStore]) -> None:
    jsonl, sqlite = both
    for store in (jsonl, sqlite):
        rows = store.query(TraceQuery(run_id="run-A"))
        lost = [row for row in query_by_kind(rows, "trace_record") if row["span_id"] == "lost"]
        assert lost[0]["input_state"] == {"x": 1}
        assert lost[0]["output_state"] == {"x": 2}
        assert lost[0]["error"] == {"type": "RuntimeError", "message": "boom"}


def test_start_snapshot_is_ignored_by_both(
    both: tuple[FileTraceStore, SqliteTraceStore],
) -> None:
    jsonl, sqlite = both
    for store in (jsonl, sqlite):
        assert not any(row.get("id") == "start-only" for row in store.query())
