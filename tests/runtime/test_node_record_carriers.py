# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · 原则 IV 的 stream 载体（T055）。

stream 路径可还原：节点名 / 耗时由节点 span；输入 / 输出由 ``values`` /
``updates`` / ``tasks`` + ``PregelTask.result``；错误由**原样抛出的异常**
（并发其它失败见 ``add_note``）。``PregelTask.error`` **不作为失败路径载体**。
``invoke()`` 路径的逐节点三项由 B19F1/B20 下游承接（D-6）。
"""

from __future__ import annotations

from typing import TypedDict

import pytest

from freegraph.graph import END, START, StateGraph
from freegraph.observability import SpanProducer

from ._span_support import RecordingReceiver, bind_producer


class _State(TypedDict, total=False):
    x: int


def test_stream_carriers_reconstruct_node_input_and_output() -> None:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_node("b", lambda state: {"x": state.get("x", 0) + 1})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    compiled = builder.compile()
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)

    with bind_producer(producer):
        events = list(
            compiled.stream(
                {"x": 0},
                stream_mode=["values", "updates", "tasks"],
            )
        )

    values = [event["payload"] for event in events if event["stream_mode"] == "values"]
    updates = [event["payload"] for event in events if event["stream_mode"] == "updates"]
    tasks = [event["payload"] for event in events if event["stream_mode"] == "tasks"]

    assert values[0] == {"x": 0}  # a 的输入
    assert updates[0] == {"a": {"x": 1}}
    assert tasks[0].name == "a" and tasks[0].result == {"x": 1}
    assert values[1] == {"x": 1}  # b 的输入
    assert updates[1] == {"b": {"x": 2}}
    assert tasks[1].name == "b" and tasks[1].result == {"x": 2}

    for span in receiver.started:
        assert span.attributes == {}
        assert span.context == {}


def test_stream_failure_error_is_carried_by_the_exception() -> None:
    error = RuntimeError("boom")

    def boom(state: _State) -> _State:
        raise error

    builder = StateGraph(_State)
    builder.add_node("boom", boom)
    builder.add_edge(START, "boom")
    builder.add_edge("boom", END)
    compiled = builder.compile()
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)
    events = []

    with bind_producer(producer):
        with pytest.raises(RuntimeError) as exc_info:
            for event in compiled.stream({"x": 0}, stream_mode=["tasks"]):
                events.append(event)

    assert exc_info.value is error
    assert events == []  # 失败路径不发 tasks 事件 ⇒ PregelTask.error 不可见
    assert len(receiver.started) == 1
    assert len(receiver.ended) == 1
    assert receiver.started[0].attributes == {}
    assert receiver.ended[0].attributes == {}
