# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · US1：``compile(tracer=FileTraceStore(...))`` 的图集成路径。"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import pytest

from freegraph.graph import END, START, RunConfig, StateGraph
from freegraph.observability import FileTraceStore, invoke_model, invoke_tool

from .conftest import read_jsonl


class _State(TypedDict, total=False):
    x: int


class _Model:
    model_name = "demo-model"

    def invoke(self, value: object) -> object:
        return value


class _Tool:
    name = "demo-tool"
    description = "demo"

    def invoke(self, value: object) -> object:
        return value


def _linear() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def _files(directory: Path) -> list[Path]:
    return sorted(directory.glob("trace-*.jsonl"))


def test_linear_graph_writes_paired_span_and_record_lines(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    out = _linear().compile(tracer=store).invoke(
        {"x": 0}, config=RunConfig(thread_id="t-1")
    )

    assert out["x"] == 2
    files = _files(target)
    assert len(files) == 1
    objs = read_jsonl(files[0])
    spans = [obj for obj in objs if obj["kind"] == "span"]
    records = [obj for obj in objs if obj["kind"] == "trace_record"]
    assert len(spans) == 2
    assert len(records) == 2
    span_ids = {span["id"] for span in spans}
    assert {record["span_id"] for record in records} <= span_ids
    for obj in objs:
        assert obj["run_id"]
        assert obj["thread_id"] == "t-1"
        assert obj["node"] in {"a", "b"}
        assert obj["checkpoint_id"] is None
        assert read_jsonl(files[0]) == objs


def test_model_and_tool_spans_are_written_with_parent(tmp_path: Path) -> None:
    target = tmp_path / "traces"

    def node(state: _State) -> _State:
        invoke_model(_Model(), 1)
        invoke_tool(_Tool(), 2)
        return {"x": 1}

    builder = StateGraph(_State)
    builder.add_node("n", node)
    builder.add_edge(START, "n")
    builder.add_edge("n", END)
    store = FileTraceStore(target)
    builder.compile(tracer=store).invoke({"x": 0})

    objs = read_jsonl(_files(target)[0])
    spans = [obj for obj in objs if obj["kind"] == "span"]
    node_span = next(obj for obj in spans if obj["name"] == "n")
    model_span = next(obj for obj in spans if obj["name"] == "chat demo-model")
    tool_span = next(obj for obj in spans if obj["name"] == "execute_tool demo-tool")
    assert model_span["parent"] == node_span["id"]
    assert tool_span["parent"] == node_span["id"]
    assert len([obj for obj in objs if obj["kind"] == "trace_record"]) == 1


def test_exception_node_still_writes_span_and_record_and_reraises(
    tmp_path: Path,
) -> None:
    target = tmp_path / "traces"
    error = RuntimeError("boom")

    def boom(state: _State) -> _State:
        raise error

    builder = StateGraph(_State)
    builder.add_node("boom", boom)
    builder.add_edge(START, "boom")
    builder.add_edge("boom", END)
    store = FileTraceStore(target)

    with pytest.raises(RuntimeError) as caught:
        builder.compile(tracer=store).invoke({"x": 0})
    assert caught.value is error

    objs = read_jsonl(_files(target)[0])
    span = next(obj for obj in objs if obj["kind"] == "span")
    record = next(obj for obj in objs if obj["kind"] == "trace_record")
    assert span["end_time"] is not None
    assert record["error"] == {"type": "RuntimeError", "message": "boom"}
    assert "RuntimeError" not in str(record.get("error", {})).replace("RuntimeError", "", 1)


def test_stream_path_writes_same_shape(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    events = list(_linear().compile(tracer=store).stream({"x": 0}))
    assert events
    objs = read_jsonl(_files(target)[0])
    assert {obj["kind"] for obj in objs} == {"span", "trace_record"}
    assert len([obj for obj in objs if obj["kind"] == "span"]) == 2
    assert len([obj for obj in objs if obj["kind"] == "trace_record"]) == 2


def test_same_store_two_invokes_write_two_files(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    app = _linear().compile(tracer=store)
    app.invoke({"x": 0})
    app.invoke({"x": 0})
    assert len(_files(target)) == 2
