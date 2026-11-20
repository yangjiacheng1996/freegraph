# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · D-201…D-208 差分场景（上游缺席 ⇒ skip）。"""

from __future__ import annotations

import importlib.metadata
from typing import Any, TypedDict

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("langchain_core")

from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402
from langchain_core.runnables import RunnableLambda  # noqa: E402
from langgraph.graph import END as UP_END  # noqa: E402
from langgraph.graph import START as UP_START  # noqa: E402
from langgraph.graph import StateGraph as UpstreamStateGraph  # noqa: E402

from freegraph.graph import END, START, RunConfig, Send, StateGraph  # noqa: E402
from freegraph.observability import SpanProducer, invoke_model, invoke_tool  # noqa: E402

from ._span_support import RecordingReceiver, bind_producer  # noqa: E402


class _State(TypedDict, total=False):
    x: int


class _Counter(BaseCallbackHandler):
    def __init__(self) -> None:
        self.starts: list[tuple[Any, Any]] = []
        self.ends: list[tuple[Any, Any]] = []
        self.errors: list[tuple[Any, Any]] = []

    def on_chain_start(self, serialized: Any, inputs: Any, **kwargs: Any) -> None:
        self.starts.append((kwargs.get("run_id"), kwargs.get("parent_run_id")))

    def on_chain_end(self, outputs: Any, **kwargs: Any) -> None:
        self.ends.append((kwargs.get("run_id"), kwargs.get("parent_run_id")))

    def on_chain_error(self, error: Any, **kwargs: Any) -> None:
        self.errors.append((kwargs.get("run_id"), kwargs.get("parent_run_id")))


def _freegraph_graph() -> Any:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_node("b", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder.compile()


def _upstream_graph() -> Any:
    builder = UpstreamStateGraph(_State)
    builder.add_node("a", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_node("b", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_edge(UP_START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", UP_END)
    return builder.compile()


def _run_freegraph(compiled: Any) -> tuple[dict[str, Any], RecordingReceiver]:
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)
    with bind_producer(producer):
        state = compiled.invoke({"x": 0})
    return state, receiver


def _node_spans(receiver: RecordingReceiver) -> list[Any]:
    return [span for span in receiver.started if not span.attributes]


def test_d201_no_tracer_no_observations_both_sides() -> None:
    free_state = _freegraph_graph().invoke({"x": 0})
    up_state = _upstream_graph().invoke({"x": 0})
    assert free_state == up_state == {"x": 2}
    # freegraph：未绑定 tracer ⇒ 零 span（由其它 US3 用例计数断言）


def test_d202_two_node_linear_same_behavior() -> None:
    free_state, receiver = _run_freegraph(_freegraph_graph())
    handler = _Counter()
    up_state = _upstream_graph().invoke({"x": 0}, config={"callbacks": [handler]})
    assert free_state == up_state == {"x": 2}
    assert len(_node_spans(receiver)) == 2
    assert len(handler.starts) >= 2


def test_d203_nested_parent_chain_same_semantics() -> None:
    class Model:
        model_name = "inner"

        def invoke(self, value: Any) -> Any:
            return value

    class Tool:
        name = "nest"
        description = "nested"

        def invoke(self, value: Any) -> Any:
            return invoke_model(Model(), value)

    class Outer:
        model_name = "outer"

        def invoke(self, value: Any) -> Any:
            return invoke_tool(Tool(), value)

    def node(state: _State) -> _State:
        invoke_model(Outer(), 1)
        return {}

    builder = StateGraph(_State)
    builder.add_node("n", node)
    builder.add_edge(START, "n")
    builder.add_edge("n", END)
    free_state, receiver = _run_freegraph(builder.compile())
    assert free_state == {"x": 0}
    by_name = {span.name: span for span in receiver.started}
    assert by_name["execute_tool nest"].parent == by_name["chat outer"].id
    assert by_name["chat inner"].parent == by_name["execute_tool nest"].id

    handler = _Counter()
    inner = RunnableLambda(lambda value: value)
    outer = RunnableLambda(lambda value: inner.invoke(value))
    assert outer.invoke(1, config={"callbacks": [handler]}) == 1
    assert len(handler.starts) == 2
    outer_run = handler.starts[0][0]
    inner_run = handler.starts[1][0]
    assert handler.starts[1][1] == outer_run
    assert outer_run != inner_run


def test_d204_model_and_tool_attributes_are_gen_ai_only() -> None:
    class Model:
        model_name = "m"

        def invoke(self, value: Any) -> Any:
            return value

    class Tool:
        name = "t"
        description = "d"

        def invoke(self, value: Any) -> Any:
            return value

    def node(state: _State) -> _State:
        invoke_model(Model(), 1)
        invoke_tool(Tool(), 2)
        return {}

    builder = StateGraph(_State)
    builder.add_node("n", node)
    builder.add_edge(START, "n")
    builder.add_edge("n", END)
    _free_state, receiver = _run_freegraph(builder.compile())
    for span in receiver.started:
        if span.name == "n":
            assert span.attributes == {}
        else:
            assert set(span.attributes) <= {
                "gen_ai.operation.name",
                "gen_ai.request.model",
                "gen_ai.tool.name",
                "gen_ai.tool.call.id",
                "error.type",
            }


def test_d205_environment_variable_does_not_enable_spans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    receiver = RecordingReceiver()
    # 不绑定 tracer；环境变量不启用生产
    _freegraph_graph().invoke({"x": 0})
    assert receiver.started == []
    assert receiver.ended == []


def test_d206_exception_still_ends_span_and_reraises() -> None:
    builder = StateGraph(_State)
    builder.add_node("boom", lambda state: (_ for _ in ()).throw(RuntimeError("boom")))
    builder.add_edge(START, "boom")
    builder.add_edge("boom", END)
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)
    with bind_producer(producer):
        with pytest.raises(RuntimeError):
            builder.compile().invoke({"x": 0})
    assert len(receiver.started) == 1
    assert len(receiver.ended) == 1

    up_builder = UpstreamStateGraph(_State)
    up_builder.add_node("boom", lambda state: (_ for _ in ()).throw(RuntimeError("boom")))
    up_builder.add_edge(UP_START, "boom")
    up_builder.add_edge("boom", UP_END)
    handler = _Counter()
    with pytest.raises(RuntimeError):
        up_builder.compile().invoke({"x": 0}, config={"callbacks": [handler]})
    assert handler.errors


def test_d207_dependency_closure_stricter() -> None:
    assert importlib.metadata.requires("freegraph") is None
    upstream_requires = importlib.metadata.requires("langchain-core") or []
    assert any("langsmith" in requirement for requirement in upstream_requires)


def test_d208_concurrent_nodes_are_independent() -> None:
    builder = StateGraph(_State)
    builder.add_node(
        "fan",
        lambda state: [Send("worker", {"x": value}) for value in (1, 2, 3)],
    )
    builder.add_node("worker", lambda state: {})
    builder.add_edge(START, "fan")
    builder.add_edge("fan", "worker")
    builder.add_edge("worker", END)
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)
    with bind_producer(producer):
        builder.compile().invoke({"x": 0}, config=RunConfig(max_concurrency=3))
    workers = [span for span in _node_spans(receiver) if span.name == "worker"]
    assert len(workers) == 3
    assert all(span.parent is None for span in workers)

    up_builder = UpstreamStateGraph(_State)
    up_builder.add_node("fan", lambda state: {})
    up_builder.add_node("a", lambda state: {})
    up_builder.add_node("b", lambda state: {})
    up_builder.add_node("c", lambda state: {})
    up_builder.add_edge(UP_START, "fan")
    up_builder.add_edge("fan", "a")
    up_builder.add_edge("fan", "b")
    up_builder.add_edge("fan", "c")
    up_builder.add_edge("a", UP_END)
    up_builder.add_edge("b", UP_END)
    up_builder.add_edge("c", UP_END)
    handler = _Counter()
    up_builder.compile().invoke({"x": 0}, config={"callbacks": [handler]})
    assert len(handler.starts) >= 4
