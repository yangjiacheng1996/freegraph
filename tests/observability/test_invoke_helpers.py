# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · US2：`invoke_model` / `invoke_tool` 的形状、属性、失败与节点外行为。"""

from __future__ import annotations

from typing import Any

import pytest

from freegraph.observability import invoke_model, invoke_tool


class Model:
    def __init__(self, model_name: str | None = None, model: str | None = None) -> None:
        self.model_name = model_name
        self.model = model
        self.calls: list[Any] = []
        self.result: Any = None

    def invoke(self, value: Any) -> Any:
        self.calls.append(value)
        return self.result if self.result is not None else value


class Tool:
    def __init__(self, name: str = "multiply", description: str | None = "d") -> None:
        self.name = name
        self.description = description
        self.calls: list[Any] = []
        self.result: Any = None

    def invoke(self, value: Any) -> Any:
        self.calls.append(value)
        return self.result if self.result is not None else value


class NotModel:
    pass


class BadTool:
    def invoke(self, value: Any) -> Any:
        return value


class AsyncModel:
    model_name = "async"

    def invoke(self, value: Any) -> Any:
        async def _coro() -> Any:
            return value

        return _coro()


def _model_spans(receiver: Any) -> list[Any]:
    return [
        span
        for span in receiver.started
        if span.attributes.get("gen_ai.operation.name") == "chat"
    ]


def _tool_spans(receiver: Any) -> list[Any]:
    return [
        span
        for span in receiver.started
        if span.attributes.get("gen_ai.operation.name") == "execute_tool"
    ]


@pytest.mark.parametrize(
    ("helper", "obj"),
    [
        (invoke_model, Tool()),
        (invoke_tool, Model()),
        (invoke_model, NotModel()),
        (invoke_tool, BadTool()),
    ],
)
def test_shape_mismatch_raises_type_error_without_tracer(helper: Any, obj: Any) -> None:
    with pytest.raises(TypeError):
        helper(obj, {"x": 1})


@pytest.mark.parametrize(
    ("helper", "obj"),
    [
        (invoke_model, Tool()),
        (invoke_tool, Model()),
        (invoke_model, NotModel()),
        (invoke_tool, BadTool()),
    ],
)
def test_shape_mismatch_raises_type_error_with_tracer(
    helper: Any,
    obj: Any,
    bound_tracer: tuple[Any, Any],
    node_span: Any,
) -> None:
    producer, receiver = bound_tracer
    before = len(receiver.started)
    with pytest.raises(TypeError):
        helper(obj, {"x": 1})
    assert len(receiver.started) == before
    assert _model_spans(receiver) == []
    assert _tool_spans(receiver) == []


def test_model_span_attributes_name_and_parent(
    bound_tracer: tuple[Any, Any], node_span: Any
) -> None:
    _producer, receiver = bound_tracer
    sentinel = object()
    model = Model(model_name="demo-model")
    model.result = sentinel

    result = invoke_model(model, "hello")

    assert result is sentinel
    spans = _model_spans(receiver)
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "chat demo-model"
    assert span.attributes == {
        "gen_ai.operation.name": "chat",
        "gen_ai.request.model": "demo-model",
    }
    assert span.parent == node_span.id
    assert span.run_id == node_span.run_id
    assert span.thread_id == node_span.thread_id
    assert span.node == node_span.node
    assert span.context == {}


def test_model_attr_fallback_and_missing_model_name(
    bound_tracer: tuple[Any, Any], node_span: Any
) -> None:
    _producer, receiver = bound_tracer
    invoke_model(Model(model="fallback"), 1)
    invoke_model(Model(), 2)
    names = [span.name for span in _model_spans(receiver)]
    assert names == ["chat fallback", "chat"]
    assert _model_spans(receiver)[1].attributes == {"gen_ai.operation.name": "chat"}


def test_tool_span_attributes_name_and_call_id(
    bound_tracer: tuple[Any, Any], node_span: Any
) -> None:
    _producer, receiver = bound_tracer
    invoke_tool(Tool(name="multiply"), {"a": 2}, call_id="call-1")
    span = _tool_spans(receiver)[0]
    assert span.name == "execute_tool multiply"
    assert span.attributes == {
        "gen_ai.operation.name": "execute_tool",
        "gen_ai.tool.name": "multiply",
        "gen_ai.tool.call.id": "call-1",
    }
    assert "gen_ai.tool.description" not in span.attributes


def test_empty_tool_name_is_written(
    bound_tracer: tuple[Any, Any], node_span: Any
) -> None:
    _producer, receiver = bound_tracer
    invoke_tool(Tool(name=""), {})
    span = _tool_spans(receiver)[0]
    assert span.name == "execute_tool "
    assert span.attributes["gen_ai.tool.name"] == ""


@pytest.mark.parametrize("call_id", [None, ""])
def test_empty_call_id_is_omitted(
    call_id: str | None, bound_tracer: tuple[Any, Any], node_span: Any
) -> None:
    _producer, receiver = bound_tracer
    invoke_tool(Tool(), {}, call_id=call_id)
    assert "gen_ai.tool.call.id" not in _tool_spans(receiver)[0].attributes


def test_model_failure_ends_span_with_error_type_and_reraises(
    bound_tracer: tuple[Any, Any], node_span: Any
) -> None:
    _producer, receiver = bound_tracer
    error = RuntimeError("model boom")

    class Failing(Model):
        def invoke(self, value: Any) -> Any:
            raise error

    with pytest.raises(RuntimeError) as exc_info:
        invoke_model(Failing(), 1)

    assert exc_info.value is error
    assert len(receiver.ended) == 1
    end = receiver.ended[0]
    assert end.id == _model_spans(receiver)[0].id
    assert end.attributes["error.type"] == "RuntimeError"


def test_tool_failure_ends_span_with_error_type_and_reraises(
    bound_tracer: tuple[Any, Any], node_span: Any
) -> None:
    _producer, receiver = bound_tracer

    class Failing(Tool):
        def invoke(self, value: Any) -> Any:
            raise ValueError("tool boom")

    with pytest.raises(ValueError):
        invoke_tool(Failing(), 1)

    end = receiver.ended[0]
    assert end.attributes["error.type"] == "ValueError"


def test_awaitable_inside_node_ends_span_with_type_error(
    bound_tracer: tuple[Any, Any], node_span: Any
) -> None:
    _producer, receiver = bound_tracer
    with pytest.raises(TypeError):
        invoke_model(AsyncModel(), 1)
    end = receiver.ended[0]
    assert end.attributes["error.type"] == "TypeError"


def test_success_has_no_error_type(
    bound_tracer: tuple[Any, Any], node_span: Any
) -> None:
    _producer, receiver = bound_tracer
    invoke_model(Model(), 1)
    invoke_tool(Tool(), 2)
    assert all("error.type" not in span.attributes for span in receiver.ended)


def test_outside_node_is_direct_call_and_produces_no_span(
    bound_tracer: tuple[Any, Any],
) -> None:
    _producer, receiver = bound_tracer
    model = Model()
    tool = Tool()
    assert invoke_model(model, 7) == 7
    assert invoke_tool(tool, 8) == 8
    assert model.calls == [7]
    assert tool.calls == [8]
    assert _model_spans(receiver) == []
    assert _tool_spans(receiver) == []


def test_outside_node_awaitable_still_raises_type_error(
    bound_tracer: tuple[Any, Any],
) -> None:
    with pytest.raises(TypeError):
        invoke_model(AsyncModel(), 1)
