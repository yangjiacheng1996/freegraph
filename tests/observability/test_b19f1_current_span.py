# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · US2：current_span() 的嵌套 / 恢复 / 空上下文。"""

from __future__ import annotations

from typing import Any, TypedDict

from freegraph.graph import END, START, StateGraph
from freegraph.observability import current_span, invoke_model, invoke_tool

from .conftest import RecordingSink


class _State(TypedDict, total=False):
    x: int


class _InnerModel:
    model_name = "inner"

    def invoke(self, value: Any) -> Any:
        return value


class _NestingTool:
    name = "nest"
    description = "nested"

    def invoke(self, value: Any) -> Any:
        return invoke_model(_InnerModel(), value)


class _OuterModel:
    model_name = "outer"

    def invoke(self, value: Any) -> Any:
        return invoke_tool(_NestingTool(), value)


def test_model_tool_model_parent_chain_and_current_span_restore() -> None:
    observed: list[Any] = []

    def node(state: _State) -> _State:
        observed.append(current_span())
        invoke_model(_OuterModel(), 1)
        observed.append(current_span())
        return {"x": 1}

    builder = StateGraph(_State)
    builder.add_node("node", node)
    builder.add_edge(START, "node")
    builder.add_edge("node", END)
    sink = RecordingSink()
    builder.compile(tracer=sink).invoke({"x": 0})

    node_span = observed[0]
    assert node_span is not None
    assert observed[1] is node_span
    spans = {span.name: span for span in sink.started}
    outer = spans["chat outer"]
    tool = spans["execute_tool nest"]
    inner = spans["chat inner"]
    assert outer.parent == node_span.id
    assert tool.parent == outer.id
    assert inner.parent == tool.id
    assert current_span() is None
