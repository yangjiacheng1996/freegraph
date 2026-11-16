# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B7F2 编译期校验测试：14 项 MUST 查 + 7 项 MUST NOT 查 + 异常类型面。

覆盖 T022 / T023 / T024 / T025。
"""

from __future__ import annotations

import pytest

from freegraph.graph import END, START, Command, Send, StateGraph
from freegraph.runtime import InvalidSchemaError

from ._builder_support import RichState, State, node_a, node_b, router
from ._compiled_support import build_minimal_graph, capture_warnings


def _builder_with_nodes(*names: str) -> StateGraph:
    graph = StateGraph(State)
    for name in names:
        graph.add_node(name, node_a)
    return graph


def _with_entry(*names: str) -> StateGraph:
    graph = _builder_with_nodes(*names)
    graph.add_edge(START, names[0])
    return graph


# ── T022 · 3 类核心错误（SC-003）─────────────────────────────────────────


class TestCoreErrors:
    def test_unknown_static_edge_target(self) -> None:
        graph = _with_entry("a")
        graph.add_edge("a", "missing")
        with pytest.raises(ValueError) as excinfo:
            graph.compile()
        assert "missing" in str(excinfo.value)

    def test_unknown_conditional_source(self) -> None:
        graph = _with_entry("a")
        graph.add_conditional_edges("nope", router, ["a"])
        with pytest.raises(ValueError) as excinfo:
            graph.compile()
        assert "nope" in str(excinfo.value)

    def test_unknown_path_map_target(self) -> None:
        graph = _with_entry("a")
        graph.add_conditional_edges("a", router, {"x": "missing"})
        with pytest.raises(ValueError) as excinfo:
            graph.compile()
        message = str(excinfo.value)
        assert "a" in message and "router" in message and "missing" in message

    def test_failures_happen_at_the_compile_call_point(self) -> None:
        # 构造期不抛；只有 compile() 时抛
        graph = _with_entry("a")
        graph.add_edge("a", "missing")
        with pytest.raises(ValueError):
            graph.compile()


# ── T023 · CV-1…CV-14（SC-006）───────────────────────────────────────────


class TestValidationMatrix:
    def test_cv1_invalid_schema(self) -> None:
        with pytest.raises(InvalidSchemaError):
            StateGraph(dict).compile()

    def test_cv2_unknown_static_source(self) -> None:
        graph = _builder_with_nodes("a")
        graph.add_edge("ghost", "a")
        with pytest.raises(ValueError, match="ghost"):
            graph.compile()

    def test_cv3_missing_entrypoint(self) -> None:
        graph = _builder_with_nodes("a")
        with pytest.raises(ValueError, match="entrypoint"):
            graph.compile()

    def test_cv4_unknown_static_target(self) -> None:
        graph = _with_entry("a")
        graph.add_edge("a", "ghost")
        with pytest.raises(ValueError, match="ghost"):
            graph.compile()

    def test_cv5_unknown_conditional_source(self) -> None:
        graph = _with_entry("a")
        graph.add_conditional_edges("ghost", router, ["a"])
        with pytest.raises(ValueError, match="ghost"):
            graph.compile()

    def test_cv6_unknown_conditional_target(self) -> None:
        graph = _with_entry("a")
        graph.add_conditional_edges("a", router, ["ghost"])
        with pytest.raises(ValueError, match="ghost"):
            graph.compile()

    def test_cv7_empty_graph_fails(self) -> None:
        # 防御性：空图先命中 C-03（entrypoint）；仍 MUST 是 ValueError
        with pytest.raises(ValueError):
            StateGraph(State).compile()

    def test_cv8_positive_valid_subscriptions(self) -> None:
        compiled = build_minimal_graph().compile()
        for node in compiled._spec.nodes.values():
            assert set(node.subscribes) <= set(compiled._spec.channels)

    def test_cv9_reserved_parent_node_name(self) -> None:
        graph = StateGraph(State)
        graph.add_node("__parent__", node_a)
        graph.add_edge(START, "__parent__")
        graph.add_edge("__parent__", END)
        with pytest.raises(ValueError, match="__parent__"):
            graph.compile()

    def test_cv10_multi_source_end_target(self) -> None:
        graph = _with_entry("a")
        graph.add_node("b", node_b)
        graph.add_edge(["a", "b"], END)
        with pytest.raises(ValueError, match="V-16"):
            graph.compile()

    def test_cv10_multi_source_target_count_not_one(self) -> None:
        graph = _with_entry("a")
        for name in ("b", "c", "d"):
            graph.add_node(name, node_a)
        graph.add_edge(["a", "b"], "c")
        graph.add_edge(["a", "b"], "d")
        with pytest.raises(ValueError, match="V-16"):
            graph.compile()

    def test_cv11_container_shape_tuple(self) -> None:
        with pytest.raises(TypeError):
            build_minimal_graph().compile(interrupt_before=("a",))

    def test_cv12_element_level_empty_string(self) -> None:
        with pytest.raises(ValueError):
            build_minimal_graph().compile(interrupt_before=[""])

    def test_cv13_path_map_shape_fails_before_compile(self) -> None:
        graph = _with_entry("a")
        with pytest.raises(TypeError):
            graph.add_conditional_edges("a", router, ("a",))

    def test_cv14_path_map_unknown_target(self) -> None:
        graph = _with_entry("a")
        graph.add_conditional_edges("a", router, {"x": "ghost"})
        with pytest.raises(ValueError, match="ghost"):
            graph.compile()


# ── T024 · NV-1…NV-7（MUST NOT 查）───────────────────────────────────────


class TestNotChecked:
    def test_nv1_dynamic_path_map_none_compiles(self) -> None:
        graph = _with_entry("a")
        graph.add_node("b", node_b)
        graph.add_conditional_edges("a", router, None)
        graph.add_edge("b", END)
        compiled = graph.compile()
        assert compiled._conditional_edges["a"][0]["path_map"] is None

    def test_nv2_node_return_shapes_compile(self) -> None:
        graph = StateGraph(State)
        graph.add_node("command", lambda state: Command(goto="plain"))
        graph.add_node("send", lambda state: Send("plain", {}))
        graph.add_node("plain", lambda state: None)
        graph.add_edge(START, "command")
        graph.add_edge("plain", END)
        graph.compile()

    def test_nv3_unreachable_node_compiles(self) -> None:
        graph = build_minimal_graph()
        graph.add_node("island", node_a)
        graph.compile()

    def test_nv4_self_loop_compiles(self) -> None:
        graph = build_minimal_graph()
        graph.add_edge("a", "a")
        graph.compile()

    def test_nv5_non_conforming_checkpointer_and_store_compile(self) -> None:
        with capture_warnings() as caught:
            build_minimal_graph().compile(
                checkpointer=object(), store=object()
            )
        assert len(caught) == 1

    def test_nv6_valid_schemas_compile(self) -> None:
        graph = StateGraph(RichState)
        graph.add_node("a", node_a)
        graph.add_edge(START, "a")
        graph.add_edge("a", END)
        graph.compile()

    def test_nv7_arbitrary_hashable_path_map_keys_compile(self) -> None:
        graph = _with_entry("a")
        graph.add_node("b", node_b)
        graph.add_conditional_edges("a", router, {1: "b", ("x",): "b"})
        graph.add_edge("b", END)
        graph.compile()


# ── T025 · 异常类型面（FR-018 / SC-003）─────────────────────────────────


class TestExceptionSurface:
    def test_schema_error_is_invalid_schema_error(self) -> None:
        with pytest.raises(InvalidSchemaError):
            StateGraph(dict).compile()

    def test_unknown_target_is_exactly_value_error(self) -> None:
        graph = _with_entry("a")
        graph.add_edge("a", "ghost")
        with pytest.raises(ValueError) as excinfo:
            graph.compile()
        assert type(excinfo.value) is ValueError

    def test_container_gate_is_exactly_type_error(self) -> None:
        with pytest.raises(TypeError) as excinfo:
            build_minimal_graph().compile(interrupt_before=("a",))
        assert type(excinfo.value) is TypeError
