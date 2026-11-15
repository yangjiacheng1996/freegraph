# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B6F1 构建器主路径测试（US1 / US2 / US4 / US6 + 签名 / 最小图）。"""

from __future__ import annotations

import inspect
from typing import Annotated, Any, Literal, TypedDict

import pytest

from freegraph.graph import END, START, Command, Send, StateGraph

from ._builder_support import (
    CallCounter,
    RichState,
    State,
    build_target_style,
    builder_summary,
    node_a,
    node_b,
    router,
    unnamed_router,
)


def literal_router(state: dict[str, Any]) -> Literal["a", "__end__"]:
    return "a"


_REDUCER_CALLS = {"count": 0}


def _counted_reducer(left: list[int], right: list[int]) -> list[int]:
    _REDUCER_CALLS["count"] += 1
    return right


class ReducerState(TypedDict):
    values: Annotated[list[int], _counted_reducer]


def test_target_style_build_is_unchanged() -> None:
    """SC-001：target 风格建图段原样执行，2 节点 / 2 静态边 / 1 条件边。"""
    builder = build_target_style()
    assert builder.validate() is builder
    spec = builder._build_spec()  # type: ignore[attr-defined]

    assert list(spec.nodes) == ["llm_call", "tool_node"]
    assert spec.edges["__start__"] == ("llm_call",)
    assert spec.edges["tool_node"] == ("llm_call",)
    assert len(spec.conditional_edges) == 1
    conditional = spec.conditional_edges[0]
    assert conditional.branch == "router"
    assert conditional.path_map == {"tool_node": "tool_node", END: END}
    assert conditional.targets == ("tool_node", END)
    assert conditional.route_channels == ("branch:to:tool_node",)
    assert builder_summary(spec) == (2, 2, 1)


def test_alias_defer_metadata_and_single_callable_are_recorded() -> None:
    """SC-014：alias / defer / metadata 记录；单 callable 取名可用。"""
    metadata = {"tag": "x"}
    builder = StateGraph(State)
    builder.add_node("a", node_a, alias="model", defer=True, metadata=metadata)
    builder.add_node(node_b)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    metadata["tag"] = "changed"

    spec = builder._build_spec()  # type: ignore[attr-defined]
    record = spec.node_records["a"]
    assert record.alias == "model"
    assert record.defer is True
    assert record.metadata == {"tag": "x"}
    assert "node_b" in spec.node_records
    assert spec.edges["a"] == (END,)


def test_path_map_list_dict_none_and_hashable_keys() -> None:
    """SC-002 / FR-004：list / dict / None / Hashable key 的归一化与路由通道。"""
    builder = StateGraph(State)
    builder.add_node("r", node_a)
    builder.add_node("a", node_b)
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", router, ["a", END])
    builder.validate()
    conditional = builder._build_spec().conditional_edges[0]  # type: ignore[attr-defined]
    assert conditional.branch == "router"
    assert conditional.path_map == {"a": "a", END: END}
    assert conditional.targets == ("a", END)
    assert conditional.route_channels == ("branch:to:a",)

    builder = StateGraph(State)
    builder.add_node("r", node_a)
    builder.add_node("hit", node_b)
    builder.add_node("miss", node_b)
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", router, {"hit": "hit", "miss": "miss"})
    builder.validate()
    conditional = builder._build_spec().conditional_edges[0]  # type: ignore[attr-defined]
    assert conditional.path_map == {"hit": "hit", "miss": "miss"}
    assert conditional.targets == ("hit", "miss")
    assert conditional.route_channels == ("branch:to:hit", "branch:to:miss")

    builder = StateGraph(State)
    builder.add_node("r", node_a)
    builder.add_node("a", node_b)
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", router, {1: "a"})
    builder.validate()
    conditional = builder._build_spec().conditional_edges[0]  # type: ignore[attr-defined]
    assert conditional.path_map == {1: "a"}
    assert conditional.targets == ("a",)

    builder = StateGraph(State)
    builder.add_node("r", node_a)
    builder.add_node("a", node_b)
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", literal_router)
    builder.validate()
    conditional = builder._build_spec().conditional_edges[0]  # type: ignore[attr-defined]
    assert conditional.path_map == {"a": "a", END: END}
    assert conditional.targets == ("a", END)

    builder = StateGraph(State)
    builder.add_node("r", node_a)
    builder.add_node("a", node_b)
    builder.add_edge(START, "r")
    builder.add_conditional_edges("r", router)
    builder.validate()
    conditional = builder._build_spec().conditional_edges[0]  # type: ignore[attr-defined]
    assert conditional.path_map is None
    assert conditional.targets == ()
    assert conditional.route_channels == ()


def test_unnamed_callable_branch_name_is_condition() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_edge(START, "a")
    builder.add_conditional_edges("a", unnamed_router, ["a", END])
    assert builder._build_spec().conditional_edges[0].branch == "condition"  # type: ignore[attr-defined]


def test_builder_methods_are_chainable() -> None:
    """SC-004：三个构建方法与 validate 均返回同一 builder。"""
    builder = StateGraph(State)
    assert builder.add_node("a", node_a) is builder
    assert builder.add_edge(START, "a") is builder
    assert builder.add_edge("a", END) is builder
    assert builder.add_conditional_edges("a", router, ["a", END]) is builder
    assert builder.validate() is builder


def test_build_is_pure_and_accepts_all_return_forms() -> None:
    """SC-007：构建期不调用节点 / 路由 / 归约器；返回注解不被拒绝。"""
    counter = CallCounter()
    _REDUCER_CALLS["count"] = 0

    def n_command(state: dict[str, Any]) -> Command:
        return Command()

    def n_command_list(state: dict[str, Any]) -> list[Command | dict[str, Any]]:
        return []

    def n_none(state: dict[str, Any]) -> None:
        return None

    def n_send(state: dict[str, Any]) -> Send:
        return Send("a", {})

    def n_send_list(state: dict[str, Any]) -> list[Send]:
        return []

    builder = StateGraph(ReducerState)
    builder.add_node("a", counter.node("node"))
    builder.add_node("cm", n_command)
    builder.add_node("cml", n_command_list)
    builder.add_node("none", n_none)
    builder.add_node("send", n_send)
    builder.add_node("sends", n_send_list)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    builder.add_conditional_edges("a", counter.router("router"), ["a", END])

    builder.validate()
    spec = builder._build_spec()  # type: ignore[attr-defined]
    assert list(spec.nodes) == ["a", "cm", "cml", "none", "send", "sends"]
    assert counter.total() == 0
    assert _REDUCER_CALLS["count"] == 0


def test_minimal_graph_can_be_built() -> None:
    """SC-015：最小图（2 节点 + START / END 边）可构造并通过 validate。"""
    counter = CallCounter()
    builder = StateGraph(State)
    builder.add_node("a", counter.node("a"))
    builder.add_node("b", counter.node("b"))
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)

    builder.validate()
    spec = builder._build_spec()  # type: ignore[attr-defined]
    assert builder_summary(spec) == (2, 3, 0)
    assert counter.total() == 0


def _required_positional_names(callable_obj: Any) -> list[str]:
    signature = inspect.signature(callable_obj)
    return [
        parameter.name
        for parameter in signature.parameters.values()
        if parameter.name != "self"
        and parameter.kind
        in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
        and parameter.default is parameter.empty
    ]


def test_constitutional_signature_and_self_return_match_upstream() -> None:
    """SC-006：只比较方法名 / 必填位置参数 / 返回语义（附上游 state.py 行号）。"""
    pytest.importorskip("langgraph")
    from langgraph.graph import END as UP_END
    from langgraph.graph import START as UP_START
    from langgraph.graph import StateGraph as UpstreamStateGraph

    for method_name in ("__init__", "add_node", "add_edge", "add_conditional_edges", "validate"):
        ours = _required_positional_names(getattr(StateGraph, method_name))
        theirs = _required_positional_names(getattr(UpstreamStateGraph, method_name))
        assert ours == theirs, (method_name, ours, theirs)

    builder = StateGraph(State)
    upstream = UpstreamStateGraph(State)
    for target in (builder, upstream):
        assert target.add_node("a", node_a) is target
        assert target.add_edge(UP_START if target is upstream else START, "a") is target
        assert (
            target.add_conditional_edges("a", router, ["a", UP_END if target is upstream else END])
            is target
        )
        assert target.validate() is target
