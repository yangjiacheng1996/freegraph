# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · 记录与节点 span 对齐 / 中断 / 取消 / record 回调隔离。"""

from __future__ import annotations

import asyncio
import operator
from typing import Annotated, TypedDict

import pytest

from freegraph.graph import END, START, StateGraph, interrupt

from .conftest import B19FailingRecordSink, B19RecordingSink


class _State(TypedDict, total=False):
    x: int


class _LogState(TypedDict, total=False):
    log: Annotated[list, operator.add]


def _linear() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def test_record_count_equals_node_span_count_and_order() -> None:
    sink = B19RecordingSink()
    _linear().compile(tracer=sink).invoke({"x": 0})
    assert len(sink.records) == len(sink.started) == 2
    assert [record.span_id for record in sink.records] == [span.id for span in sink.started]


def test_interrupt_record_keeps_original_graph_interrupt() -> None:
    def gate(state: _State) -> _State:
        interrupt({"need": "approval"})
        return {}

    builder = StateGraph(_State)
    builder.add_node("gate", gate)
    builder.add_edge(START, "gate")
    builder.add_edge("gate", END)
    sink = B19RecordingSink()
    result = builder.compile(tracer=sink).invoke({"x": 0})
    assert "__interrupt__" in result
    assert len(sink.records) == 1
    assert type(sink.records[0].error).__name__ == "GraphInterrupt"


def test_node_raised_cancellation_keeps_original_object_and_record() -> None:
    error = asyncio.CancelledError("stop")

    def cancel(state: _State) -> _State:
        raise error

    builder = StateGraph(_State)
    builder.add_node("cancel", cancel)
    builder.add_edge(START, "cancel")
    builder.add_edge("cancel", END)
    sink = B19RecordingSink()
    with pytest.raises(BaseException) as info:
        builder.compile(tracer=sink).invoke({"x": 0})
    assert info.value is error
    assert len(sink.records) == 1
    assert sink.records[0].error is error


def test_record_callback_exception_is_isolated() -> None:
    sink = B19FailingRecordSink()
    assert _linear().compile(tracer=sink).invoke({"x": 0})["x"] == 2
    assert len(sink.records) == 2


def test_concurrent_cancellation_keeps_record_count_aligned() -> None:
    from freegraph.graph import RunConfig, Send

    def fan(state):
        return [Send("worker", {"fail": True}), Send("worker", {"fail": False})]

    def worker(state):
        if state.get("fail"):
            raise RuntimeError("boom")
        return {}

    builder = StateGraph(_LogState)
    builder.add_node("fan", fan)
    builder.add_node("worker", worker)
    builder.add_edge(START, "fan")
    builder.add_edge("fan", "worker")
    builder.add_edge("worker", END)
    sink = B19RecordingSink()
    with pytest.raises(RuntimeError):
        builder.compile(tracer=sink).invoke(
            {"log": []}, config=RunConfig(max_concurrency=1)
        )
    worker_spans = [span for span in sink.started if span.name == "worker"]
    worker_records = [record for record in sink.records if record.node == "worker"]
    assert len(worker_spans) == len(worker_records)
    assert {record.task_id for record in worker_records} <= {"worker:0", "worker:1"}
