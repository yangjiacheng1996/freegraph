# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · US2：跨编译产物嵌套 / 作用域优先级 / run-id 单次绑定。"""

from __future__ import annotations

from typing import TypedDict

from freegraph.graph import END, START, StateGraph
from freegraph.observability import SpanProducer
from freegraph.observability._producer import bind_tracer
from freegraph.runtime._span_hook import bind_span_tracer

from .conftest import B19RecordingSink, B19RunIdBindingCounter


class _State(TypedDict, total=False):
    x: int


def _inner_graph() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("inner", lambda state: {})
    builder.add_edge(START, "inner")
    builder.add_edge("inner", END)
    return builder


def _outer_graph(action) -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("outer", action)
    builder.add_edge(START, "outer")
    builder.add_edge("outer", END)
    return builder


def test_inner_without_tracer_is_masked_inside_b19f1_scope() -> None:
    inner = _inner_graph().compile()
    sink = B19RecordingSink()

    def node(state: _State) -> _State:
        inner.invoke({"x": 0})
        return {}

    _outer_graph(node).compile(tracer=sink).invoke({"x": 0})
    assert [span.name for span in sink.started] == ["outer"]
    assert [record.node for record in sink.records] == ["outer"]


def test_inner_with_tracer_gets_independent_tree() -> None:
    inner_sink = B19RecordingSink()
    inner = _inner_graph().compile(tracer=inner_sink)
    outer_sink = B19RecordingSink()

    def node(state: _State) -> _State:
        inner.invoke({"x": 0})
        return {}

    _outer_graph(node).compile(tracer=outer_sink).invoke({"x": 0})
    assert outer_sink.started[0].run_id != inner_sink.started[0].run_id
    assert inner_sink.started[0].parent is None


def test_direct_binding_outside_scope_still_produces_spans() -> None:
    inner = _inner_graph().compile()
    sink = B19RecordingSink()
    producer = SpanProducer(sink)
    with bind_span_tracer(producer), bind_tracer(producer):
        inner.invoke({"x": 0})
    assert [span.name for span in sink.started] == ["inner"]


def test_direct_binding_inside_b19f1_scope_is_masked() -> None:
    inner = _inner_graph().compile()
    direct_sink = B19RecordingSink()
    producer = SpanProducer(direct_sink)
    outer_sink = B19RecordingSink()

    def node(state: _State) -> _State:
        with bind_span_tracer(producer), bind_tracer(producer):
            inner.invoke({"x": 0})
        return {}

    _outer_graph(node).compile(tracer=outer_sink).invoke({"x": 0})
    assert direct_sink.started == []
    assert [span.name for span in outer_sink.started] == ["outer"]


def test_each_injected_run_binds_run_id_exactly_once(monkeypatch) -> None:
    counter = B19RunIdBindingCounter()
    counter.install(monkeypatch)
    inner = _inner_graph().compile(tracer=B19RecordingSink())

    def node(state: _State) -> _State:
        inner.invoke({"x": 0})
        return {}

    _outer_graph(node).compile(tracer=B19RecordingSink()).invoke({"x": 0})
    assert len(counter.calls) == 2
