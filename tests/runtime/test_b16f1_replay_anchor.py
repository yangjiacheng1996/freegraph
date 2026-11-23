# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B16F1 · branch anchor / 父链 / 正常终态 no-op（runtime 层）。"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from freegraph.graph import END, START, StateGraph
from freegraph.persistence import MemorySaver


class _State(TypedDict):
    log: Annotated[list, operator.add]


def _a(state: dict) -> dict:
    return {"log": ["a"]}


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


def _run(**compile_kwargs):
    saver = MemorySaver()
    compiled = _linear().compile(checkpointer=saver, **compile_kwargs)
    compiled.invoke({"log": []}, {"thread_id": "t"})
    return compiled, saver


def _history(compiled) -> list:
    return list(compiled.get_state_history({"thread_id": "t"}))


def _id(config) -> str:
    value = config.configurable["checkpoint_id"]
    assert isinstance(value, str)
    return value


def test_replay_anchor_fields_and_parent_chain() -> None:
    compiled, saver = _run()
    base = next(s for s in _history(compiled) if s.next == ("b",))
    before = _history(compiled)

    compiled.invoke(None, base.config)
    after = _history(compiled)
    added = len(after) - len(before)
    assert added == 3

    anchor = after[added - 1]
    stored = saver.get_tuple(anchor.config).snapshot
    assert _id(anchor.parent_config) == _id(base.config)
    assert stored.values == base.values
    assert stored.next == base.next
    assert stored.interrupts == ()
    assert stored.tasks == ()
    assert saver.get_tuple(anchor.config).pending_writes == ()


def test_normal_terminal_replay_has_no_anchor() -> None:
    compiled, _ = _run()
    final = _history(compiled)[0]
    before = _history(compiled)
    compiled.invoke(None, final.config)
    assert _history(compiled) == before


def test_static_after_next_empty_writes_anchor_then_completion() -> None:
    compiled, saver = _run(interrupt_after=["c"])
    paused = _history(compiled)[0]
    assert paused.next == ()
    before = _history(compiled)

    compiled.invoke(None, paused.config)
    after = _history(compiled)
    assert len(after) == len(before) + 2  # anchor + completion
    anchor = after[1]
    assert _id(anchor.parent_config) == _id(paused.config)
    assert saver.get_tuple(after[0].config).scheduler["suspension_kind"] is None


def test_b7f3_continuation_with_historical_config_writes_anchor() -> None:
    compiled, _ = _run()
    base = next(s for s in _history(compiled) if s.next == ("b",))
    before = _history(compiled)

    result = compiled.invoke({"log": ["injected"]}, base.config)
    assert "injected" in result["log"]
    after = _history(compiled)
    assert len(after) > len(before)
    # 第一条新增快照（最老的新增）是 anchor：parent = base
    added = len(after) - len(before)
    anchor = after[added - 1]
    assert _id(anchor.parent_config) == _id(base.config)


def test_fork_invoke_has_no_extra_anchor() -> None:
    compiled, _ = _run()
    base = next(s for s in _history(compiled) if s.next == ("b",))
    before = _history(compiled)
    fork = compiled.update_state(base.config, {"log": ["fork"]}, as_node="a")
    compiled.invoke(None, fork)
    after = _history(compiled)
    assert len(after) == len(before) + 1 + 2  # branch + b + c
    first_execution = after[1]
    assert _id(first_execution.parent_config) == _id(fork)
