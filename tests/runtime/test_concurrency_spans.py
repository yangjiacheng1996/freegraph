# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · US5：并发节点 span 独立，模型 / 工具子 span 不跨任务串父。"""

from __future__ import annotations

from typing import TypedDict

from freegraph.graph import END, START, RunConfig, Send, StateGraph
from freegraph.observability import SpanProducer, invoke_tool

from ._span_support import RecordingReceiver, bind_producer


class _State(TypedDict, total=False):
    x: int


class DynamicTool:
    def __init__(self, name: str) -> None:
        self.name = name
        self.description = "dynamic"

    def invoke(self, args: object) -> None:
        return None


def test_concurrent_nodes_have_independent_node_and_tool_spans() -> None:
    def worker(state: _State) -> _State:
        invoke_tool(DynamicTool(f"tool-{state['x']}"), {})
        return {}

    builder = StateGraph(_State)
    builder.add_node(
        "fan",
        lambda state: [Send("worker", {"x": value}) for value in (1, 2, 3)],
    )
    builder.add_node("worker", worker)
    builder.add_edge(START, "fan")
    builder.add_edge("fan", "worker")
    builder.add_edge("worker", END)
    compiled = builder.compile()
    receiver = RecordingReceiver()
    producer = SpanProducer(receiver)

    with bind_producer(producer):
        compiled.invoke({"x": 0}, config=RunConfig(max_concurrency=3))

    node_spans = [span for span in receiver.started if not span.attributes]
    worker_spans = [span for span in node_spans if span.name == "worker"]
    tool_spans = [
        span
        for span in receiver.started
        if span.attributes.get("gen_ai.operation.name") == "execute_tool"
    ]
    fan_spans = [span for span in node_spans if span.name == "fan"]

    assert len(worker_spans) == 3
    assert len(fan_spans) == 1
    assert all(span.parent is None for span in worker_spans)
    assert len({span.id for span in worker_spans}) == 3
    assert len(tool_spans) == 3
    worker_ids = {span.id for span in worker_spans}
    assert {span.parent for span in tool_spans} == worker_ids
    assert all(span.parent not in {fan.id for fan in fan_spans} for span in tool_spans)
    tool_names = {span.attributes["gen_ai.tool.name"] for span in tool_spans}
    assert tool_names == {"tool-1", "tool-2", "tool-3"}
