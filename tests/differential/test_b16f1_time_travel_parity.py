# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B16F1 · 时间旅行 / update_state 上游差分（D-01…D-17）。

上游 ``langgraph`` 缺席 ⇒ 整文件 skip（不是 fail）。差分只比较行为面：
节点序列（用 ``log`` 记录）、最终状态、``next``、异常、历史数量与顺序；
``metadata`` / ``created_at`` / config 载体按 B15F1 投影排除。上游额外
``__start__`` 快照在比较时排除（P-20）。
"""

from __future__ import annotations

import operator
import sqlite3
from typing import Annotated, TypedDict

import pytest

from freegraph.contracts import Command as FGCommand
from freegraph.contracts import InvalidUpdateError
from freegraph.graph import END, START, StateGraph as FGStateGraph, interrupt as fg_interrupt
from freegraph.persistence import MemorySaver, SqliteSaver

lg_graph = pytest.importorskip("langgraph.graph")
lg_memory = pytest.importorskip("langgraph.checkpoint.memory")
lg_types = pytest.importorskip("langgraph.types")

LGStateGraph = lg_graph.StateGraph
LGSTART = lg_graph.START
LGEND = lg_graph.END
LGMemorySaver = lg_memory.InMemorySaver
LGCommand = lg_types.Command
lg_interrupt = lg_types.interrupt


class _State(TypedDict):
    x: int
    log: Annotated[list, operator.add]


def _a(state: dict) -> dict:
    return {"log": ["a"], "x": 1}


def _b(state: dict) -> dict:
    return {"log": ["b"]}


def _c(state: dict) -> dict:
    return {"log": ["c"]}


def _ask_fg(state: dict) -> dict:
    fg_interrupt({"ask": "approve"})
    return {"log": ["answered"]}


def _ask_lg(state: dict) -> dict:
    lg_interrupt({"ask": "approve"})
    return {"log": ["answered"]}


FG_CFG = {"thread_id": "t"}
LG_CFG = {"configurable": {"thread_id": "t"}}


def _fg_linear(**compile_kwargs):
    graph = FGStateGraph(_State)
    graph.add_node("a", _a)
    graph.add_node("b", _b)
    graph.add_node("c", _c)
    graph.add_edge(START, "a")
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", END)
    return graph.compile(checkpointer=MemorySaver(), **compile_kwargs)


def _lg_linear(**compile_kwargs):
    graph = LGStateGraph(_State)
    graph.add_node("a", _a)
    graph.add_node("b", _b)
    graph.add_node("c", _c)
    graph.add_edge(LGSTART, "a")
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", LGEND)
    return graph.compile(checkpointer=LGMemorySaver(), **compile_kwargs)


def _fg_interrupt_graph():
    graph = FGStateGraph(_State)
    graph.add_node("a", _a)
    graph.add_node("ask", _ask_fg)
    graph.add_edge(START, "a")
    graph.add_edge("a", "ask")
    graph.add_edge("ask", END)
    return graph.compile(checkpointer=MemorySaver())


def _lg_interrupt_graph():
    graph = LGStateGraph(_State)
    graph.add_node("a", _a)
    graph.add_node("ask", _ask_lg)
    graph.add_edge(LGSTART, "a")
    graph.add_edge("a", "ask")
    graph.add_edge("ask", LGEND)
    return graph.compile(checkpointer=LGMemorySaver())


def _fg_hist(compiled) -> list:
    return list(compiled.get_state_history(FG_CFG))


def _lg_hist(compiled) -> list:
    return [
        s
        for s in compiled.get_state_history(LG_CFG)
        if s.next != ("__start__",)
    ]


def _fg_base(compiled, node: str):
    return next(s for s in _fg_hist(compiled) if s.next == (node,))


def _lg_base(compiled, node: str):
    return next(s for s in _lg_hist(compiled) if s.next == (node,))


def _state_projection(snapshot) -> tuple[dict, tuple]:
    return dict(snapshot.values), tuple(snapshot.next)


# ── D-01 … D-17 ───────────────────────────────────────────────────────────


def test_d01_replay_from_middle_checkpoint() -> None:
    fg = _fg_linear()
    fg.invoke({"log": []}, FG_CFG)
    lg = _lg_linear()
    lg.invoke({"log": []}, LG_CFG)
    fg_base = _fg_base(fg, "b")
    lg_base_snap = _lg_base(lg, "b")
    fg_original = _fg_hist(fg)
    lg_original = _lg_hist(lg)

    fg_result = fg.invoke(None, fg_base.config)
    lg_result = lg.invoke(None, lg_base_snap.config)
    assert fg_result["log"] == lg_result["log"] == ["a", "b", "c"]
    assert [ _state_projection(s) for s in fg_original ] == [
        _state_projection(s) for s in lg_original
    ]


def test_d02_normal_terminal_replay() -> None:
    fg = _fg_linear()
    fg.invoke({"log": []}, FG_CFG)
    lg = _lg_linear()
    lg.invoke({"log": []}, LG_CFG)
    fg_final = _fg_hist(fg)[0]
    lg_final = _lg_hist(lg)[0]
    fg_before = len(_fg_hist(fg))

    fg_result = fg.invoke(None, fg_final.config)
    lg_result = lg.invoke(None, lg_final.config)
    assert fg_result["log"] == lg_result["log"] == ["a", "b", "c"]
    # STRICTER（X-06）：freegraph 零新快照；不比较快照数。
    assert len(_fg_hist(fg)) == fg_before


def test_d03_replay_interrupt_point() -> None:
    fg = _fg_interrupt_graph()
    fg.invoke({"log": []}, FG_CFG)
    lg = _lg_interrupt_graph()
    lg.invoke({"log": []}, LG_CFG)
    fg_pause = _fg_hist(fg)[0]
    lg_pause = _lg_hist(lg)[0]

    fg_replay = fg.invoke(None, fg_pause.config)
    lg_replay = lg.invoke(None, lg_pause.config)
    assert "__interrupt__" in fg_replay
    assert "__interrupt__" in lg_replay

    fg_result = fg.invoke(FGCommand(resume="ok"), FG_CFG)
    lg_result = lg.invoke(LGCommand(resume="ok"), LG_CFG)
    assert fg_result["log"] == lg_result["log"] == ["a", "answered"]


def test_d04_update_state_override() -> None:
    fg = _fg_linear()
    fg.invoke({"log": []}, FG_CFG)
    lg = _lg_linear()
    lg.invoke({"log": []}, LG_CFG)
    fg_fork = fg.update_state(_fg_base(fg, "b").config, {"x": 99})
    lg_fork = lg.update_state(_lg_base(lg, "b").config, {"x": 99})
    assert fg.get_state(fg_fork).values["x"] == lg.get_state(lg_fork).values["x"] == 99
    assert fg.get_state(fg_fork).parent_config is not None
    assert lg.get_state(lg_fork).parent_config is not None


def test_d05_update_state_reducer() -> None:
    fg = _fg_linear()
    fg.invoke({"log": []}, FG_CFG)
    lg = _lg_linear()
    lg.invoke({"log": []}, LG_CFG)
    fg_fork = fg.update_state(_fg_base(fg, "b").config, {"log": ["fork"]})
    lg_fork = lg.update_state(_lg_base(lg, "b").config, {"log": ["fork"]})
    assert fg.get_state(fg_fork).values["log"] == ["a", "fork"]
    assert lg.get_state(lg_fork).values["log"] == ["a", "fork"]


def test_d06_update_state_as_node_successors() -> None:
    fg = _fg_linear()
    fg.invoke({"log": []}, FG_CFG)
    lg = _lg_linear()
    lg.invoke({"log": []}, LG_CFG)
    fg_fork = fg.update_state(_fg_base(fg, "b").config, {"x": 7}, as_node="a")
    lg_fork = lg.update_state(_lg_base(lg, "b").config, {"x": 7}, as_node="a")
    assert fg.get_state(fg_fork).next == lg.get_state(lg_fork).next == ("b",)
    assert fg.invoke(None, fg_fork)["log"] == lg.invoke(None, lg_fork)["log"]


def test_d07_as_node_ambiguous_and_missing() -> None:
    fg = _fg_linear()
    fg.invoke({"log": []}, FG_CFG)
    lg = _lg_linear()
    lg.invoke({"log": []}, LG_CFG)
    fg_terminal = _fg_hist(fg)[0]
    lg_terminal = _lg_hist(lg)[0]

    # ⚠️ 上游 1.2.11 的 edge channel 版本是全局递增的，终止快照仍可推断最后更新者；
    # freegraph 的 versions_seen 是「源节点执行版本」（每节点各自计数）⇒ 该场景
    # 取 STRICTER 显式失败（登记于 manual-verification 的遗留问题）。
    with pytest.raises(Exception) as fg_amb:
        fg.update_state(fg_terminal.config, {"x": 1})
    assert "Ambiguous" in str(fg_amb.value)

    with pytest.raises(Exception) as fg_missing:
        fg.update_state(fg_terminal.config, {"x": 1}, as_node="missing")
    with pytest.raises(Exception) as lg_missing:
        lg.update_state(lg_terminal.config, {"x": 1}, as_node="missing")
    assert "does not exist" in str(fg_missing.value)
    assert "does not exist" in str(lg_missing.value)


def test_d08_missing_saver_and_thread() -> None:
    fg = _fg_linear()
    fg.invoke({"log": []}, FG_CFG)

    free_graph = FGStateGraph(_State)
    free_graph.add_node("a", _a)
    free_graph.add_edge(START, "a")
    free_graph.add_edge("a", END)
    free_no_saver = free_graph.compile()

    lg_graph_no_saver = LGStateGraph(_State)
    lg_graph_no_saver.add_node("a", _a)
    lg_graph_no_saver.add_edge(LGSTART, "a")
    lg_graph_no_saver.add_edge("a", LGEND)
    lg_no_saver = lg_graph_no_saver.compile()

    with pytest.raises(ValueError):
        free_no_saver.update_state({"thread_id": "t"}, {})
    with pytest.raises(ValueError):
        lg_no_saver.update_state(LG_CFG, {})

    with pytest.raises(ValueError):
        fg.update_state({}, {})


def test_d09_missing_explicit_checkpoint_id_is_stricter() -> None:
    fg = _fg_linear()
    fg.invoke({"log": []}, FG_CFG)
    with pytest.raises(ValueError, match="checkpoint_id"):
        fg.update_state(
            {"thread_id": "t", "configurable": {"checkpoint_id": "9" * 32}},
            {"x": 1},
        )


def test_d10_update_state_return_carrier() -> None:
    from freegraph.contracts import RunConfig

    fg = _fg_linear()
    fg.invoke({"log": []}, FG_CFG)
    lg = _lg_linear()
    lg.invoke({"log": []}, LG_CFG)
    fg_fork = fg.update_state(_fg_base(fg, "b").config, {"x": 1})
    lg_fork = lg.update_state(_lg_base(lg, "b").config, {"x": 1})
    assert isinstance(fg_fork, RunConfig)
    assert fg_fork.configurable["checkpoint_id"]
    assert isinstance(lg_fork, dict)
    assert lg_fork["configurable"]["checkpoint_id"]


def test_d11_context_is_not_persisted() -> None:
    from freegraph.contracts import RunConfig

    fg = _fg_linear()
    fg.invoke({"log": []}, FG_CFG)
    base = _fg_base(fg, "b")
    fork = fg.update_state(
        RunConfig(
            thread_id="t",
            context={"secret": 1},
            configurable={"checkpoint_id": base.config.configurable["checkpoint_id"]},
        ),
        {"x": 2},
    )
    snapshot = fg.get_state(fork)
    assert snapshot.config.context is None
    assert "secret" not in repr(snapshot.metadata)


def test_d12_history_enumeration_and_order() -> None:
    fg = _fg_linear()
    fg.invoke({"log": []}, FG_CFG)
    lg = _lg_linear()
    lg.invoke({"log": []}, LG_CFG)
    fg_ids = [s.config.configurable["checkpoint_id"] for s in _fg_hist(fg)]
    lg_ids = [s.config["configurable"]["checkpoint_id"] for s in _lg_hist(lg)]
    assert fg_ids == sorted(fg_ids, reverse=True)
    assert lg_ids == sorted(lg_ids, reverse=True)
    assert [_state_projection(s) for s in _fg_hist(fg)] == [
        _state_projection(s) for s in _lg_hist(lg)
    ]


def test_d13_multiple_replays_same_branch_point() -> None:
    fg = _fg_linear()
    fg.invoke({"log": []}, FG_CFG)
    lg = _lg_linear()
    lg.invoke({"log": []}, LG_CFG)
    fg_base = _fg_base(fg, "b")
    lg_base_snap = _lg_base(lg, "b")
    fg_original = [_state_projection(s) for s in _fg_hist(fg)]
    lg_original = [_state_projection(s) for s in _lg_hist(lg)]

    for _ in range(2):
        assert fg.invoke(None, fg_base.config)["log"] == lg.invoke(None, lg_base_snap.config)["log"]
    fg_after = [_state_projection(s) for s in _fg_hist(fg)]
    lg_after = [_state_projection(s) for s in _lg_hist(lg)]
    assert fg_after[-len(fg_original):] == fg_original
    assert lg_after[-len(lg_original):] == lg_original


def test_d14_memory_and_sqlite_time_travel_are_consistent() -> None:
    def run(saver) -> list[tuple]:
        graph = FGStateGraph(_State)
        graph.add_node("a", _a)
        graph.add_node("b", _b)
        graph.add_node("c", _c)
        graph.add_edge(START, "a")
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        graph.add_edge("c", END)
        compiled = graph.compile(checkpointer=saver)
        compiled.invoke({"log": []}, FG_CFG)
        base = _fg_base(compiled, "b")
        fork = compiled.update_state(base.config, {"log": ["fork"]}, as_node="a")
        compiled.invoke(None, fork)
        return [
            (
                _state_projection(s),
                None
                if s.parent_config is None
                else s.parent_config.configurable["checkpoint_id"],
            )
            for s in _fg_hist(compiled)
        ]

    assert run(MemorySaver()) == run(
        SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))
    )


def test_d15_static_snapshot_replay() -> None:
    fg = _fg_linear(interrupt_before=["b"])
    fg.invoke({"log": []}, FG_CFG)
    lg = _lg_linear(interrupt_before=["b"])
    lg.invoke({"log": []}, LG_CFG)
    fg_pause = _fg_hist(fg)[0]
    lg_pause = _lg_hist(lg)[0]
    assert fg_pause.interrupts == ()
    assert lg_pause.interrupts == ()
    assert fg.invoke(None, fg_pause.config)["log"] == lg.invoke(
        None, lg_pause.config
    )["log"] == ["a", "b", "c"]


def test_d16_error_interrupt_trace_only_new_checkpoint() -> None:
    def ask(state: dict) -> dict:
        fg_interrupt({"q": "ok"})
        return {"log": ["ask"]}

    def boom(state: dict) -> dict:
        raise RuntimeError("boom")

    graph = FGStateGraph(_State)
    graph.add_node("ask", ask)
    graph.add_node("boom", boom)
    graph.add_edge(START, "ask")
    graph.add_edge(START, "boom")
    graph.add_edge("ask", END)
    graph.add_edge("boom", END)
    saver = MemorySaver()
    compiled = graph.compile(checkpointer=saver)
    with pytest.raises(RuntimeError):
        compiled.invoke({"log": []}, FG_CFG)
    base = _fg_hist(compiled)[0]
    original_pending = saver.get_tuple(base.config).pending_writes
    with pytest.raises(RuntimeError):
        compiled.invoke(None, base.config)
    assert saver.get_tuple(base.config).pending_writes == original_pending
    assert len(_fg_hist(compiled)) >= 2


def test_d17_static_breakpoint_replay_and_fork() -> None:
    fg = _fg_linear(interrupt_before=["b"])
    fg.invoke({"log": []}, FG_CFG)
    entry = next(s for s in _fg_hist(fg) if s.next == ("a",))
    # 从断点之前 replay 产生新写入 ⇒ 静态断点再次触发
    fg.invoke(None, entry.config)
    assert _fg_hist(fg)[0].next == ("b",)

    paused = _fg_hist(fg)[0]
    fork = fg.update_state(paused.config, {"x": 9}, as_node="a")
    fg.invoke(None, fork)
    # 新分支清空 ack ⇒ 后继命中 interrupt_before 再次暂停
    assert _fg_hist(fg)[0].next == ("b",)
    assert _fg_hist(fg)[0].interrupts == ()
