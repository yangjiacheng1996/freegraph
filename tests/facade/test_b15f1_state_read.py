# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B15F1 · ``CompiledGraph.get_state`` / ``get_state_history`` 行为。"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

import pytest

from freegraph.contracts import RunConfig
from freegraph.graph import END, START, StateGraph, interrupt
from freegraph.persistence import MemorySaver, SqliteSaver


class _State(TypedDict):
    log: Annotated[list, operator.add]


def _a(state: dict) -> dict:
    return {"log": ["a"]}


def _b(state: dict) -> dict:
    return {"log": ["b"]}


def _linear() -> StateGraph:
    graph = StateGraph(_State)
    graph.add_node("a", _a)
    graph.add_node("b", _b)
    graph.add_edge(START, "a")
    graph.add_edge("a", "b")
    graph.add_edge("b", END)
    return graph


def _interrupting() -> StateGraph:
    def ask(state: dict) -> dict:
        interrupt({"ask": "approve"})
        return {"log": ["asked"]}

    graph = StateGraph(_State)
    graph.add_node("ask", ask)
    graph.add_edge(START, "ask")
    graph.add_edge("ask", END)
    return graph


def _sqlite() -> SqliteSaver:
    import sqlite3

    return SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))


def test_get_state_fields_and_config_context_none() -> None:
    saver = _sqlite()
    compiled = _linear().compile(checkpointer=saver)
    compiled.invoke({"log": []}, {"thread_id": "t"})
    snapshot = compiled.get_state({"thread_id": "t"})
    assert snapshot is not None
    assert snapshot.values == {"log": ["a", "b"]}
    assert snapshot.next == ()
    assert snapshot.tasks == ()
    assert snapshot.interrupts == ()
    assert snapshot.config.configurable["checkpoint_id"]
    assert snapshot.config.context is None
    assert snapshot.parent_config is not None


def test_get_state_config_carriers_and_failures() -> None:
    saver = _sqlite()
    compiled = _linear().compile(checkpointer=saver)
    compiled.invoke({"log": []}, {"thread_id": "t"})
    # RunConfig / Mapping accepted
    assert compiled.get_state(RunConfig(thread_id="t")) is not None
    assert compiled.get_state({"thread_id": "t"}) is not None
    # None only type-level: missing thread_id -> ValueError
    with pytest.raises(ValueError):
        compiled.get_state(None)
    with pytest.raises(ValueError):
        compiled.get_state({})
    # bare str / number -> TypeError
    with pytest.raises(TypeError):
        compiled.get_state("t")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        compiled.get_state(123)  # type: ignore[arg-type]
    # non-empty checkpoint_ns -> ValueError
    with pytest.raises(ValueError):
        compiled.get_state({"thread_id": "t", "configurable": {"checkpoint_ns": "sub"}})


def test_get_state_without_saver_raises() -> None:
    compiled = _linear().compile()
    with pytest.raises(ValueError, match="No checkpointer set"):
        compiled.get_state({"thread_id": "t"})
    with pytest.raises(ValueError, match="No checkpointer set"):
        compiled.get_state_history({"thread_id": "t"})


def test_get_state_unknown_thread_returns_none_and_empty_history() -> None:
    saver = _sqlite()
    compiled = _linear().compile(checkpointer=saver)
    assert compiled.get_state({"thread_id": "missing"}) is None
    assert list(compiled.get_state_history({"thread_id": "missing"})) == []


def test_pending_writes_merge_only_without_checkpoint_id() -> None:
    saver = _sqlite()
    compiled = _linear().compile(checkpointer=saver)
    compiled.invoke({"log": []}, {"thread_id": "t"})

    latest = saver.get_tuple(RunConfig(thread_id="t"))
    assert latest is not None
    latest_id = latest.snapshot.config.configurable["checkpoint_id"]
    saver.put_writes(
        RunConfig(thread_id="t", configurable={"checkpoint_id": latest_id}),
        writes=[("log", ["pending"]), ("__error__", "ignored")],
        task_id="a",
    )

    merged = compiled.get_state({"thread_id": "t"})
    assert merged is not None
    assert merged.values["log"] == ["a", "b", "pending"]

    by_id = compiled.get_state(
        {"thread_id": "t", "configurable": {"checkpoint_id": latest_id}}
    )
    assert by_id is not None
    assert by_id.values["log"] == ["a", "b"]

    history_first = list(compiled.get_state_history({"thread_id": "t"}))[0]
    assert history_first.values["log"] == ["a", "b"]


def test_get_state_none_checkpoint_id_is_unspecified() -> None:
    saver = _sqlite()
    compiled = _linear().compile(checkpointer=saver)
    compiled.invoke({"log": []}, {"thread_id": "t"})
    latest = saver.get_tuple(RunConfig(thread_id="t"))
    assert latest is not None
    latest_id = latest.snapshot.config.configurable["checkpoint_id"]
    saver.put_writes(
        RunConfig(thread_id="t", configurable={"checkpoint_id": latest_id}),
        writes=[("log", ["pending"])],
        task_id="a",
    )
    via_none = compiled.get_state(
        {"thread_id": "t", "configurable": {"checkpoint_id": None}}
    )
    assert via_none is not None
    assert via_none.values["log"] == ["a", "b", "pending"]


def test_dynamic_interrupt_matches_invoke_interrupt_tuple() -> None:
    saver = _sqlite()
    compiled = _interrupting().compile(checkpointer=saver)
    result = compiled.invoke({"log": []}, {"thread_id": "t"})
    expected = tuple(result["__interrupt__"])
    snapshot = compiled.get_state({"thread_id": "t"})
    assert snapshot is not None
    assert snapshot.interrupts == expected
    assert len(snapshot.tasks) == 1
    task = snapshot.tasks[0]
    assert task.name == "ask"
    assert task.id == "ask"
    assert task.interrupts == expected
    assert len(expected[0].__dataclass_fields__) == 2


def test_static_suspension_interrupts_empty_and_tasks_projected() -> None:
    saver = _sqlite()
    compiled = _linear().compile(checkpointer=saver, interrupt_before=["b"])
    compiled.invoke({"log": []}, {"thread_id": "t"})
    snapshot = compiled.get_state({"thread_id": "t"})
    assert snapshot is not None
    assert snapshot.next == ("b",)
    assert snapshot.interrupts == ()
    assert len(snapshot.tasks) == 1
    assert snapshot.tasks[0].id == "b"
    assert snapshot.tasks[0].interrupts == ()


def test_history_count_order_and_by_id_equality() -> None:
    saver = _sqlite()
    compiled = _linear().compile(checkpointer=saver)
    saver_history_before = len(list(saver.list(RunConfig(thread_id="t"))))
    compiled.invoke({"log": []}, {"thread_id": "t"})
    history = list(compiled.get_state_history({"thread_id": "t"}))
    assert len(history) == len(list(saver.list(RunConfig(thread_id="t"))))
    assert len(history) >= saver_history_before
    ids = [item.config.configurable["checkpoint_id"] for item in history]
    assert ids == sorted(ids, reverse=True)
    first = history[0]
    by_id = compiled.get_state(
        {"thread_id": "t", "configurable": {"checkpoint_id": first.config.configurable["checkpoint_id"]}}
    )
    assert by_id is not None
    assert by_id.values == first.values
    assert by_id.next == first.next
    assert by_id.tasks == first.tasks
    assert by_id.interrupts == first.interrupts


def test_history_filter_before_limit_match_saver_list() -> None:
    saver = _sqlite()
    compiled = _linear().compile(checkpointer=saver)
    compiled.invoke({"log": []}, {"thread_id": "t"})
    all_history = list(compiled.get_state_history({"thread_id": "t"}))
    target_id = all_history[-1].config.configurable["checkpoint_id"]  # oldest
    before = RunConfig(thread_id="t", configurable={"checkpoint_id": target_id})

    from_saver = [
        item.snapshot.config.configurable["checkpoint_id"]
        for item in saver.list(RunConfig(thread_id="t"), before=before, limit=2)
    ]
    from_graph = [
        item.config.configurable["checkpoint_id"]
        for item in compiled.get_state_history({"thread_id": "t"}, before=before, limit=2)
    ]
    assert from_graph == from_saver
    assert list(compiled.get_state_history({"thread_id": "t"}, limit=0)) == []


def test_memory_saver_filter_is_top_level_exact_match() -> None:
    saver = MemorySaver()
    graph = StateGraph(_State)
    graph.add_node("a", _a)
    graph.add_edge(START, "a")
    graph.add_edge("a", END)
    compiled = graph.compile(checkpointer=saver)
    compiled.invoke({"log": []}, {"thread_id": "t"})
    # MemorySaver keeps B14F1 top-level exact match on metadata keys (here "next").
    matched = list(compiled.get_state_history({"thread_id": "t"}, filter={"next": ()}))
    assert matched != []
