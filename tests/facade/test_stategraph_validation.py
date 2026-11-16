# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B6F1 构建期校验矩阵（US3 + BV-1…BV-13）。"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

import pytest

from freegraph.graph import END, START, StateGraph
from freegraph.runtime import EphemeralValue, InvalidSchemaError

from ._builder_support import State, node_a, node_b, router


class CallableNamed:
    """普通 callable 实例：只有 ``.name``，没有 ``__name__``。"""

    name = "not-a-node-name"

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        return {}


def _valid_base() -> StateGraph:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    return builder


def test_duplicate_node_is_immediate() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    with pytest.raises(ValueError, match="a"):
        builder.add_node("a", node_b)


def test_unknown_edge_target_is_reported_at_validate_with_valid_entry() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_edge(START, "a")
    builder.add_edge("a", "missing")
    with pytest.raises(ValueError, match="missing"):
        builder.validate()


def test_missing_entrypoint_is_reported() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_edge("a", END)
    with pytest.raises(ValueError, match="entrypoint|START"):
        builder.validate()


def test_conditional_start_counts_as_entrypoint() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_conditional_edges(START, router, {"a": "a"})
    builder.validate()


def test_invalid_schema_propagates_invalid_schema_error() -> None:
    builder = StateGraph({"count": 0})
    builder.add_node("a", node_a)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    with pytest.raises(InvalidSchemaError):
        builder.validate()


def test_empty_node_table_is_rejected() -> None:
    builder = StateGraph(State)
    builder.add_edge(START, END)
    with pytest.raises(ValueError, match="node|empty"):
        builder.validate()


def test_conditional_source_and_target_errors_are_at_validate() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_edge(START, "a")
    builder.add_conditional_edges(END, router, {"a": "a"})
    with pytest.raises(ValueError, match="END|unknown"):
        builder.validate()

    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_edge(START, "a")
    builder.add_conditional_edges("a", router, {"a": START})
    with pytest.raises(ValueError, match="START|__start__|unknown"):
        builder.validate()


def test_start_end_and_reserved_characters_are_immediate() -> None:
    builder = StateGraph(State)
    with pytest.raises(ValueError, match="reserved"):
        builder.add_node(START, node_a)
    with pytest.raises(ValueError, match="reserved"):
        builder.add_node(END, node_a)
    for name in ("bad|name", "bad:name"):
        with pytest.raises(ValueError, match="reserved character"):
            builder.add_node(name, node_a)

    builder.add_node("a", node_a)
    builder.add_node("b", node_b)
    with pytest.raises(ValueError, match="END"):
        builder.add_edge(END, "a")
    with pytest.raises(ValueError, match="START"):
        builder.add_edge("a", START)


def test_invalid_add_node_forms_raise_type_error() -> None:
    builder = StateGraph(State)
    with pytest.raises(TypeError):
        builder.add_node("a")
    with pytest.raises(TypeError):
        builder.add_node("a", 123)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        builder.add_node(123)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        builder.add_node(node_a, node_b)  # type: ignore[arg-type]


def test_invalid_edge_argument_types_raise_type_error() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    with pytest.raises(TypeError):
        builder.add_edge(123, "a")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        builder.add_edge("a", 123)  # type: ignore[arg-type]


def test_plain_callable_name_is_not_used_for_node_name() -> None:
    builder = StateGraph(State)
    builder.add_node(CallableNamed())
    builder.add_edge(START, "CallableNamed")
    builder.add_edge("CallableNamed", END)
    spec = builder._build_spec()  # type: ignore[attr-defined]
    assert "CallableNamed" in spec.nodes
    assert "not-a-node-name" not in spec.nodes


def test_multi_source_errors() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_node("b", node_b)
    with pytest.raises(ValueError):
        builder.add_edge([], "a")
    with pytest.raises(ValueError):
        builder.add_edge(["a", "missing"], "b")
    with pytest.raises(ValueError):
        builder.add_edge(["a", END], "b")
    with pytest.raises(ValueError):
        builder.add_edge(["a", "b"], "missing")


def test_multi_source_end_and_multi_target_are_retained() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_node("b", node_b)
    builder.add_node("c", node_a)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    builder.add_edge(["a", "b"], END)
    builder.add_edge(["a", "b"], "c")
    builder.validate()
    edges = builder._build_spec().edges  # type: ignore[attr-defined]
    assert edges[("a", "b")] == (END, "c")


def test_parent_reserved_name_is_retained_for_b7f2() -> None:
    builder = StateGraph(State)
    builder.add_node("__parent__", node_a)
    builder.add_edge(START, "__parent__")
    builder.add_edge("__parent__", END)
    builder.validate()
    spec = builder._build_spec()  # type: ignore[attr-defined]
    assert "__parent__" in spec.nodes
    assert "__parent__" in spec.node_records


def test_validate_interrupt_unknown_node() -> None:
    builder = _valid_base()
    with pytest.raises(ValueError, match="missing"):
        builder.validate(interrupt=["missing"])


def test_validate_failure_does_not_mutate_state_and_is_idempotent() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_edge(START, "a")
    builder.add_edge("a", "missing")
    before = {key: list(value) if isinstance(value, list) else dict(value) if isinstance(value, dict) else value for key, value in vars(builder).items()}
    with pytest.raises(ValueError):
        builder.validate()
    after = {key: list(value) if isinstance(value, list) else dict(value) if isinstance(value, dict) else value for key, value in vars(builder).items()}
    assert before == after

    builder._edges["a"] = [END]  # type: ignore[attr-defined]
    assert builder.validate() is builder
    assert builder.validate() is builder


def test_invalid_path_map_containers_elements_and_values() -> None:
    builder = _valid_base()
    for bad in (("a",), {"a"}, "a"):
        with pytest.raises(TypeError):
            builder.add_conditional_edges("a", router, bad)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        builder.add_conditional_edges("a", router, ["a", 3])  # type: ignore[list-item]
    with pytest.raises(TypeError):
        builder.add_conditional_edges("a", router, {"x": 3})  # type: ignore[dict-item]


def test_duplicate_branch_name_on_same_source_is_immediate() -> None:
    builder = _valid_base()
    builder.add_conditional_edges("a", router, ["a", END])
    with pytest.raises(ValueError, match="router"):
        builder.add_conditional_edges("a", router, ["a", END])


def test_route_channels_are_built_once_and_end_is_not_a_channel() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_node("b", node_b)
    builder.add_edge(START, "a")
    builder.add_conditional_edges("a", router, ["a", "b", END])
    spec = builder._build_spec()  # type: ignore[attr-defined]
    assert "branch:to:a" in spec.channels
    assert "branch:to:b" in spec.channels
    assert "branch:to:__end__" not in spec.channels
    assert isinstance(spec.channels["branch:to:a"], EphemeralValue)
    assert spec.channels["branch:to:a"].guard is False
    conditional = spec.conditional_edges[0]
    assert conditional.route_channels == ("branch:to:a", "branch:to:b")

def test_not_delivered_methods_raise_not_implemented() -> None:
    builder = StateGraph(State)
    for method, args in (
        ("add_sequence", ([],)),
        ("set_entry_point", ("a",)),
        ("set_conditional_entry_point", (router, ["a"])),
        ("set_finish_point", ("a",)),
        ("set_node_defaults", ()),
    ):
        with pytest.raises(NotImplementedError):
            getattr(builder, method)(*args)


def test_conditional_source_and_path_type_errors() -> None:
    builder = StateGraph(State)
    with pytest.raises(TypeError):
        builder.add_conditional_edges(123, router, ["a"])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        builder.add_conditional_edges("a", 123, ["a"])  # type: ignore[arg-type]


def test_multi_source_non_str_source_and_start_target() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    with pytest.raises(ValueError):
        builder.add_edge([123], "a")  # type: ignore[list-item]
    with pytest.raises(ValueError):
        builder.add_edge(["a"], START)


def test_unknown_single_source_is_reported_at_validate() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_edge("missing", "a")
    builder.add_edge(START, "a")
    with pytest.raises(ValueError, match="missing"):
        builder.validate()


def test_unknown_multi_source_in_internal_state_is_reported() -> None:
    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    builder._edges[("missing",)] = ["a"]  # type: ignore[attr-defined]
    with pytest.raises(ValueError, match="missing"):
        builder.validate()


def _broken_annotation(state: dict[str, Any]) -> "MissingType":  # type: ignore[name-defined]  # noqa: F821
    return "a"


def _non_str_literal(state: dict[str, Any]) -> Literal[1]:
    return 1


def test_path_map_inference_failure_and_non_str_literal_keep_none() -> None:
    for router_fn in (_broken_annotation, _non_str_literal):
        builder = StateGraph(State)
        builder.add_node("r", node_a)
        builder.add_node("a", node_b)
        builder.add_edge(START, "r")
        builder.add_conditional_edges("r", router_fn)  # type: ignore[arg-type]
        builder.validate()
        conditional = builder._build_spec().conditional_edges[0]  # type: ignore[attr-defined]
        assert conditional.path_map is None


def test_callable_with_empty_type_name_cannot_infer_node_name() -> None:
    empty = type("", (object,), {"__call__": lambda self, state: {}})()
    builder = StateGraph(State)
    with pytest.raises(ValueError):
        builder.add_node(empty)  # type: ignore[arg-type]
