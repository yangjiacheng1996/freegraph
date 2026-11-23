# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B16F1 · ``CompiledGraph.update_state`` facade 行为。"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

import pytest

from freegraph.contracts import InvalidUpdateError, RunConfig
from freegraph.graph import END, START, StateGraph
from freegraph.persistence import MemorySaver


class _State(TypedDict):
    x: int
    log: Annotated[list, operator.add]


def _a(state: dict) -> dict:
    return {"log": ["a"], "x": 1}


def _b(state: dict) -> dict:
    return {"log": ["b"]}


def _c(state: dict) -> dict:
    return {"log": ["c"]}


def _linear() -> StateGraph:
    graph = StateGraph(_State)
    graph.add_node("a", _a)
    graph.add_node("b", _b)
    graph.add_node("c", _c)
    graph.add_edge(START, "a")
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", END)
    return graph


def _single() -> StateGraph:
    graph = StateGraph(_State)
    graph.add_node("only", _a)
    graph.add_edge(START, "only")
    graph.add_edge("only", END)
    return graph


def _run(graph: StateGraph, saver: MemorySaver | None = None):
    saver = saver or MemorySaver()
    compiled = graph.compile(checkpointer=saver)
    compiled.invoke({"log": []}, {"thread_id": "t"})
    return compiled, saver


def _history(compiled) -> list:
    return list(compiled.get_state_history({"thread_id": "t"}))


def _id(config: RunConfig) -> str:
    value = config.configurable["checkpoint_id"]
    assert isinstance(value, str)
    return value


def _snapshot_with_next(compiled, node: str):
    return next(s for s in _history(compiled) if s.next == (node,))


def test_update_state_returns_new_branch_and_parent_points_to_base() -> None:
    compiled, _ = _run(_linear())
    base = _snapshot_with_next(compiled, "b")
    before = _history(compiled)

    fork = compiled.update_state(base.config, {"x": 99})
    assert isinstance(fork, RunConfig)
    assert _id(fork)
    branch = compiled.get_state(fork)
    assert branch is not None
    assert branch.values["x"] == 99
    assert branch.next == ("b",)
    assert branch.parent_config is not None
    assert _id(branch.parent_config) == _id(base.config)
    assert _history(compiled)[1:] == before


def test_update_state_uses_c6_reducers_and_overrides() -> None:
    compiled, _ = _run(_linear())
    base = _snapshot_with_next(compiled, "b")

    fork = compiled.update_state(
        base.config, {"x": 7, "log": ["fork"]}
    )
    branch = compiled.get_state(fork)
    assert branch is not None
    assert branch.values["x"] == 7
    assert branch.values["log"] == ["a", "fork"]


def test_update_state_unknown_key_is_atomic() -> None:
    compiled, _ = _run(_linear())
    base = _snapshot_with_next(compiled, "b")
    before = _history(compiled)

    with pytest.raises(InvalidUpdateError) as excinfo:
        compiled.update_state(base.config, {"nope": 1})
    assert excinfo.value.invalid_keys == ("nope",)
    assert _history(compiled) == before


def test_update_state_explicit_as_node_controls_successors() -> None:
    compiled, _ = _run(_linear())
    base = _snapshot_with_next(compiled, "b")

    fork = compiled.update_state(base.config, {"x": 5}, as_node="a")
    branch = compiled.get_state(fork)
    assert branch is not None
    assert branch.next == ("b",)
    result = compiled.invoke(None, fork)
    assert result["log"] == ["a", "b", "c"]
    assert result["x"] == 5


def test_update_state_omitted_as_node_infers_last_updater() -> None:
    compiled, _ = _run(_linear())
    base = _snapshot_with_next(compiled, "b")

    fork = compiled.update_state(base.config, {"x": 3})
    branch = compiled.get_state(fork)
    assert branch is not None
    assert branch.next == ("b",)


def test_update_state_single_node_fallback() -> None:
    compiled, _ = _run(_single())
    terminal = _history(compiled)[0]
    fork = compiled.update_state(terminal.config, {"x": 2})
    branch = compiled.get_state(fork)
    assert branch is not None
    assert branch.values["x"] == 2


def test_update_state_config_carriers_and_failures() -> None:
    compiled, _ = _run(_linear())
    base = _snapshot_with_next(compiled, "b")
    base_id = _id(base.config)
    assert isinstance(
        compiled.update_state(
            RunConfig(
                thread_id="t",
                configurable={"checkpoint_id": base_id},
            ),
            {"x": 1},
        ),
        RunConfig,
    )
    assert isinstance(
        compiled.update_state(
            {"thread_id": "t", "configurable": {"checkpoint_id": base_id}},
            {"x": 2},
        ),
        RunConfig,
    )
    with pytest.raises(ValueError):
        compiled.update_state(None, {"x": 1})
    with pytest.raises(TypeError):
        compiled.update_state("t", {"x": 1})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        compiled.update_state(123, {"x": 1})  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        compiled.update_state(
            {"thread_id": "t", "configurable": {"checkpoint_ns": "sub"}},
            {"x": 1},
        )


def test_update_state_requires_saver_and_existing_base() -> None:
    graph = _linear()
    no_saver = graph.compile()
    with pytest.raises(ValueError, match="No checkpointer set"):
        no_saver.update_state({"thread_id": "t"}, {"x": 1})

    compiled, _ = _run(_linear())
    with pytest.raises(ValueError, match="thread_id"):
        compiled.update_state({}, {"x": 1})
    with pytest.raises(ValueError, match="checkpoint_id"):
        compiled.update_state(
            {"thread_id": "t", "configurable": {"checkpoint_id": "9" * 32}},
            {"x": 1},
        )


def test_update_state_rejects_non_mapping_values_and_bad_as_node() -> None:
    compiled, _ = _run(_linear())
    cfg = {"thread_id": "t"}
    with pytest.raises(TypeError):
        compiled.update_state(cfg, None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        compiled.update_state(cfg, {"x": 1}, as_node=123)  # type: ignore[arg-type]
    with pytest.raises(InvalidUpdateError, match="missing"):
        compiled.update_state(cfg, {"x": 1}, as_node="missing")


def test_v1_capability_boundaries() -> None:
    compiled, _ = _run(_linear())
    cfg = {"thread_id": "t"}
    with pytest.raises(TypeError):
        compiled.update_state(cfg, {}, task_id="task")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        compiled.update_state(cfg, None)  # type: ignore[arg-type]

    fresh = _linear().compile(checkpointer=MemorySaver())
    with pytest.raises(ValueError):
        fresh.update_state({"thread_id": "fresh"}, {"x": 1})

    # v1 不提供分支树 / 按分支枚举 / async API
    for name in ("get_state_tree", "get_branches", "aupdate_state"):
        assert not hasattr(compiled, name)


def test_update_state_does_not_persist_context() -> None:
    compiled, saver = _run(_linear())
    base = _snapshot_with_next(compiled, "b")
    fork = compiled.update_state(
        RunConfig(
            thread_id="t",
            context={"secret": 1},
            configurable={"checkpoint_id": _id(base.config)},
        ),
        {"x": 4},
    )
    snapshot = compiled.get_state(fork)
    assert snapshot is not None
    assert snapshot.config.context is None
    assert "secret" not in repr(snapshot.metadata)
