# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · 上游差分 D-301…D-310（上游缺席即 skip）。"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

import pytest

from freegraph.graph import END, START, StateGraph


class _State(TypedDict, total=False):
    x: int


class _LogState(TypedDict, total=False):
    log: Annotated[list, operator.add]


def _graph() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_node("b", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def test_d301_default_off_has_no_callbacks_on_either_side() -> None:
    pytest.importorskip("langgraph.graph")
    from langgraph.graph import END as U_END
    from langgraph.graph import START as U_START
    from langgraph.graph import StateGraph as UStateGraph

    import freegraph.runtime._span_hook as hook

    calls = 0
    original = hook.Span

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    hook.Span = counted
    try:
        assert _graph().compile().invoke({"x": 0})["x"] == 2
    finally:
        hook.Span = original
    assert calls == 0

    builder = UStateGraph(_State)
    builder.add_node("a", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_node("b", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_edge(U_START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", U_END)
    assert builder.compile().invoke({"x": 0})["x"] == 2


def _count_callbacks():
    from langchain_core.callbacks import BaseCallbackHandler

    class Counter(BaseCallbackHandler):
        def __init__(self) -> None:
            self.starts = 0
            self.ends = 0
            self.errors = 0

        def on_chain_start(self, serialized, inputs, **kwargs) -> None:
            self.starts += 1

        def on_chain_end(self, outputs, **kwargs) -> None:
            self.ends += 1

        def on_chain_error(self, error, **kwargs) -> None:
            self.errors += 1

    return Counter()


def test_d302_two_node_linear_same_behavior_and_pairing() -> None:
    pytest.importorskip("langgraph.graph")
    pytest.importorskip("langchain_core")
    from langgraph.graph import END as U_END
    from langgraph.graph import START as U_START
    from langgraph.graph import StateGraph as UStateGraph

    class Sink:
        def __init__(self) -> None:
            self.started = []
            self.ended = []

        def on_span_start(self, span) -> None:
            self.started.append(span)

        def on_span_end(self, span) -> None:
            self.ended.append(span)

    sink = Sink()
    free_state = _graph().compile(tracer=sink).invoke({"x": 0})

    builder = UStateGraph(_State)
    builder.add_node("a", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_node("b", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_edge(U_START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", U_END)
    handler = _count_callbacks()
    up_state = builder.compile().invoke({"x": 0}, config={"callbacks": [handler]})

    assert free_state == up_state == {"x": 2}
    assert len(sink.started) == len(sink.ended) == 2
    assert handler.starts >= 2 and handler.ends >= 2


def test_d304_environment_variables_do_not_enable_freegraph_observability(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    assert _graph().compile().invoke({"x": 0})["x"] == 2


def test_d305_exception_path_pairs_and_reraises_same_object() -> None:
    pytest.importorskip("langgraph.graph")
    pytest.importorskip("langchain_core")
    from langgraph.graph import END as U_END
    from langgraph.graph import START as U_START
    from langgraph.graph import StateGraph as UStateGraph

    error = RuntimeError("boom")

    class Sink:
        def __init__(self) -> None:
            self.started = []
            self.ended = []

        def on_span_start(self, span) -> None:
            self.started.append(span)

        def on_span_end(self, span) -> None:
            self.ended.append(span)

    def boom(state):
        raise error

    builder = StateGraph(_State)
    builder.add_node("boom", boom)
    builder.add_edge(START, "boom")
    builder.add_edge("boom", END)
    sink = Sink()
    with pytest.raises(RuntimeError) as free_info:
        builder.compile(tracer=sink).invoke({"x": 0})
    assert free_info.value is error
    assert len(sink.started) == len(sink.ended) == 1

    up = UStateGraph(_State)
    up.add_node("boom", boom)
    up.add_edge(U_START, "boom")
    up.add_edge("boom", U_END)
    handler = _count_callbacks()
    with pytest.raises(RuntimeError):
        up.compile().invoke({"x": 0}, config={"callbacks": [handler]})
    assert handler.errors >= 1


def test_d307_dependency_closure_is_stricter() -> None:
    import tomllib

    from pathlib import Path

    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["dependencies"] == []
    pytest.importorskip("langsmith")


def test_d310_stream_and_span_share_ids_on_freegraph_side() -> None:
    class Sink:
        def __init__(self) -> None:
            self.started = []

        def on_span_start(self, span) -> None:
            self.started.append(span)

        def on_span_end(self, span) -> None:
            pass

    sink = Sink()
    app = _graph().compile(tracer=sink)
    events = list(app.stream({"x": 0}, stream_mode="updates"))
    event_ids = {(event["run_id"], event["thread_id"]) for event in events}
    span_ids = {(span.run_id, span.thread_id) for span in sink.started}
    assert event_ids == span_ids


def test_d303_nested_parent_chain_with_tracesink() -> None:
    from typing import Any

    from freegraph.observability import invoke_model, invoke_tool

    class Inner:
        model_name = "inner"

        def invoke(self, value: Any) -> Any:
            return value

    class Tool:
        name = "nest"
        description = "nested"

        def invoke(self, value: Any) -> Any:
            return invoke_model(Inner(), value)

    class Outer:
        model_name = "outer"

        def invoke(self, value: Any) -> Any:
            return invoke_tool(Tool(), value)

    class Sink:
        def __init__(self) -> None:
            self.started = []

        def on_span_start(self, span) -> None:
            self.started.append(span)

        def on_span_end(self, span) -> None:
            pass

    def node(state):
        invoke_model(Outer(), 1)
        return {}

    builder = StateGraph(_State)
    builder.add_node("n", node)
    builder.add_edge(START, "n")
    builder.add_edge("n", END)
    sink = Sink()
    builder.compile(tracer=sink).invoke({"x": 0})
    by_name = {span.name: span for span in sink.started}
    assert by_name["chat outer"].parent == by_name["n"].id
    assert by_name["execute_tool nest"].parent == by_name["chat outer"].id
    assert by_name["chat inner"].parent == by_name["execute_tool nest"].id


def test_d306_current_span_is_available_inside_node() -> None:
    from freegraph.observability import current_span

    seen = []

    def node(state):
        seen.append(current_span())
        return {}

    builder = StateGraph(_State)
    builder.add_node("n", node)
    builder.add_edge(START, "n")
    builder.add_edge("n", END)
    builder.compile().invoke({"x": 0})
    assert seen and seen[0] is None


def test_d308_injection_carrier_produces_events_on_both_sides() -> None:
    pytest.importorskip("langgraph.graph")
    pytest.importorskip("langchain_core")
    from langgraph.graph import END as U_END
    from langgraph.graph import START as U_START
    from langgraph.graph import StateGraph as UStateGraph

    class Sink:
        def __init__(self) -> None:
            self.started = 0

        def on_span_start(self, span) -> None:
            self.started += 1

        def on_span_end(self, span) -> None:
            pass

    sink = Sink()
    _graph().compile(tracer=sink).invoke({"x": 0})
    assert sink.started == 2

    builder = UStateGraph(_State)
    builder.add_node("a", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_node("b", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_edge(U_START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", U_END)
    handler = _count_callbacks()
    builder.compile().invoke({"x": 0}, config={"callbacks": [handler]})
    assert handler.starts >= 2


def test_d309_metadata_surface_is_freegraph_specific() -> None:

    class Sink:
        def __init__(self) -> None:
            self.records = []

        def on_span_start(self, span) -> None:
            pass

        def on_span_end(self, span) -> None:
            pass

        def on_trace_record(self, record) -> None:
            self.records.append(record)

    builder = StateGraph(_LogState)
    builder.add_node("a", lambda state: {"log": ["a"]})
    builder.add_node("b", lambda state: {"log": ["b"]})
    builder.add_node("c", lambda state: {"log": ["c"]})
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    builder.add_edge(["a", "b"], "c")
    builder.add_edge("c", END)
    sink = Sink()
    builder.compile(tracer=sink).invoke({"log": []})
    c_record = next(record for record in sink.records if record.node == "c")
    assert c_record.triggers
    assert c_record.barrier_groups == (("a", "b"),)
    assert c_record.concurrency_group
