# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · 属性允许清单 / 节点空映射 / JSON 可序列化（T022 / T047）。"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from freegraph.observability import SpanProducer, invoke_model, invoke_tool
from freegraph.observability._producer import bind_tracer as bind_l5
from freegraph.runtime._span_hook import (
    bind_span_tracer,
    end_node_span,
    start_node_span,
)


class Rec:
    def __init__(self) -> None:
        self.started: list[Any] = []
        self.ended: list[Any] = []

    def on_span_start(self, span: Any) -> None:
        self.started.append(span)

    def on_span_end(self, span: Any) -> None:
        self.ended.append(span)


class Model:
    model_name = "demo-model"

    def invoke(self, value: Any) -> Any:
        return value


class Tool:
    name = "multiply"
    description = "Multiply"

    def invoke(self, value: Any) -> Any:
        return value


class Failing:
    name = "failing"
    description = "Fails"

    def invoke(self, value: Any) -> Any:
        raise RuntimeError("boom")


@contextmanager
def _scene() -> Iterator[tuple[SpanProducer, Rec, Any]]:
    receiver = Rec()
    producer = SpanProducer(receiver)
    with bind_span_tracer(producer), bind_l5(producer):
        node = start_node_span(producer, "node", "run", "thread")
        assert node is not None
        try:
            yield producer, receiver, node
        finally:
            end_node_span(producer, node)


def test_model_and_tool_attributes_are_exact_minimal_sets() -> None:
    with _scene() as (_producer, receiver, node):
        invoke_model(Model(), 1)
        invoke_tool(Tool(), 2, call_id="call-1")

    node_span = next(span for span in receiver.started if span.name == "node")
    model_span = next(span for span in receiver.started if span.name == "chat demo-model")
    tool_span = next(
        span for span in receiver.started if span.name == "execute_tool multiply"
    )
    assert node_span.attributes == {}
    assert node_span.context == {}
    assert dict(model_span.attributes) == {
        "gen_ai.operation.name": "chat",
        "gen_ai.request.model": "demo-model",
    }
    assert dict(tool_span.attributes) == {
        "gen_ai.operation.name": "execute_tool",
        "gen_ai.tool.name": "multiply",
        "gen_ai.tool.call.id": "call-1",
    }
    forbidden = {
        "gen_ai.system",
        "gen_ai.provider.name",
        "gen_ai.usage.input_tokens",
        "gen_ai.usage.output_tokens",
        "gen_ai.response.model",
        "gen_ai.response.id",
        "gen_ai.response.finish_reasons",
        "gen_ai.request.temperature",
        "gen_ai.request.max_tokens",
        "gen_ai.request.top_p",
        "gen_ai.tool.description",
        "gen_ai.tool.type",
        "gen_ai.conversation.id",
    }
    for span in (node_span, model_span, tool_span):
        assert forbidden.isdisjoint(span.attributes)
        assert span.context == {}


def test_error_type_is_present_on_failure_and_absent_on_success() -> None:
    with _scene() as (_producer, receiver, _node):
        invoke_model(Model(), 1)
        with pytest.raises(RuntimeError):
            invoke_tool(Failing(), 2)

    successes = [span for span in receiver.ended if span.name == "chat demo-model"]
    failures = [span for span in receiver.ended if span.name == "execute_tool failing"]
    assert successes and "error.type" not in successes[-1].attributes
    assert failures and failures[-1].attributes["error.type"] == "RuntimeError"


def test_all_span_fields_are_json_serializable_via_asdict() -> None:
    with _scene() as (_producer, receiver, _node):
        invoke_model(Model(), 1)
        invoke_tool(Tool(), 2, call_id="call-1")
        with pytest.raises(RuntimeError):
            invoke_tool(Failing(), 3)

    for span in receiver.started + receiver.ended:
        payload = dataclasses.asdict(span)
        encoded = json.dumps(payload, sort_keys=True)
        assert isinstance(encoded, str)
        assert payload["context"] == {}
        if payload["name"] == "node":
            assert payload["attributes"] == {}
