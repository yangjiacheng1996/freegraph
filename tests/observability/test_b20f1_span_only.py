# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · INC-01：接收端不含 ``on_trace_record`` 时允许 span-only。"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from freegraph.graph import END, START, StateGraph
from freegraph.observability import FileTraceStore
from freegraph.runtime._span_hook import bind_span_tracer
from freegraph.runtime._stream_context import bind_run_ids

from .conftest import read_jsonl


class _State(TypedDict, total=False):
    x: int


class _SpanOnlyAdapter:
    """只转发 start/end 的适配器；不暴露 ``on_trace_record``。"""

    def __init__(self, store: FileTraceStore) -> None:
        self.store = store

    def on_span_start(self, span) -> None:
        self.store.on_span_start(span)

    def on_span_end(self, span) -> None:
        self.store.on_span_end(span)

    def current_span_id(self) -> None:
        return None


def _linear() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def test_span_only_adapter_writes_no_trace_record(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    adapter = _SpanOnlyAdapter(store)
    app = _linear().compile()
    with bind_run_ids("span-only-run", "t-1"), bind_span_tracer(adapter):
        assert app.invoke({"x": 0})["x"] == 2

    objs = read_jsonl(next(target.glob("trace-*.jsonl")))
    assert len([obj for obj in objs if obj["kind"] == "span"]) == 2
    assert [obj for obj in objs if obj["kind"] == "trace_record"] == []


def test_b19f1_injection_path_with_store_writes_both_kinds(tmp_path: Path) -> None:
    target = tmp_path / "traces"
    store = FileTraceStore(target)
    _linear().compile(tracer=store).invoke({"x": 0})
    kinds = {obj["kind"] for obj in read_jsonl(next(target.glob("trace-*.jsonl")))}
    assert kinds == {"span", "trace_record"}
