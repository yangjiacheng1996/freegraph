# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B6F1 构建器测试的共享夹具（schema / 节点替身 / 结构等价 / 快照适配）。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from freegraph.graph import END, StateGraph
from freegraph.runtime import EphemeralValue, GraphSpec


class State(TypedDict):
    """最小状态 schema。"""

    count: int


class RichState(TypedDict):
    """带两个状态通道的 schema（用于顺序断言）。"""

    first: int
    second: str


def node_a(state: dict[str, Any]) -> dict[str, Any]:
    return {}


def node_b(state: dict[str, Any]) -> dict[str, Any]:
    return {}


def router(state: dict[str, Any]) -> str:
    return "a"


def unnamed_router(state: dict[str, Any]) -> str:
    return "a"


unnamed_router.__name__ = "<lambda>"


class CallCounter:
    """节点 / 路由 / 归约器调用计数器。"""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def node(self, name: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def _node(state: dict[str, Any]) -> dict[str, Any]:
            self.counts[name] = self.counts.get(name, 0) + 1
            return {}

        _node.__name__ = name
        return _node

    def router(self, name: str, target: str = "a") -> Callable[[dict[str, Any]], str]:
        def _router(state: dict[str, Any]) -> str:
            self.counts[name] = self.counts.get(name, 0) + 1
            return target

        _router.__name__ = name
        return _router

    def reducer(self, name: str = "reducer") -> Callable[[Any, Any], Any]:
        def _reducer(left: Any, right: Any) -> Any:
            self.counts[name] = self.counts.get(name, 0) + 1
            return right

        return _reducer

    def total(self) -> int:
        return sum(self.counts.values())


def builder_summary(spec: Any) -> tuple[int, int, int]:
    """返回 ``(节点数, 静态边数, 条件边数)``。"""
    edge_count = sum(len(targets) for targets in spec.edges.values())
    return len(spec.nodes), edge_count, len(spec.conditional_edges)


def _channel_signature(channel: Any) -> tuple[Any, ...]:
    return (
        type(channel),
        channel.key,
        repr(channel.value_type),
        channel.reducer,
        getattr(channel, "guard", None),
    )


def specs_equivalent(left: Any, right: Any) -> bool:
    """按结构（而非通道对象身份）比较两份 ``_BuilderSpec``。"""
    if list(left.channels) != list(right.channels):
        return False
    if any(
        _channel_signature(left.channels[key])
        != _channel_signature(right.channels[key])
        for key in left.channels
    ):
        return False
    if list(left.nodes) != list(right.nodes):
        return False
    for name in left.nodes:
        if left.nodes[name] != right.nodes[name]:
            return False
    if left.node_records != right.node_records:
        return False
    if left.edges != right.edges:
        return False
    if len(left.conditional_edges) != len(right.conditional_edges):
        return False
    for lce, rce in zip(left.conditional_edges, right.conditional_edges):
        if (
            lce.source != rce.source
            or lce.branch != rce.branch
            or lce.path is not rce.path
            or lce.path_map != rce.path_map
            or lce.targets != rce.targets
            or lce.route_channels != rce.route_channels
        ):
            return False
    return True


def build_graph_spec_from_snapshot(spec: Any) -> GraphSpec:
    """把 ``_BuilderSpec`` 适配为 ``GraphSpec``（只过滤**单源** ``END`` 目标）。"""
    edges: dict[str | tuple[str, ...], tuple[str, ...]] = {}
    for key, targets in spec.edges.items():
        if isinstance(key, str):
            filtered = tuple(target for target in targets if target != END)
            edges[key] = filtered
        else:
            edges[key] = tuple(targets)
    return GraphSpec(
        channels=dict(spec.channels),
        nodes=dict(spec.nodes),
        edges=edges,
    )


def build_target_style() -> StateGraph:
    """与 ``harness/demo/target.py:142-155`` 同形的建图段（本地替身）。"""
    builder = StateGraph(State)
    builder.add_node("llm_call", node_a)
    builder.add_node("tool_node", node_b)
    builder.add_edge("__start__", "llm_call")
    builder.add_conditional_edges("llm_call", router, ["tool_node", END])
    builder.add_edge("tool_node", "llm_call")
    return builder


def route_channel(builder: StateGraph, target: str) -> EphemeralValue:
    return builder._build_spec().channels[f"branch:to:{target}"]  # type: ignore[attr-defined]
