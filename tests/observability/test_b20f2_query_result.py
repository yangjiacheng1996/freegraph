# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · US4：稳定排序 / JSON 断言 / 独立副本 / 容错结果面。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from freegraph.contracts import TraceQuery
from freegraph.observability import FileTraceStore, SqliteTraceStore

from .conftest import make_record, make_span, query_by_kind

T0 = "2026-11-21T12:00:00.000000000+00:00"
T1 = "2026-11-21T12:00:01.000000000+00:00"


def _is_pure(value: Any) -> bool:
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, list):
        return all(_is_pure(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_pure(item) for key, item in value.items())
    return False


def _seed_sorting(store: object) -> None:
    spans = (
        make_span(id="b", run_id="r2", node="b", start_time=T1),
        make_span(id="a", run_id="r1", node="a", start_time=T1),
        make_span(id="c", run_id="r1", node="c", start_time=T0),
        make_span(id="d", run_id="r1", node="d", start_time=T0),
    )
    records = (
        make_record(span_id="c", run_id="r1", node="c", superstep=0),
        make_record(span_id="missing-u2", run_id="r1", node="u", superstep=2),
        make_record(span_id="missing-u1", run_id="r1", node="u", superstep=1),
    )
    for record in records:
        store.on_trace_record(record)  # type: ignore[attr-defined]
    for span in spans:
        store.on_span_end(span)  # type: ignore[attr-defined]


def test_sorting_keys_and_record_before_span(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed_sorting(store)
    rows = store.query()
    keys = [
        (row["kind"], row.get("id") or row.get("span_id"), row["run_id"]) for row in rows
    ]
    assert keys == [
        ("trace_record", "c", "r1"),
        ("span", "c", "r1"),
        ("span", "d", "r1"),
        ("span", "a", "r1"),
        ("span", "b", "r2"),
        ("trace_record", "missing-u1", "r1"),
        ("trace_record", "missing-u2", "r1"),
    ]


def test_repeated_query_is_stable(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed_sorting(store)
    assert store.query() == store.query()
    assert store.query(TraceQuery(run_id="r1")) == store.query(TraceQuery(run_id="r1"))


def test_caller_mutation_does_not_affect_next_query(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed_sorting(store)
    first = store.query()
    first.reverse()
    first[0]["run_id"] = "mutated"
    assert store.query() == store.query()


def test_json_and_pure_data_for_both_backends(tmp_path: Path) -> None:
    jsonl = FileTraceStore(tmp_path / "traces")
    sqlite = SqliteTraceStore(tmp_path / "traces.sqlite3")
    for store in (jsonl, sqlite):
        _seed_sorting(store)
        rows = store.query()
        assert json.loads(json.dumps(rows)) == rows
        assert all(_is_pure(row) for row in rows)


def test_count_model_spans_for_ci_assertion(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    store.on_span_end(make_span(id="m1", name="chat", run_id="r1", node="a"))
    store.on_span_end(make_span(id="m2", name="chat", run_id="r1", node="b"))
    store.on_span_end(make_span(id="other", name="tool", run_id="r1", node="c"))
    rows = store.query(TraceQuery(run_id="r1"))
    assert len([row for row in rows if row["kind"] == "span" and row["name"] == "chat"]) == 2


def test_extra_fields_are_dropped_and_unknown_kind_is_skipped(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    target.mkdir()
    span_row = {
        "kind": "span",
        "id": "s1",
        "name": "a",
        "attributes": {},
        "parent": None,
        "start_time": T0,
        "end_time": T0,
        "context": {},
        "thread_id": "t-1",
        "run_id": "r1",
        "node": "a",
        "checkpoint_id": None,
        "extra": "drop-me",
    }
    unknown = {"kind": "future", "payload": True}
    (target / "trace-r1.jsonl").write_text(
        json.dumps(span_row) + "\n" + json.dumps(unknown) + "\n", encoding="utf-8"
    )
    rows = FileTraceStore(target).query()
    assert len(rows) == 1
    assert rows[0]["kind"] == "span"
    assert "extra" not in rows[0]
    assert query_by_kind(rows, "future") == []
