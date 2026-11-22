# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B14F1 · 节点 span 的 ``checkpoint_id``（子 span 继承）。"""

from __future__ import annotations

from typing import Any, TypedDict

from freegraph.contracts import RunConfig
from freegraph.graph import END, START, StateGraph
from freegraph.observability import SpanProducer, invoke_model
from freegraph.persistence import MemorySaver

from ._span_support import RecordingReceiver, bind_producer


class _State(TypedDict, total=False):
    x: int


class _Model:
    def invoke(self, value: Any) -> str:
        return "ok"


def _graph() -> StateGraph:
    def node(state: _State) -> _State:
        invoke_model(_Model(), "hello")
        return {"x": 1}

    builder = StateGraph(_State)
    builder.add_node("a", node)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    return builder


def test_node_and_child_span_inherit_checkpoint_id() -> None:
    saver = MemorySaver()
    cfg = RunConfig(thread_id="span")
    app = _graph().compile(checkpointer=saver)
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)

    with bind_producer(producer):
        app.invoke({"x": 0}, cfg)

    node_span = next(span for span in receiver.started if span.node == "a")
    model_span = next(span for span in receiver.started if span.node == "a" and span is not node_span)
    initial = list(saver.list(cfg))[-1].snapshot
    initial_id = initial.config.configurable["checkpoint_id"]
    assert node_span.checkpoint_id == initial_id
    assert model_span.checkpoint_id == initial_id
    assert model_span.parent == node_span.id


def test_without_checkpointer_checkpoint_id_is_none() -> None:
    app = _graph().compile()
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)

    with bind_producer(producer):
        app.invoke({"x": 0}, RunConfig(thread_id="span-none"))

    node_span = next(span for span in receiver.started if span.node == "a")
    assert node_span.checkpoint_id is None
