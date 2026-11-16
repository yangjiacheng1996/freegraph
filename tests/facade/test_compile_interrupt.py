# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B7F2 静态断点测试：6 形态 / 逐字同款 / 归一值可见。

覆盖 T027 / T028 / T029。
"""

from __future__ import annotations

from typing import Any

import pytest

from freegraph.graph import END, START, StateGraph
from freegraph.runtime._static import normalize_static_points

from ._builder_support import State, node_a, node_b
from ._compiled_support import build_minimal_graph


def _nodes() -> dict[str, Any]:
    return {"a": None, "b": None}


def _compile_error(value: Any, field: str = "interrupt_before") -> BaseException:
    graph = build_minimal_graph()
    try:
        graph.compile(**{field: value})
    except BaseException as exc:  # noqa: BLE001 - 需要拿到原始异常做逐字比较
        return exc
    raise AssertionError(f"{field}={value!r} 未抛异常")


def _reference_error(value: Any, field: str = "interrupt_before") -> BaseException:
    try:
        normalize_static_points(value, _nodes(), field)
    except BaseException as exc:  # noqa: BLE001
        return exc
    raise AssertionError(f"normalize_static_points({value!r}) 未抛异常")


# ── T027 · 6 种形态（SC-007）─────────────────────────────────────────────


class TestStaticInterruptForms:
    def test_none_becomes_empty_tuple(self) -> None:
        compiled = build_minimal_graph().compile(interrupt_before=None)
        assert compiled.interrupt_before_nodes == ()

    def test_star_expands_to_all_executable_nodes(self) -> None:
        compiled = build_minimal_graph().compile(interrupt_before="*")
        assert compiled.interrupt_before_nodes == ("a", "b")

    def test_list_is_deduplicated_and_order_preserved(self) -> None:
        compiled = build_minimal_graph().compile(interrupt_before=["b", "a", "b"])
        assert compiled.interrupt_before_nodes == ("b", "a")

    @pytest.mark.parametrize("bad", [("a",), {"a"}, 1, 1.5])
    def test_container_forms_raise_type_error(self, bad: Any) -> None:
        with pytest.raises(TypeError):
            build_minimal_graph().compile(interrupt_before=bad)

    def test_bare_non_star_string_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            build_minimal_graph().compile(interrupt_before="a")

    def test_unknown_node_raises_value_error_naming_it(self) -> None:
        with pytest.raises(ValueError) as excinfo:
            build_minimal_graph().compile(interrupt_before=["nope"])
        assert "nope" in str(excinfo.value)

    @pytest.mark.parametrize("bad", [["*"], [""]])
    def test_illegal_elements_raise_value_error(self, bad: list[str]) -> None:
        with pytest.raises(ValueError):
            build_minimal_graph().compile(interrupt_before=bad)


# ── T028 · 逐字同款（B13F1 D-2）──────────────────────────────────────────


class TestByteEqualityWithGraphSpec:
    @pytest.mark.parametrize(
        "value",
        ["", "a", [""], ["__start__"], ["__end__"], ["*"], ["nope"], [123]],
        ids=[
            "bare-empty",
            "bare-a",
            "element-empty",
            "element-start",
            "element-end",
            "element-star",
            "unknown-node",
            "non-str",
        ],
    )
    def test_message_is_byte_identical(self, value: Any) -> None:
        raised = _compile_error(value)
        reference = _reference_error(value)
        assert type(raised) is type(reference)
        assert str(raised) == str(reference)

    @pytest.mark.parametrize("value", [("a",), {"a"}, 1, 1.5])
    def test_container_forms_only_require_type_error(self, value: Any) -> None:
        with pytest.raises(TypeError):
            build_minimal_graph().compile(interrupt_before=value)


# ── T029 · 公开属性（X-11）──────────────────────────────────────────────


class TestPublicInterruptAttributes:
    def test_star_is_expanded_on_the_public_attribute(self) -> None:
        compiled = build_minimal_graph().compile(interrupt_before="*")
        assert compiled.interrupt_before_nodes == ("a", "b")

    def test_none_is_empty_tuple_on_the_public_attribute(self) -> None:
        compiled = build_minimal_graph().compile(interrupt_before=None)
        assert compiled.interrupt_before_nodes == ()

    def test_before_and_after_are_validated_independently(self) -> None:
        graph = StateGraph(State)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge(START, "a")
        graph.add_edge("a", "b")
        graph.add_edge("b", END)
        compiled = graph.compile(
            interrupt_before=["a"], interrupt_after=["b"]
        )
        assert compiled.interrupt_before_nodes == ("a",)
        assert compiled.interrupt_after_nodes == ("b",)
