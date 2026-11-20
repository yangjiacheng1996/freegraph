# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · US2/US5：SpanProducer 的父链、栈平衡与接收端异常隔离。"""

from __future__ import annotations

from typing import Any

from freegraph.observability import SpanProducer, invoke_model, invoke_tool
from freegraph.runtime._span_hook import end_node_span, start_node_span

from .conftest import FailingReceiver, RecordingReceiver, bind_producer


class InnerModel:
    model_name = "inner"

    def invoke(self, value: Any) -> Any:
        return value


class OuterModel:
    model_name = "outer"

    def invoke(self, value: Any) -> Any:
        return invoke_tool(NestingTool(), value)


class NestingTool:
    name = "nest"
    description = "nested"

    def invoke(self, value: Any) -> Any:
        return invoke_model(InnerModel(), value)


def _span_named(receiver: RecordingReceiver, name: str) -> Any:
    matches = [span for span in receiver.started if span.name == name]
    assert len(matches) == 1, [span.name for span in receiver.started]
    return matches[0]


def test_nested_model_tool_model_parent_chain(
    bound_tracer: tuple[Any, Any], node_span: Any
) -> None:
    producer, receiver = bound_tracer
    assert invoke_model(OuterModel(), 1) == 1

    node = node_span
    outer = _span_named(receiver, "chat outer")
    tool = _span_named(receiver, "execute_tool nest")
    inner = _span_named(receiver, "chat inner")
    assert outer.parent == node.id
    assert tool.parent == outer.id
    assert inner.parent == tool.id
    assert producer.current_span_id() == node.id


def test_failing_receiver_does_not_break_call_or_stack(
    recording_receiver: RecordingReceiver,
) -> None:
    receiver = FailingReceiver()
    producer = SpanProducer(receiver)
    with bind_producer(producer):
        node = start_node_span(producer, "n", "run", "thread")
        assert node is not None
        assert invoke_model(InnerModel(), 1) == 1
        end_node_span(producer, node)
    assert producer.current_span_id() is None
    assert receiver.calls >= 3


def test_receiver_exception_on_end_is_isolated() -> None:
    receiver = FailingReceiver()
    producer = SpanProducer(receiver)
    with bind_producer(producer):
        node = start_node_span(producer, "n", "run", "thread")
        assert node is not None
        end_node_span(producer, node)
    assert producer.current_span_id() is None
    assert receiver.calls == 2


def test_copy_context_tasks_have_independent_stacks() -> None:
    import threading
    from contextvars import copy_context

    producer = SpanProducer()
    barrier = threading.Barrier(2)
    observed: dict[str, str | None] = {}

    def worker(key: str) -> None:
        context = copy_context()

        def run() -> None:
            node = start_node_span(producer, key, "run", "thread")
            assert node is not None
            observed[f"{key}-start"] = producer.current_span_id()
            barrier.wait(timeout=5)
            end_node_span(producer, node)
            observed[f"{key}-end"] = producer.current_span_id()

        context.run(run)

    first = threading.Thread(target=worker, args=("a",))
    second = threading.Thread(target=worker, args=("b",))
    first.start()
    second.start()
    first.join(timeout=5)
    second.join(timeout=5)
    assert not first.is_alive() and not second.is_alive()
    assert observed["a-start"] != observed["b-start"]
    assert observed["a-end"] is None
    assert observed["b-end"] is None
