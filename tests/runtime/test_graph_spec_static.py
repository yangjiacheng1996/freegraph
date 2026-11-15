# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B13F1 · ``GraphSpec`` 静态断点字段的归一 / 校验 / 防御性拷贝（V-22…V-26）。"""

from __future__ import annotations

import inspect

import pytest

from freegraph.runtime import GraphSpec, NodeSpec, SchedulerState
from freegraph.runtime import run_super_step, run_super_steps
from freegraph.runtime.channel import LastValue


def _node() -> NodeSpec:
    return NodeSpec((), lambda state: {})


def _spec(**kwargs) -> GraphSpec:
    return GraphSpec(
        channels={"x": LastValue("x", int)},
        nodes={"a": _node(), "b": _node(), "review": _node()},
        edges={"__start__": ("a",)},
        **kwargs,
    )


def test_static_fields_default_to_empty_tuples() -> None:
    spec = _spec()
    assert spec.interrupt_before == ()
    assert spec.interrupt_after == ()


def test_bare_star_expands_to_executable_nodes_in_node_table_order() -> None:
    spec = _spec(interrupt_before="*", interrupt_after="*")
    assert spec.interrupt_before == ("a", "b", "review")
    assert spec.interrupt_after == ("a", "b", "review")


def test_sequence_is_normalized_deduplicated_and_stored_as_tuple() -> None:
    spec = _spec(interrupt_before=["b", "a", "b"])
    assert spec.interrupt_before == ("b", "a")


def test_fields_are_defensively_copied() -> None:
    points = ["b", "a"]
    spec = _spec(interrupt_before=points)
    points.append("review")
    assert spec.interrupt_before == ("b", "a")


@pytest.mark.parametrize("value", ["", "a", "__start__", "__end__"])
def test_bare_non_star_string_is_rejected(value: str) -> None:
    with pytest.raises(TypeError):
        _spec(interrupt_before=value)


def test_none_is_rejected() -> None:
    with pytest.raises(TypeError):
        _spec(interrupt_before=None)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [1, ["a", 1], {"a"}])
def test_non_sequence_or_non_string_elements_are_rejected(value: object) -> None:
    with pytest.raises(TypeError):
        _spec(interrupt_before=value)  # type: ignore[arg-type]


def test_mapping_is_rejected() -> None:
    with pytest.raises(TypeError):
        _spec(interrupt_before={"a": 1})  # type: ignore[arg-type]


def test_empty_element_is_rejected() -> None:
    with pytest.raises(ValueError):
        _spec(interrupt_before=["a", ""])


@pytest.mark.parametrize("element", ["__start__", "__end__", "*"])
def test_sequence_sentinels_and_star_element_are_rejected(element: str) -> None:
    with pytest.raises(ValueError):
        _spec(interrupt_before=["a", element])


def test_unknown_node_is_rejected_and_named() -> None:
    with pytest.raises(ValueError) as exc:
        _spec(interrupt_before=["nope"])
    assert "nope" in str(exc.value)


def test_empty_sequence_disables_the_feature() -> None:
    spec = _spec(interrupt_before=[], interrupt_after=())
    assert spec.interrupt_before == ()
    assert spec.interrupt_after == ()


def test_low_level_entries_reject_non_empty_static_fields() -> None:
    spec = _spec(interrupt_before=("a",))
    with pytest.raises(ValueError) as exc:
        run_super_step(spec, SchedulerState())
    assert "run_graph" in str(exc.value)
    with pytest.raises(ValueError) as exc:
        run_super_steps(spec)
    assert "run_graph" in str(exc.value)


def test_low_level_entry_signatures_are_unchanged() -> None:
    single = inspect.signature(run_super_step)
    multi = inspect.signature(run_super_steps)
    assert list(single.parameters) == ["spec", "state", "max_concurrency"]
    assert list(multi.parameters) == ["spec", "state", "max_steps", "max_concurrency"]


def test_normalization_accepts_an_iterable_of_node_names() -> None:
    from freegraph.runtime._static import normalize_static_points

    assert normalize_static_points("*", ["a", "b"], "interrupt_before") == ("a", "b")
