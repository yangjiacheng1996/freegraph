# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · US2：JSONL 可读性 / 编码 / 转义 / 行序。"""

from __future__ import annotations

import json
from pathlib import Path

from freegraph.observability import FileTraceStore

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


def test_file_is_utf8_lf_without_bom_or_header(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    store.on_span_end(make_span())
    raw = next(target.glob("trace-*.jsonl")).read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert raw.endswith(b"\n")
    assert b"\r\n" not in raw
    assert raw.count(b"\n") == 1


def test_every_line_is_one_json_object_with_only_locked_kinds(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    span = make_span()
    store.on_trace_record(make_record(span_id=span.id))
    store.on_span_end(span)

    text = next(target.glob("trace-*.jsonl")).read_text(encoding="utf-8")
    lines = text.splitlines()
    assert all(line for line in lines)
    objs = [json.loads(line) for line in lines]
    assert [obj["kind"] for obj in objs] == ["trace_record", "span"]
    assert set(objs[0]) == RECORD_FIELDS
    assert set(objs[1]) == SPAN_FIELDS


def test_unicode_and_control_characters_stay_on_one_line(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    span = make_span(
        attributes={"text": "中文\n引号\"控制\x01"},
        context={"note": "换行\n与制表\t"},
    )
    record = make_record(
        span_id=span.id,
        input_state={"text": "中文\n输入"},
        output_state={"text": "中文\n输出"},
    )
    store.on_trace_record(record)
    store.on_span_end(span)

    path = next(target.glob("trace-*.jsonl"))
    text = path.read_text(encoding="utf-8")
    assert "中文" in text
    assert "\\u4e2d" not in text
    assert len(text.splitlines()) == 2
    objs = [json.loads(line) for line in text.splitlines()]
    assert objs[0]["input_state"]["text"] == "中文\n输入"
    assert objs[1]["attributes"]["text"] == "中文\n引号\"控制\x01"


def test_filtering_by_kind_node_and_run_id(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    for node in ("a", "b"):
        span = make_span(node=node)
        store.on_trace_record(make_record(span_id=span.id, node=node))
        store.on_span_end(span)

    objs = [
        json.loads(line)
        for path in sorted(target.glob("trace-*.jsonl"))
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    assert len([obj for obj in objs if obj["kind"] == "span"]) == 2
    assert len([obj for obj in objs if obj["kind"] == "trace_record"]) == 2
    assert len([obj for obj in objs if obj["node"] == "a"]) == 2
    assert len([obj for obj in objs if obj["run_id"] == objs[0]["run_id"]]) == 4
