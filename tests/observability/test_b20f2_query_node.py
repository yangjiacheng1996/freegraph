# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · US3：节点名精确匹配（含模型 / 工具子 span 与 record）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from freegraph.contracts import TraceQuery
from freegraph.observability import FileTraceStore, SqliteTraceStore

from .conftest import assert_rows_equal, make_record, make_span, seed_events


def _seed(store: object) -> None:
    node_b = make_span(id="b-span", name="b", run_id="r1", node="b")
    model_b = make_span(id="b-model", name="chat", run_id="r1", node="b")
    tool_b = make_span(id="b-tool", name="tool", run_id="r1", node="b")
    node_a = make_span(id="a-span", name="a", run_id="r1", node="a")
    node_c = make_span(id="c-span", name="c", run_id="r1", node="c")
    record_b = make_record(
        span_id="b-span", run_id="r1", node="b", task_id="b:TaskId", superstep=1
    )
    seed_events(
        store,  # type: ignore[arg-type]
        spans=(node_b, model_b, tool_b, node_a, node_c),
        records=(record_b,),
    )


def test_node_exact_match_is_case_sensitive_and_not_substring(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed(store)
    assert store.query(TraceQuery(node="B")) == []
    assert store.query(TraceQuery(node="bb")) == []
    rows = store.query(TraceQuery(node="b"))
    assert {row["node"] for row in rows} == {"b"}


def test_node_filter_returns_children_and_record(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed(store)
    rows = store.query(TraceQuery(node="b"))
    ids = {row.get("id") for row in rows if row["kind"] == "span"}
    assert ids == {"b-span", "b-model", "b-tool"}
    records = [row for row in rows if row["kind"] == "trace_record"]
    assert len(records) == 1
    assert records[0]["task_id"] == "b:TaskId"


def test_other_nodes_are_not_returned(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed(store)
    rows = store.query(TraceQuery(node="b"))
    assert all(row["node"] == "b" for row in rows)
    assert not any(row.get("id") in {"a-span", "c-span"} for row in rows)


def test_task_id_superstep_checkpoint_id_are_not_filters() -> None:
    with pytest.raises(TypeError):
        TraceQuery(task_id="b")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        TraceQuery(superstep=1)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        TraceQuery(checkpoint_id="cp")  # type: ignore[call-arg]


def test_fan_out_task_id_still_matches_node(tmp_path: Path) -> None:
    store = FileTraceStore(tmp_path / "traces")
    _seed(store)
    records = [row for row in store.query(TraceQuery(node="b")) if row["kind"] == "trace_record"]
    assert len(records) == 1
    assert records[0]["task_id"] == "b:TaskId"
    assert records[0]["node"] == "b"


def test_both_backends_agree_on_node_filter(tmp_path: Path) -> None:
    jsonl = FileTraceStore(tmp_path / "traces")
    sqlite = SqliteTraceStore(tmp_path / "traces.sqlite3")
    _seed(jsonl)
    _seed(sqlite)
    assert_rows_equal(jsonl.query(TraceQuery(node="b")), sqlite.query(TraceQuery(node="b")))
