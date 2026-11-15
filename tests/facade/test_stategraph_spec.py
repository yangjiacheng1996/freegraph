# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B6F1 内部快照与 B7F1 ``GraphSpec`` 适配测试（US5）。"""

from __future__ import annotations

from typing import Any

import pytest

from freegraph.graph import END, START, StateGraph
from freegraph.runtime import GraphSpec

from ._builder_support import (
    RichState,
    State,
    build_graph_spec_from_snapshot,
    node_a,
    node_b,
    router,
    specs_equivalent,
)


def _valid_builder() -> StateGraph:
    builder = StateGraph(RichState)
    builder.add_node("a", node_a)
    builder.add_node("b", node_b)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    builder.add_conditional_edges("a", router, ["a", "b", END])
    return builder


def test_builder_spec_can_become_graph_spec() -> None:
    builder = _valid_builder()
    builder.validate()
    spec = builder._build_spec()  # type: ignore[attr-defined]
    graph_spec = build_graph_spec_from_snapshot(spec)

    assert isinstance(graph_spec, GraphSpec)
    assert graph_spec.conditional_edges == {}
    assert list(graph_spec.channels) == ["first", "second", "branch:to:a", "branch:to:b"]
    assert list(graph_spec.nodes) == ["a", "b"]
    assert graph_spec.edges["__start__"] == ("a",)


def test_multi_source_end_is_retained_and_rejected_by_graph_spec_v16() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_node("b", node_b)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    builder.add_edge(["a", "b"], END)
    builder.validate()
    spec = builder._build_spec()  # type: ignore[attr-defined]
    assert spec.edges[("a", "b")] == (END,)
    with pytest.raises(ValueError, match="V-16|__end__"):
        build_graph_spec_from_snapshot(spec)


def test_multi_source_multiple_targets_are_retained_and_rejected_by_v16() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_node("b", node_b)
    builder.add_node("c", node_a)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    builder.add_edge(["a", "b"], "c")
    builder.add_edge(["a", "b"], END)
    builder.validate()
    spec = builder._build_spec()  # type: ignore[attr-defined]
    assert spec.edges[("a", "b")] == ("c", END)
    with pytest.raises(ValueError, match="V-16"):
        build_graph_spec_from_snapshot(spec)


def test_parent_node_is_retained_and_rejected_by_graph_spec() -> None:
    builder = StateGraph(State)
    builder.add_node("__parent__", node_a)
    builder.add_edge(START, "__parent__")
    builder.add_edge("__parent__", END)
    builder.validate()
    spec = builder._build_spec()  # type: ignore[attr-defined]
    assert "__parent__" in spec.nodes
    assert "__parent__" in spec.node_records
    with pytest.raises(ValueError, match="reserved|__parent__"):
        build_graph_spec_from_snapshot(spec)


def test_snapshots_are_equivalent_but_independent() -> None:
    builder = _valid_builder()
    first = builder._build_spec()  # type: ignore[attr-defined]
    second = builder._build_spec()  # type: ignore[attr-defined]

    assert specs_equivalent(first, second)
    first.channels.pop("first")
    first.nodes.pop("a")
    first.edges.pop("__start__")
    first.node_records.pop("a")
    first.conditional_edges[0].path_map["a"] = "b"  # type: ignore[index]

    third = builder._build_spec()  # type: ignore[attr-defined]
    assert specs_equivalent(second, third)
    assert "first" in third.channels
    assert "a" in third.nodes
    assert "__start__" in third.edges
    assert "a" in third.node_records
    assert third.conditional_edges[0].path_map == {"a": "a", "b": "b", END: END}


def test_order_and_input_invariance() -> None:
    path_map: dict[str, str] = {"a": "a", "b": "b", END: END}
    metadata = {"tag": "original"}
    builder = StateGraph(RichState)
    builder.add_node("b", node_b, metadata=metadata)
    builder.add_node("a", node_a)
    builder.add_edge(START, "b")
    builder.add_edge("b", "a")
    builder.add_edge("a", END)
    builder.add_conditional_edges("b", router, path_map)

    path_map["a"] = "b"
    path_map["extra"] = "a"
    metadata["tag"] = "changed"
    spec = builder._build_spec()  # type: ignore[attr-defined]

    assert list(spec.channels) == ["first", "second", "branch:to:a", "branch:to:b"]
    assert list(spec.nodes) == ["b", "a"]
    assert list(spec.edges) == ["__start__", "b", "a"]
    assert spec.conditional_edges[0].path_map == {"a": "a", "b": "b", END: END}
    assert spec.conditional_edges[0].branch == "router"
    assert spec.node_records["b"].metadata == {"tag": "original"}


def test_channel_instances_are_fresh_per_snapshot() -> None:
    builder = _valid_builder()
    first = builder._build_spec()  # type: ignore[attr-defined]
    second = builder._build_spec()  # type: ignore[attr-defined]
    assert first.channels["first"] is not second.channels["first"]
    assert first.channels["branch:to:a"] is not second.channels["branch:to:a"]
