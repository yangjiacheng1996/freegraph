# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B16F1 · 历史 checkpoint 重放 / 分叉不污染历史。"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

import pytest

from freegraph.contracts import RunConfig
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


def _run():
    saver = MemorySaver()
    compiled = _linear().compile(checkpointer=saver)
    compiled.invoke({"log": []}, {"thread_id": "t"})
    return compiled, saver


def _history(compiled) -> list:
    return list(compiled.get_state_history({"thread_id": "t"}))


def _id(config: RunConfig) -> str:
    value = config.configurable["checkpoint_id"]
    assert isinstance(value, str)
    return value


def test_replay_each_historical_checkpoint() -> None:
    compiled, _ = _run()
    original = _history(compiled)
    originals = {
        _id(snapshot.config): (
            dict(snapshot.values),
            tuple(snapshot.next),
            snapshot.created_at,
            snapshot.parent_config,
        )
        for snapshot in original
    }

    for snapshot in original:
        if not snapshot.next:
            continue
        result = compiled.invoke(None, snapshot.config)
        assert result["log"] == ["a", "b", "c"]
        assert result["x"] == 1

    for checkpoint_id, expected in originals.items():
        current = compiled.get_state(
            {
                "thread_id": "t",
                "configurable": {"checkpoint_id": checkpoint_id},
            }
        )
        assert current is not None
        assert (
            dict(current.values),
            tuple(current.next),
            current.created_at,
            current.parent_config,
        ) == expected


def test_normal_terminal_replay_is_noop() -> None:
    compiled, _ = _run()
    final = _history(compiled)[0]
    before = _history(compiled)
    result = compiled.invoke(None, final.config)
    assert result["log"] == ["a", "b", "c"]
    assert _history(compiled) == before


def test_missing_explicit_checkpoint_does_not_fall_back() -> None:
    compiled, _ = _run()
    with pytest.raises(ValueError, match="checkpoint_id"):
        compiled.invoke(
            None,
            {"thread_id": "t", "configurable": {"checkpoint_id": "9" * 32}},
        )


def test_replay_requires_saver_and_rejects_checkpoint_ns() -> None:
    no_saver = _linear().compile()
    with pytest.raises(ValueError, match="No checkpointer set"):
        no_saver.invoke(
            None,
            {"thread_id": "t", "configurable": {"checkpoint_id": "9" * 32}},
        )

    compiled, _ = _run()
    base = next(s for s in _history(compiled) if s.next == ("b",))
    with pytest.raises(ValueError, match="checkpoint_ns"):
        compiled.invoke(
            None,
            {
                "thread_id": "t",
                "configurable": {
                    "checkpoint_id": _id(base.config),
                    "checkpoint_ns": "sub",
                },
            },
        )


def test_non_noop_replay_writes_branch_anchor() -> None:
    compiled, saver = _run()
    base = next(s for s in _history(compiled) if s.next == ("b",))
    before = _history(compiled)

    compiled.invoke(None, base.config)
    after = _history(compiled)
    added = len(after) - len(before)
    assert added == 3  # anchor + b + c

    newest_first = after[:added]
    anchor = newest_first[-1]
    assert _id(anchor.parent_config) == _id(base.config)
    assert anchor.values == base.values
    assert anchor.next == base.next
    stored_anchor = saver.get_tuple(anchor.config).snapshot
    assert stored_anchor.interrupts == ()
    assert stored_anchor.tasks == ()

    first_execution = newest_first[1]
    assert first_execution.parent_config is not None
    assert _id(first_execution.parent_config) == _id(anchor.config)


def test_multiple_forks_have_independent_parents() -> None:
    compiled, _ = _run()
    base_b = next(s for s in _history(compiled) if s.next == ("b",))
    base_c = next(s for s in _history(compiled) if s.next == ("c",))

    fork1 = compiled.update_state(base_b.config, {"x": 1}, as_node="a")
    fork2 = compiled.update_state(base_c.config, {"x": 2}, as_node="b")
    branch1 = compiled.get_state(fork1)
    branch2 = compiled.get_state(fork2)
    assert branch1 is not None and branch2 is not None
    assert _id(branch1.parent_config) == _id(base_b.config)
    assert _id(branch2.parent_config) == _id(base_c.config)
    assert _id(fork1) != _id(fork2)
    assert len(_history(compiled)) >= 6


def test_fork_invoke_does_not_write_extra_anchor() -> None:
    compiled, _ = _run()
    base = next(s for s in _history(compiled) if s.next == ("b",))
    before = _history(compiled)

    fork = compiled.update_state(base.config, {"x": 99})
    after_fork = _history(compiled)
    assert len(after_fork) == len(before) + 1
    branch = after_fork[0]
    assert _id(branch.config) == _id(fork)

    compiled.invoke(None, fork)
    after_invoke = _history(compiled)
    assert len(after_invoke) == len(before) + 1 + 2  # branch + b + c; no anchor
    first_execution = after_invoke[1]
    assert first_execution.parent_config is not None
    assert _id(first_execution.parent_config) == _id(fork)
