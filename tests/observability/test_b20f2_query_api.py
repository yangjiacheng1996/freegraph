# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · US1：``FileTraceStore.query`` 的 run / thread / 空过滤器 / 字段面。"""

from __future__ import annotations

import json
from pathlib import Path

from freegraph.contracts import TraceQuery
from freegraph.observability import FileTraceStore

from .conftest import make_record, make_span, query_by_kind, seed_events

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


def _seed_two_runs(store: FileTraceStore) -> tuple[object, object]:
    span_a = make_span(id="a1", run_id="run-A", node="a", thread_id="t-1")
    span_b = make_span(id="b1", run_id="run-B", node="b", thread_id="t-2")
    record_a = make_record(span_id="a1", run_id="run-A", node="a", thread_id="t-1")
    record_b = make_record(span_id="b1", run_id="run-B", node="b", thread_id="t-2")
    seed_events(store, spans=(span_a, span_b), records=(record_a, record_b))
    return span_a, span_b


def test_empty_filter_and_none_return_all(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed_two_runs(store)
    assert store.query() == store.query(TraceQuery())
    assert len(store.query()) == 4


def test_run_id_filter_returns_only_that_run(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed_two_runs(store)
    rows = store.query(TraceQuery(run_id="run-A"))
    assert {row["run_id"] for row in rows} == {"run-A"}
    assert len(rows) == 2
    assert query_by_kind(rows, "span")[0]["id"] == "a1"


def test_thread_id_filter_returns_only_that_thread(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed_two_runs(store)
    rows = store.query(TraceQuery(thread_id="t-1"))
    assert {row["thread_id"] for row in rows} == {"t-1"}
    assert len(rows) == 2


def test_both_kinds_and_frozen_field_sets(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed_two_runs(store)
    rows = store.query(TraceQuery(run_id="run-A"))
    spans = query_by_kind(rows, "span")
    records = query_by_kind(rows, "trace_record")
    assert len(spans) == 1 and len(records) == 1
    assert set(spans[0]) == SPAN_FIELDS
    assert set(records[0]) == RECORD_FIELDS
    assert records[0]["span_id"] == spans[0]["id"]


def test_result_is_independent_copy(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed_two_runs(store)
    first = store.query()
    first.append({"kind": "span"})
    first[0]["run_id"] = "mutated"
    first[0].clear()
    second = store.query()
    assert len(second) == 4
    assert second[0]["kind"] in {"span", "trace_record"}


def test_result_is_json_serialisable(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed_two_runs(store)
    assert json.loads(json.dumps(store.query()))


def test_none_is_not_the_same_as_empty_string(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed_two_runs(store)
    assert store.query(TraceQuery(run_id="")) == []
    assert store.query(TraceQuery(thread_id="")) == []
    assert store.query(TraceQuery(node="")) == []


def test_unsafe_run_id_filter_values_return_empty(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed_two_runs(store)
    for value in ("", "a.b", "a/b", "../x"):
        assert store.query(TraceQuery(run_id=value)) == []


def test_span_only_storage_has_no_records(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    store.on_span_end(make_span(id="only", run_id="run-only", node="a"))
    rows = store.query()
    assert len(rows) == 1
    assert rows[0]["kind"] == "span"
    assert query_by_kind(rows, "trace_record") == []


def test_thread_id_none_entries_only_match_empty_filter(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    store.on_span_end(make_span(id="n1", run_id="r1", thread_id=None))
    assert len(store.query()) == 1
    assert store.query(TraceQuery(thread_id="t-1")) == []


def test_non_ascii_and_control_characters_round_trip(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    span = make_span(
        id="weird",
        run_id="r1",
        attributes={"键": "值\n带控制\u0001"},
        context={"emoji": "🚀"},
    )
    store.on_span_end(span)
    rows = store.query()
    assert rows[0]["attributes"] == {"键": "值\n带控制\u0001"}
    assert "\\u0001" in json.dumps(rows)
    assert "\n" in rows[0]["attributes"]["键"]
