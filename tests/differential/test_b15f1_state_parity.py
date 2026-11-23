# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B15F1 · 状态读取差分场景（D-01…D-21）。

* **上游对照**（`langgraph 1.2.11` 的 `InMemorySaver`）不可导入 ⇒ 仅跳过**对照**，
  freegraph-only 部分**始终运行**（spec D-14 / D-15）。
* **上游 SQLite**（`langgraph.checkpoint.sqlite`）未安装 ⇒ 相关对照标
  `SKIP (source-aligned)`（不 fail）。
* 比较投影：排除 `metadata` / `created_at` / `config`（见 spec 差分场景组注记）；
  fan-out 轮不比较 `next` 字面值。
* 上游额外的 ``__start__`` 快照（`next == ('__start__',)`）在比较「实际 super-step
  快照」时排除（B14F1 既有口径 · 不占 X 编号）。
"""

from __future__ import annotations

import importlib
import operator
import sqlite3
import threading
from typing import Annotated, Any, TypedDict

import pytest

from freegraph.contracts import RunConfig, StateSnapshot
from freegraph.graph import END, START, StateGraph
from freegraph.graph import interrupt as fg_interrupt
from freegraph.persistence import MemorySaver, SqliteSaver


class _State(TypedDict):
    log: Annotated[list, operator.add]


# ── builders ────────────────────────────────────────────────────────────


def _fg_linear() -> Any:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"log": ["a"]})
    builder.add_node("b", lambda state: {"log": ["b"]})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def _fg_compiled(saver: Any, *, interrupt_before: list[str] | None = None) -> Any:
    return _fg_linear().compile(checkpointer=saver, interrupt_before=interrupt_before)


def _fg_interrupting(saver: Any) -> Any:
    def ask(state: dict) -> dict:
        fg_interrupt({"ask": "approve"})
        return {"log": ["asked"]}

    builder = StateGraph(_State)
    builder.add_node("ask", ask)
    builder.add_edge(START, "ask")
    builder.add_edge("ask", END)
    return builder.compile(checkpointer=saver)


def _up():
    """惰性导入上游（缺席 ⇒ 仅该对照 skip）。"""
    pytest.importorskip("langgraph")
    graph_mod = importlib.import_module("langgraph.graph")
    memory_mod = importlib.import_module("langgraph.checkpoint.memory")
    interrupt_mod = importlib.import_module("langgraph.types")
    return graph_mod, memory_mod, interrupt_mod


def _up_linear(graph_mod: Any) -> Any:
    builder = graph_mod.StateGraph(_State)
    builder.add_node("a", lambda state: {"log": ["a"]})
    builder.add_node("b", lambda state: {"log": ["b"]})
    builder.add_edge(graph_mod.START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", graph_mod.END)
    return builder


def _up_cfg(thread: str = "t", checkpoint_id: str | None = None) -> dict[str, Any]:
    configurable: dict[str, Any] = {"thread_id": thread}
    if checkpoint_id is not None:
        configurable["checkpoint_id"] = checkpoint_id
    return {"configurable": configurable}


def _up_history(compiled: Any) -> list[Any]:
    return [
        item
        for item in compiled.get_state_history(_up_cfg())
        if tuple(item.next) != ("__start__",)
    ]


def _fg_sqlite() -> SqliteSaver:
    return SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))


def _meta(next_nodes: tuple[str, ...] = ()) -> dict[str, Any]:
    return {"next": next_nodes, "interrupts": (), "tasks": (), "scheduler": {"fanout": {}}}


# ── D-01 / D-02 / D-03 / D-21（对照 InMemorySaver）──────────────────────


def _run_both_linear():
    fg_compiled = _fg_compiled(MemorySaver())
    fg_compiled.invoke({"log": []}, {"thread_id": "t"})

    graph_mod, memory_mod, _ = _up()
    up_compiled = _up_linear(graph_mod).compile(checkpointer=memory_mod.InMemorySaver())
    up_compiled.invoke({"log": []}, _up_cfg())
    return fg_compiled, up_compiled


def test_d01_get_state_latest_values_next_tasks() -> None:
    fg_compiled, up_compiled = _run_both_linear()
    fg_state = fg_compiled.get_state({"thread_id": "t"})
    up_state = up_compiled.get_state(_up_cfg())
    assert fg_state is not None
    assert fg_state.values == up_state.values
    assert fg_state.next == tuple(up_state.next)
    assert [task.name for task in fg_state.tasks] == [task.name for task in up_state.tasks]


def test_d02_get_state_by_checkpoint_id_and_unknown_diff() -> None:
    fg_compiled, up_compiled = _run_both_linear()
    up_state = up_compiled.get_state(_up_cfg())
    up_id = up_state.config["configurable"]["checkpoint_id"]
    up_by_id = up_compiled.get_state(_up_cfg(checkpoint_id=up_id))
    fg_state = fg_compiled.get_state({"thread_id": "t"})
    assert fg_state is not None
    fg_by_id = fg_compiled.get_state(
        {"thread_id": "t", "configurable": {"checkpoint_id": fg_state.config.configurable["checkpoint_id"]}}
    )
    assert fg_by_id is not None
    assert fg_by_id.values == up_by_id.values
    # X-01: unknown checkpoint_id -> freegraph None, upstream empty StateSnapshot
    assert fg_compiled.get_state({"thread_id": "t", "configurable": {"checkpoint_id": "nope"}}) is None
    up_unknown = up_compiled.get_state(_up_cfg(checkpoint_id="nope"))
    assert up_unknown is not None and up_unknown.values == {}


def test_d03_history_values_next_tasks_excluding_start() -> None:
    fg_compiled, up_compiled = _run_both_linear()
    fg_history = list(fg_compiled.get_state_history({"thread_id": "t"}))
    up_history = _up_history(up_compiled)
    assert len(fg_history) == len(up_history)
    for fg_item, up_item in zip(fg_history, up_history):
        assert fg_item.values == up_item.values
        assert fg_item.next == tuple(up_item.next)
        assert [task.name for task in fg_item.tasks] == [task.name for task in up_item.tasks]


def test_d04_filter_before_limit_boundaries() -> None:
    fg_compiled, up_compiled = _run_both_linear()
    # limit: same count on both
    fg_limited = list(fg_compiled.get_state_history({"thread_id": "t"}, limit=2))
    up_limited = list(up_compiled.get_state_history(_up_cfg(), limit=2))
    assert len(fg_limited) == len(up_limited) == 2
    # limit <= 0 -> empty on both
    assert list(fg_compiled.get_state_history({"thread_id": "t"}, limit=0)) == []
    assert list(up_compiled.get_state_history(_up_cfg(), limit=0)) == []
    # before: both accept it and return a subset (B14F1 冻结的 before 口径与上游可有差异)
    fg_full = list(fg_compiled.get_state_history({"thread_id": "t"}))
    fg_oldest = fg_full[-1]
    fg_before = RunConfig(
        thread_id="t",
        configurable={"checkpoint_id": fg_oldest.config.configurable["checkpoint_id"]},
    )
    fg_before_count = len(list(fg_compiled.get_state_history({"thread_id": "t"}, before=fg_before)))
    up_full = _up_history(up_compiled)
    up_oldest = up_full[-1]
    up_before = _up_cfg(checkpoint_id=up_oldest.config["configurable"]["checkpoint_id"])
    up_before_count = len(list(up_compiled.get_state_history(up_before)))
    assert 0 <= fg_before_count < len(fg_full)
    assert 0 <= up_before_count <= len(up_full)
    # 注：filter 非法 key ⇒ ValueError 仅对 **SqliteSaver** 成立（D-20）；
    # MemorySaver 保持 B14F1 顶层精确匹配（不校验 key）。


def test_d21_next_tasks_projection_matches_names() -> None:
    fg_compiled, up_compiled = _run_both_linear()
    fg_history = list(fg_compiled.get_state_history({"thread_id": "t"}))
    up_history = _up_history(up_compiled)
    for fg_item, up_item in zip(fg_history, up_history):
        assert [task.name for task in fg_item.tasks] == [task.name for task in up_item.tasks]
        if tuple(fg_item.next) == ():
            assert fg_item.tasks == ()


# ── D-05 / D-06 中断 ────────────────────────────────────────────────────


def test_d05_static_suspension_representation() -> None:
    fg_saver = MemorySaver()
    fg_app = _fg_compiled(fg_saver, interrupt_before=["b"])
    fg_app.invoke({"log": []}, {"thread_id": "t"})
    fg_state = fg_app.get_state({"thread_id": "t"})
    assert fg_state is not None
    assert fg_state.next == ("b",)
    assert fg_state.interrupts == ()
    assert [task.id for task in fg_state.tasks] == ["b"]

    graph_mod, memory_mod, _ = _up()
    up_app = _up_linear(graph_mod).compile(
        checkpointer=memory_mod.InMemorySaver(), interrupt_before=["b"]
    )
    up_app.invoke({"log": []}, _up_cfg())
    up_state = up_app.get_state(_up_cfg())
    assert tuple(up_state.next) == ("b",)
    assert tuple(up_state.interrupts) == ()
    assert [task.name for task in up_state.tasks] == [task.name for task in fg_state.tasks]


def test_d06_dynamic_interrupt_interrupts_and_tasks() -> None:
    fg_app = _fg_interrupting(MemorySaver())
    fg_result = fg_app.invoke({"log": []}, {"thread_id": "t"})
    fg_expected = tuple(fg_result["__interrupt__"])
    fg_state = fg_app.get_state({"thread_id": "t"})
    assert fg_state is not None
    assert fg_state.interrupts == fg_expected
    assert [task.name for task in fg_state.tasks] == ["ask"]
    assert fg_state.tasks[0].interrupts == fg_expected

    graph_mod, memory_mod, interrupt_mod = _up()
    def ask(state: dict) -> dict:
        interrupt_mod.interrupt({"ask": "approve"})
        return {"log": ["asked"]}

    builder = graph_mod.StateGraph(_State)
    builder.add_node("ask", ask)
    builder.add_edge(graph_mod.START, "ask")
    builder.add_edge("ask", graph_mod.END)
    up_app = builder.compile(checkpointer=memory_mod.InMemorySaver())
    up_result = up_app.invoke({"log": []}, _up_cfg())
    up_state = up_app.get_state(_up_cfg())
    assert [item.value for item in fg_state.interrupts] == [
        item.value for item in up_state.interrupts
    ]
    assert [task.name for task in fg_state.tasks] == [task.name for task in up_state.tasks]


def test_d07_true_error_and_interrupt_coexistence() -> None:
    """freegraph-only：真异常优先，pending ``__interrupt__`` 仍可读出（上游对照跳过）。"""
    def ask(state: dict) -> dict:
        fg_interrupt({"ask": "approve"})
        return {"log": ["asked"]}

    def boom(state: dict) -> dict:
        raise ValueError("boom")

    builder = StateGraph(_State)
    builder.add_node("ask", ask)
    builder.add_node("boom", boom)
    builder.add_edge(START, "ask")
    builder.add_edge(START, "boom")
    saver = _fg_sqlite()
    app = builder.compile(checkpointer=saver)
    with pytest.raises(ValueError, match="boom"):
        app.invoke({"log": []}, {"thread_id": "t"})
    snapshot = app.get_state({"thread_id": "t"})
    assert snapshot is not None
    assert any(item.value == {"ask": "approve"} for item in snapshot.interrupts)
    assert {task.id for task in snapshot.tasks} == {"ask", "boom"}


# ── D-08 / D-09 / D-10 ──────────────────────────────────────────────────


def test_d08_context_not_persisted() -> None:
    saver = _fg_sqlite()
    app = _fg_compiled(saver)
    app.invoke({"log": []}, RunConfig(thread_id="t", context={"user": "a"}))
    stored = saver.get_tuple(RunConfig(thread_id="t"))
    assert stored is not None
    assert stored.snapshot.config.context is None
    assert "context" not in stored.snapshot.metadata
    assert "context" not in stored.scheduler


def test_d09_no_checkpointer_raises_value_error() -> None:
    fg_compiled = _fg_linear().compile()
    with pytest.raises(ValueError):
        fg_compiled.get_state({"thread_id": "t"})
    graph_mod, _, _ = _up()
    up_compiled = _up_linear(graph_mod).compile()
    with pytest.raises(ValueError):
        up_compiled.get_state(_up_cfg())


def test_d10_missing_thread_id_is_a_clearer_failure() -> None:
    """STRICTER(X-08)：freegraph 必抛 ``ValueError`` 并点名 thread_id。"""
    fg_compiled = _fg_compiled(MemorySaver())
    with pytest.raises(ValueError, match="thread_id"):
        fg_compiled.get_state({})
    graph_mod, memory_mod, _ = _up()
    up_compiled = _up_linear(graph_mod).compile(checkpointer=memory_mod.InMemorySaver())
    with pytest.raises((ValueError, KeyError)):
        up_compiled.get_state({"configurable": {}})


# ── D-11 checkpoints 事件（DIFF · X-04）─────────────────────────────────


def test_d11_checkpoints_event_shape_diff() -> None:
    fg_app = _fg_compiled(MemorySaver())
    fg_events = list(fg_app.stream({"log": []}, {"thread_id": "t"}, stream_mode="checkpoints"))
    assert fg_events
    assert all(set(event) == {"stream_mode", "payload", "run_id", "thread_id"} for event in fg_events)
    assert all(isinstance(event["payload"], StateSnapshot) for event in fg_events)

    graph_mod, memory_mod, _ = _up()
    up_app = _up_linear(graph_mod).compile(checkpointer=memory_mod.InMemorySaver())
    up_events = list(up_app.stream({"log": []}, _up_cfg(), stream_mode="checkpoints"))
    assert up_events
    # upstream 事件是「字段平铺」的 dict，**没有** freegraph 的四键信封 / payload
    for event in up_events:
        assert "payload" not in event
        assert set(event) != {"stream_mode", "payload", "run_id", "thread_id"}


# ── D-12 delete_thread ──────────────────────────────────────────────────


def test_d12_delete_thread() -> None:
    fg_saver = MemorySaver()
    app = _fg_compiled(fg_saver)
    app.invoke({"log": []}, {"thread_id": "t1"})
    app.invoke({"log": []}, {"thread_id": "t2"})
    fg_saver.delete_thread("t1")
    assert fg_saver.get_tuple(RunConfig(thread_id="t1")) is None
    assert fg_saver.get_tuple(RunConfig(thread_id="t2")) is not None

    graph_mod, memory_mod, _ = _up()
    up_saver = memory_mod.InMemorySaver()
    up_app = _up_linear(graph_mod).compile(checkpointer=up_saver)
    up_app.invoke({"log": []}, _up_cfg("t1"))
    up_app.invoke({"log": []}, _up_cfg("t2"))
    up_saver.delete_thread("t1")
    assert up_saver.get_tuple(_up_cfg("t1")) is None
    assert up_saver.get_tuple(_up_cfg("t2")) is not None


# ── D-13 / D-16 双后端 ──────────────────────────────────────────────────


def _exercise(saver: Any) -> Any:
    config = RunConfig(thread_id="t")
    written = saver.put(
        config,
        values={"a": [1, 2], "n": 3},
        metadata={"next": ("b",), "interrupts": (), "tasks": (), "scheduler": {"fanout": {}}},
    )
    saver.put_writes(
        written,
        writes=[("a", [9]), ("__error__", "e")],
        task_id="b",
        task_path="b",
    )
    return saver.get_tuple(written)


def test_d13_sqlite_and_memory_savers_agree() -> None:
    memory = _exercise(MemorySaver())
    sqlite = _exercise(_fg_sqlite())
    assert memory is not None and sqlite is not None
    for field in ("values", "next", "config", "metadata", "parent_config", "tasks", "interrupts"):
        assert getattr(memory.snapshot, field) == getattr(sqlite.snapshot, field), field
    assert memory.pending_writes == sqlite.pending_writes
    assert memory.scheduler == sqlite.scheduler
    assert bool(memory.snapshot.created_at) and bool(sqlite.snapshot.created_at)


def test_d16_non_serializable_payload_diff() -> None:
    payload = object()
    sqlite = _fg_sqlite()
    with pytest.raises(TypeError):
        sqlite.put(RunConfig(thread_id="t"), values={"bad": payload}, metadata=_meta())
    # MemorySaver accepts arbitrary objects (deepcopy) -> DIFF (X-05)
    memory = MemorySaver()
    written = memory.put(RunConfig(thread_id="t"), values={"bad": payload}, metadata=_meta())
    stored = memory.get_tuple(written)
    assert stored is not None and type(stored.snapshot.values["bad"]) is object


# ── D-14 / D-15 freegraph-only（始终运行）───────────────────────────────


def test_d14_cross_instance_persistence(tmp_path) -> None:
    path = str(tmp_path / "d14.db")
    with SqliteSaver.from_conn_string(path) as saver:
        written = saver.put(RunConfig(thread_id="t"), values={"n": 7}, metadata=_meta(("b",)))
    with SqliteSaver.from_conn_string(path) as saver:
        first = saver.get_tuple(written)
        latest = saver.get_tuple(RunConfig(thread_id="t"))
        assert first is not None and latest is not None
        for field in ("values", "next", "config", "metadata", "tasks", "interrupts"):
            assert getattr(first.snapshot, field) == getattr(latest.snapshot, field), field


def test_d15_same_instance_concurrency() -> None:
    saver = _fg_sqlite()
    errors: list[BaseException] = []

    def worker(worker_id: int) -> None:
        try:
            for index in range(3):
                saver.put(
                    RunConfig(thread_id="t"),
                    values={"w": worker_id, "i": index},
                    metadata=_meta(),
                )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    ids = [item.snapshot.config.configurable["checkpoint_id"] for item in saver.list(RunConfig(thread_id="t"))]
    assert not errors
    assert len(ids) == 24 and len(set(ids)) == 24
    assert not any("database is locked" in str(exc) for exc in errors)


# ── D-17 / D-18 pending 合并 ────────────────────────────────────────────


def test_d17_pending_merge_for_task_in_next() -> None:
    # freegraph: static suspend -> next=('b',)
    fg_app = _fg_compiled(_fg_sqlite(), interrupt_before=["b"])
    fg_app.invoke({"log": []}, {"thread_id": "t"})
    fg_state = fg_app.get_state({"thread_id": "t"})
    assert fg_state is not None and fg_state.next == ("b",)
    fg_saver = fg_app.checkpointer
    fg_saver.put_writes(
        RunConfig(thread_id="t", configurable={"checkpoint_id": fg_state.config.configurable["checkpoint_id"]}),
        writes=[("log", ["pending"])],
        task_id="b",
    )
    fg_merged = fg_app.get_state({"thread_id": "t"})
    assert fg_merged is not None and fg_merged.values["log"] == ["a", "pending"]

    # upstream: static suspend -> put_writes with the upstream task id
    graph_mod, memory_mod, _ = _up()
    up_saver = memory_mod.InMemorySaver()
    up_app = _up_linear(graph_mod).compile(checkpointer=up_saver, interrupt_before=["b"])
    up_app.invoke({"log": []}, _up_cfg())
    up_state = up_app.get_state(_up_cfg())
    up_task_id = up_state.tasks[0].id
    up_saver.put_writes(up_state.config, [("log", ["pending"])], task_id=up_task_id)
    up_merged = up_app.get_state(_up_cfg())
    assert up_merged.values == fg_merged.values


def test_d18_pending_not_merged_when_checkpoint_id_given() -> None:
    fg_app = _fg_compiled(_fg_sqlite(), interrupt_before=["b"])
    fg_app.invoke({"log": []}, {"thread_id": "t"})
    fg_state = fg_app.get_state({"thread_id": "t"})
    assert fg_state is not None
    fg_id = fg_state.config.configurable["checkpoint_id"]
    fg_app.checkpointer.put_writes(
        RunConfig(thread_id="t", configurable={"checkpoint_id": fg_id}),
        writes=[("log", ["pending"])],
        task_id="b",
    )
    fg_by_id = fg_app.get_state({"thread_id": "t", "configurable": {"checkpoint_id": fg_id}})
    assert fg_by_id is not None and fg_by_id.values["log"] == ["a"]

    graph_mod, memory_mod, _ = _up()
    up_saver = memory_mod.InMemorySaver()
    up_app = _up_linear(graph_mod).compile(checkpointer=up_saver, interrupt_before=["b"])
    up_app.invoke({"log": []}, _up_cfg())
    up_state = up_app.get_state(_up_cfg())
    up_saver.put_writes(up_state.config, [("log", ["pending"])], task_id=up_state.tasks[0].id)
    up_by_id = up_app.get_state(up_state.config)
    assert up_by_id.values == fg_by_id.values


# ── D-19 / D-20 SQLite（上游 SQLite 缺席 ⇒ SKIP）───────────────────────


def test_d19_from_conn_string_memory_and_structures(tmp_path) -> None:
    with SqliteSaver.from_conn_string(":memory:") as saver:
        saver.put(RunConfig(thread_id="t"), values={"n": 1}, metadata=_meta())
        assert saver.get_tuple(RunConfig(thread_id="t")) is not None
    path = str(tmp_path / "d19.db")
    with SqliteSaver.from_conn_string(path) as saver:
        saver.put(RunConfig(thread_id="t"), values={"n": 1}, metadata=_meta())
        mode = saver.conn.execute("PRAGMA journal_mode").fetchone()[0]
        tables = {
            row[0]
            for row in saver.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert mode.lower() == "wal"
    assert {"checkpoints", "writes"}.issubset(tables)


def test_d19_upstream_sqlite_source_aligned() -> None:
    pytest.importorskip("langgraph.checkpoint.sqlite")


def test_d20_filter_invalid_key_value_error() -> None:
    saver = _fg_sqlite()
    saver.put(RunConfig(thread_id="t"), values={}, metadata=_meta())
    with pytest.raises(ValueError):
        list(saver.list(RunConfig(thread_id="t"), filter={"bad key;": 1}))
    # upstream SQLite is not installed -> source-aligned skip
    pytest.importorskip("langgraph.checkpoint.sqlite")
