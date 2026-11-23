# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B15F1 · 状态读取差分场景（上游 ``langgraph`` 1.2.11）。

上游缺席 ⇒ 整个文件 skip。上游会额外保存一个 ``__start__`` checkpoint
（``next == ('__start__',)`` / ``metadata['step'] == -1``）⇒ 比较「实际 super-step
快照」时排除它；``metadata`` / ``created_at`` / ``config`` 按 spec 的投影排除。

> 覆盖 spec 的 D-01 / D-03 / D-09 / D-21（state 读取部分）。SQLite 连接 / WAL 等
> source-aligned 场景在 `langgraph.checkpoint.sqlite` 缺席时 skip（本文件不覆盖）。
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

import pytest

pytest.importorskip("langgraph")

from langgraph.checkpoint.memory import InMemorySaver as UpstreamSaver  # noqa: E402
from langgraph.graph import END  # noqa: E402
from langgraph.graph import START  # noqa: E402
from langgraph.graph import StateGraph as UpstreamGraph  # noqa: E402

from freegraph.contracts import RunConfig  # noqa: E402
from freegraph.graph import END as FG_END  # noqa: E402
from freegraph.graph import START as FG_START  # noqa: E402
from freegraph.graph import StateGraph as FG_Graph  # noqa: E402
from freegraph.persistence import MemorySaver  # noqa: E402


class _State(TypedDict):
    log: Annotated[list, operator.add]


def _fg_linear() -> FG_Graph:
    builder = FG_Graph(_State)
    builder.add_node("a", lambda state: {"log": ["a"]})
    builder.add_node("b", lambda state: {"log": ["b"]})
    builder.add_edge(FG_START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", FG_END)
    return builder


def _up_linear() -> UpstreamGraph:
    builder = UpstreamGraph(_State)
    builder.add_node("a", lambda state: {"log": ["a"]})
    builder.add_node("b", lambda state: {"log": ["b"]})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def _is_start(item: Any) -> bool:
    return tuple(item.next) == ("__start__",)


def _fg_history(compiled: Any) -> list[Any]:
    return list(compiled.get_state_history({"thread_id": "t"}))


def _up_history(compiled: Any) -> list[Any]:
    return [
        item
        for item in compiled.get_state_history({"configurable": {"thread_id": "t"}})
        if not _is_start(item)
    ]


def _run_both():
    fg_saver = MemorySaver()
    fg_compiled = _fg_linear().compile(checkpointer=fg_saver)
    fg_compiled.invoke({"log": []}, {"thread_id": "t"})

    up_saver = UpstreamSaver()
    up_compiled = _up_linear().compile(checkpointer=up_saver)
    up_compiled.invoke({"log": []}, {"configurable": {"thread_id": "t"}})
    return fg_compiled, up_compiled


def test_d01_get_state_latest_values_next_tasks() -> None:
    fg_compiled, up_compiled = _run_both()
    fg_state = fg_compiled.get_state({"thread_id": "t"})
    up_state = up_compiled.get_state({"configurable": {"thread_id": "t"}})
    assert fg_state is not None
    assert fg_state.values == up_state.values
    assert fg_state.next == tuple(up_state.next)
    assert [task.name for task in fg_state.tasks] == [task.name for task in up_state.tasks]


def test_d03_history_values_next_tasks_excluding_start() -> None:
    fg_compiled, up_compiled = _run_both()
    fg_history = _fg_history(fg_compiled)
    up_history = _up_history(up_compiled)
    assert len(fg_history) == len(up_history)
    for fg_item, up_item in zip(fg_history, up_history):
        assert fg_item.values == up_item.values
        assert fg_item.next == tuple(up_item.next)
        assert [task.name for task in fg_item.tasks] == [
            task.name for task in up_item.tasks
        ]


def test_d09_no_checkpointer_raises_value_error() -> None:
    fg_compiled = _fg_linear().compile()
    with pytest.raises(ValueError):
        fg_compiled.get_state({"thread_id": "t"})
    up_compiled = _up_linear().compile()
    with pytest.raises(ValueError):
        up_compiled.get_state({"configurable": {"thread_id": "t"}})


def test_d21_next_tasks_projection_matches_names() -> None:
    fg_compiled, up_compiled = _run_both()
    fg_history = _fg_history(fg_compiled)
    up_history = _up_history(up_compiled)
    for fg_item, up_item in zip(fg_history, up_history):
        assert [task.name for task in fg_item.tasks] == [
            task.name for task in up_item.tasks
        ]
        # convergence snapshots yield no next tasks on either side
        if tuple(fg_item.next) == ():
            assert fg_item.tasks == ()
