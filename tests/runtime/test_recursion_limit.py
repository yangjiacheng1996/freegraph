# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B13F1 · ``recursion_limit`` 的载体 / 默认值 / 校验 / 计数 / 错误。"""

from __future__ import annotations

import inspect

import pytest

from freegraph.contracts import GraphRecursionError, RunConfig, Send
from freegraph.runtime import GraphSpec, NodeSpec, SchedulerState, run_graph
from freegraph.runtime.channel import LastValue
from freegraph.runtime._recursion import (
    DEFAULT_RECURSION_LIMIT,
    resolve_config,
    resolve_limit,
    validate_limit,
)


def _loop_spec() -> GraphSpec:
    def loop(state: dict) -> dict:
        return {"count": state.get("count", 0) + 1}

    return GraphSpec(
        channels={"count": LastValue("count", int)},
        nodes={"loop": NodeSpec(("count",), loop)},
        edges={"__start__": ("loop",), "loop": ("loop",)},
    )


def _chain_spec(length: int) -> GraphSpec:
    nodes: dict[str, NodeSpec] = {}
    edges: dict[str, tuple[str, ...]] = {}
    for index in range(length):
        name = f"n{index}"
        nodes[name] = NodeSpec((), lambda state: {})
        edges["__start__" if index == 0 else f"n{index - 1}"] = (name,)
    return GraphSpec(
        channels={"count": LastValue("count", int)},
        nodes=nodes,
        edges=edges,
    )


def test_default_constant_is_10007() -> None:
    assert DEFAULT_RECURSION_LIMIT == 10007


def test_dict_carrier_raises_graph_recursion_error() -> None:
    with pytest.raises(GraphRecursionError) as exc:
        run_graph(_loop_spec(), {"count": 0}, config={"recursion_limit": 3})
    assert exc.value.recursion_limit == 3
    assert exc.value.current_step == 3
    assert "recursion" in str(exc.value).lower()


def test_runconfig_carrier_raises_graph_recursion_error() -> None:
    with pytest.raises(GraphRecursionError) as exc:
        run_graph(_loop_spec(), {"count": 0}, config=RunConfig(recursion_limit=3))
    assert exc.value.recursion_limit == 3


def test_dict_carrier_beats_max_steps() -> None:
    with pytest.raises(GraphRecursionError) as exc:
        run_graph(
            _loop_spec(),
            {"count": 0},
            config={"recursion_limit": 3},
            max_steps=100,
        )
    assert exc.value.recursion_limit == 3


def test_runconfig_carrier_beats_max_steps() -> None:
    with pytest.raises(GraphRecursionError) as exc:
        run_graph(
            _loop_spec(),
            {"count": 0},
            config=RunConfig(recursion_limit=3),
            max_steps=100,
        )
    assert exc.value.recursion_limit == 3


def test_none_means_absent_and_falls_back_to_max_steps() -> None:
    with pytest.raises(GraphRecursionError) as exc:
        run_graph(
            _loop_spec(),
            {"count": 0},
            config={"recursion_limit": None},
            max_steps=2,
        )
    assert exc.value.recursion_limit == 2


@pytest.mark.parametrize("value", [0, -1])
def test_values_below_one_raise_value_error(value: int) -> None:
    with pytest.raises(ValueError):
        run_graph(_loop_spec(), {"count": 0}, config={"recursion_limit": value})


@pytest.mark.parametrize("value", [True, 1.5, "3"])
def test_non_int_values_raise_type_error(value: object) -> None:
    with pytest.raises(TypeError):
        run_graph(_loop_spec(), {"count": 0}, config={"recursion_limit": value})


def test_validation_happens_before_running_any_task() -> None:
    spec = GraphSpec(
        channels={"count": LastValue("count", int)},
        nodes={"loop": NodeSpec(("count",), lambda state: {"count": 1})},
        edges={},
    )
    with pytest.raises(ValueError):
        run_graph(spec, config={"recursion_limit": 0})


def test_unknown_dict_keys_are_ignored_and_thread_id_is_preserved() -> None:
    config = resolve_config(
        {"recursion_limit": 3, "thread_id": "t-1", "unknown": object()}
    )
    assert config.recursion_limit == 3
    assert config.resolved_thread_id() == "t-1"


def test_default_does_not_report_at_25_rounds() -> None:
    result = run_graph(_chain_spec(30), {"count": 0})
    assert result.steps >= 30


def test_environment_variable_does_not_change_default(monkeypatch) -> None:
    monkeypatch.setenv("LANGGRAPH_DEFAULT_RECURSION_LIMIT", "1")
    result = run_graph(_chain_spec(30), {"count": 0})
    assert result.steps >= 30


def test_fanout_round_counts_toward_the_limit() -> None:
    def fan(state: dict) -> list[Send]:
        return [Send("worker", {"n": 1})]

    def worker(state: dict) -> dict:
        return {"out": [state["n"]]}

    spec = GraphSpec(
        channels={"out": LastValue("out", list)},
        nodes={"fan": NodeSpec((), fan), "worker": NodeSpec((), worker)},
        edges={"__start__": ("fan",)},
    )
    with pytest.raises(GraphRecursionError) as exc:
        run_graph(spec, config={"recursion_limit": 1})
    assert exc.value.recursion_limit == 1


def test_error_is_not_wrapped() -> None:
    with pytest.raises(GraphRecursionError):
        run_graph(_loop_spec(), {"count": 0}, config={"recursion_limit": 3})


def test_run_graph_has_no_explicit_recursion_limit_keyword() -> None:
    assert "recursion_limit" not in inspect.signature(run_graph).parameters


def test_resolve_limit_and_validate_limit_are_pure() -> None:
    assert resolve_limit(None, 7) == 7
    assert resolve_limit(3, 7) == 3
    assert validate_limit(1) == 1
    with pytest.raises(TypeError):
        validate_limit(True)
    with pytest.raises(ValueError):
        validate_limit(0)


def test_repeated_runs_are_deterministic() -> None:
    errors = []
    for _ in range(3):
        with pytest.raises(GraphRecursionError) as exc:
            run_graph(_loop_spec(), {"count": 0}, config={"recursion_limit": 3})
        errors.append((exc.value.recursion_limit, exc.value.current_step))
    assert errors == [(3, 3), (3, 3), (3, 3)]


def test_resolve_config_rejects_unsupported_types() -> None:
    with pytest.raises(TypeError):
        resolve_config(object())  # type: ignore[arg-type]
