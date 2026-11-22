# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B14F1 · checkpoint 差分场景（上游 ``langgraph`` 1.2.11）。

上游缺席 ⇒ 整个文件 skip。上游的 ``InMemorySaver`` 会额外保存一个
``__start__`` checkpoint（``metadata["step"] == -1``）⇒ 本文件在比较
「执行快照」时把它排除，使两边的**实际 super-step 快照**可比。
"""

from __future__ import annotations

from typing import Any, TypedDict

import pytest

pytest.importorskip("langgraph")

from langgraph.checkpoint.base import empty_checkpoint  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver as UpstreamSaver  # noqa: E402
from langgraph.graph import END, START, StateGraph as UpstreamGraph  # noqa: E402
from langgraph.types import Command as UpstreamCommand  # noqa: E402
from langgraph.types import Send as UpstreamSend  # noqa: E402
from langgraph.types import interrupt as upstream_interrupt  # noqa: E402

from freegraph.contracts import Command, RunConfig  # noqa: E402
from freegraph.graph import END as FG_END  # noqa: E402
from freegraph.graph import START as FG_START  # noqa: E402
from freegraph.graph import StateGraph as FG_Graph  # noqa: E402
from freegraph.graph import interrupt as fg_interrupt  # noqa: E402
from freegraph.graph import Send as FGSend  # noqa: E402
from freegraph.persistence import MemorySaver  # noqa: E402


class _State(TypedDict, total=False):
    x: Any


def _fg_linear() -> FG_Graph:
    builder = FG_Graph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(FG_START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", FG_END)
    return builder


def _up_linear() -> UpstreamGraph:
    builder = UpstreamGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder


def _up_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


def _up_snapshots(saver: UpstreamSaver, config: dict[str, Any]):
    return [
        item
        for item in saver.list(config)
        if (item.metadata or {}).get("step", -1) >= 0
    ]


def _up_values(item: Any) -> dict[str, Any]:
    values = item.checkpoint.get("channel_values", {})
    return {key: value for key, value in values.items() if key == "x"}


def test_d01_single_node_snapshot_count() -> None:
    fg_saver = MemorySaver()
    fg_cfg = RunConfig(thread_id="d01")
    builder = FG_Graph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_edge(FG_START, "a")
    builder.add_edge("a", FG_END)
    builder.compile(checkpointer=fg_saver).invoke({"x": 0}, fg_cfg)
    assert len(list(fg_saver.list(fg_cfg))) == 2

    up_saver = UpstreamSaver()
    up_cfg = _up_config("d01")
    up_builder = UpstreamGraph(_State)
    up_builder.add_node("a", lambda state: {"x": 1})
    up_builder.add_edge(START, "a")
    up_builder.add_edge("a", END)
    up_builder.compile(checkpointer=up_saver).invoke({"x": 0}, up_cfg)
    assert len(_up_snapshots(up_saver, up_cfg)) == 2


def test_d02_two_node_snapshot_counts_and_values() -> None:
    fg_saver = MemorySaver()
    fg_cfg = RunConfig(thread_id="d02")
    _fg_linear().compile(checkpointer=fg_saver).invoke({"x": 0}, fg_cfg)
    fg_items = list(fg_saver.list(fg_cfg))
    assert len(fg_items) == 3
    assert [item.snapshot.values for item in fg_items] == [
        {"x": 2},
        {"x": 1},
        {"x": 0},
    ]

    up_saver = UpstreamSaver()
    up_cfg = _up_config("d02")
    _up_linear().compile(checkpointer=up_saver).invoke({"x": 0}, up_cfg)
    up_items = _up_snapshots(up_saver, up_cfg)
    assert len(up_items) == 3
    assert [_up_values(item) for item in up_items] == [
        {"x": 2},
        {"x": 1},
        {"x": 0},
    ]


def test_d03_get_tuple_latest_specified_and_unknown() -> None:
    fg_saver = MemorySaver()
    fg_cfg = RunConfig(thread_id="d03")
    _fg_linear().compile(checkpointer=fg_saver).invoke({"x": 0}, fg_cfg)
    latest = fg_saver.get_tuple(fg_cfg)
    assert latest is not None and latest.snapshot.values == {"x": 2}
    first_id = list(fg_saver.list(fg_cfg))[-1].snapshot.config.configurable["checkpoint_id"]
    specified = fg_saver.get_tuple(
        RunConfig(thread_id="d03", configurable={"checkpoint_id": first_id})
    )
    assert specified is not None and specified.snapshot.values == {"x": 0}
    assert fg_saver.get_tuple(
        RunConfig(thread_id="d03", configurable={"checkpoint_id": "999"})
    ) is None

    up_saver = UpstreamSaver()
    up_cfg = _up_config("d03")
    _up_linear().compile(checkpointer=up_saver).invoke({"x": 0}, up_cfg)
    up_latest = up_saver.get_tuple(up_cfg)
    assert up_latest is not None and _up_values(up_latest) == {"x": 2}
    up_first_id = _up_snapshots(up_saver, up_cfg)[-1].config["configurable"]["checkpoint_id"]
    up_specified = up_saver.get_tuple(
        {"configurable": {"thread_id": "d03", "checkpoint_id": up_first_id}}
    )
    assert up_specified is not None and _up_values(up_specified) == {"x": 0}
    assert up_saver.get_tuple(
        {"configurable": {"thread_id": "d03", "checkpoint_id": "999"}}
    ) is None


def test_d05_thread_isolation() -> None:
    fg_saver = MemorySaver()
    _fg_linear().compile(checkpointer=fg_saver).invoke(
        {"x": 0}, RunConfig(thread_id="d05-a")
    )
    _fg_linear().compile(checkpointer=fg_saver).invoke(
        {"x": 0}, RunConfig(thread_id="d05-b")
    )
    assert len(list(fg_saver.list(RunConfig(thread_id="d05-a")))) == 3
    fg_saver.delete_thread("d05-a")
    assert list(fg_saver.list(RunConfig(thread_id="d05-a"))) == []
    assert len(list(fg_saver.list(RunConfig(thread_id="d05-b")))) == 3

    up_saver = UpstreamSaver()
    _up_linear().compile(checkpointer=up_saver).invoke({"x": 0}, _up_config("d05-a"))
    _up_linear().compile(checkpointer=up_saver).invoke({"x": 0}, _up_config("d05-b"))
    assert len(_up_snapshots(up_saver, _up_config("d05-a"))) == 3
    up_saver.delete_thread("d05-a")
    assert list(up_saver.list(_up_config("d05-a"))) == []
    assert len(_up_snapshots(up_saver, _up_config("d05-b"))) == 3


def test_d07_interrupt_resume_parity() -> None:
    fg_seen: list[Any] = []

    def fg_ask(state):
        fg_seen.append(fg_interrupt("approve?"))
        return {"x": "yes"}

    fg_builder = FG_Graph(_State)
    fg_builder.add_node("ask", fg_ask)
    fg_builder.add_edge(FG_START, "ask")
    fg_builder.add_edge("ask", FG_END)
    fg_saver = MemorySaver()
    fg_cfg = RunConfig(thread_id="d07")
    fg_app = fg_builder.compile(checkpointer=fg_saver)
    fg_app.invoke({"x": 0}, fg_cfg)
    fg_out = fg_app.invoke(Command(resume="yes"), fg_cfg)
    assert fg_out["x"] == "yes" and fg_seen == ["yes"]

    up_seen: list[Any] = []

    def up_ask(state):
        up_seen.append(upstream_interrupt("approve?"))
        return {"x": "yes"}

    up_builder = UpstreamGraph(_State)
    up_builder.add_node("ask", up_ask)
    up_builder.add_edge(START, "ask")
    up_builder.add_edge("ask", END)
    up_saver = UpstreamSaver()
    up_cfg = _up_config("d07")
    up_app = up_builder.compile(checkpointer=up_saver)
    up_app.invoke({"x": 0}, up_cfg)
    up_out = up_app.invoke(UpstreamCommand(resume="yes"), up_cfg)
    assert up_out["x"] == "yes" and up_seen == ["yes"]


def test_d12_invalid_checkpointer_raises_type_error_on_both_sides() -> None:
    with pytest.raises(TypeError):
        _fg_linear().compile(checkpointer=object())
    with pytest.raises(TypeError):
        _up_linear().compile(checkpointer=object())


def test_d13_true_false_are_accepted_by_compile() -> None:
    for value in (True, False):
        assert _fg_linear().compile(checkpointer=value).checkpointer is value
        _up_linear().compile(checkpointer=value)


def test_d14_missing_thread_id_freegraph_skips_upstream_rejects() -> None:
    fg_saver = MemorySaver()
    out = _fg_linear().compile(checkpointer=fg_saver).invoke({"x": 0})
    assert out == {"x": 2}
    assert list(fg_saver.list(None)) == []

    up_saver = UpstreamSaver()
    with pytest.raises(Exception):
        _up_linear().compile(checkpointer=up_saver).invoke({"x": 0})


def test_d15_context_is_not_persisted_by_freegraph() -> None:
    fg_saver = MemorySaver()
    fg_cfg = RunConfig(thread_id="d15", context={"user": "a"})
    _fg_linear().compile(checkpointer=fg_saver).invoke({"x": 0}, fg_cfg)
    stored = fg_saver.get_tuple(fg_cfg)
    assert stored is not None
    assert stored.snapshot.config.context is None


def _normalized_pending(items) -> list[tuple[str, str, Any]]:
    normalized = []
    for task_id, channel, value in items:
        if isinstance(value, (list, tuple)):
            value = tuple(value)
        normalized.append((task_id, channel, value))
    return sorted(normalized, key=lambda item: (item[0], item[1], repr(item[2])))


def test_d04_put_writes_dedup_and_reserved_channels() -> None:
    fg_saver = MemorySaver()
    fg_cfg = fg_saver.put(RunConfig(thread_id="d04"), values={}, metadata={})
    for writes in ([("x", 1)], [("x", 2)], [("__interrupt__", ("p1",)), ("__interrupt__", ("p2",))]):
        fg_saver.put_writes(fg_cfg, writes=writes, task_id="n")
    fg_pending = fg_saver.get_tuple(fg_cfg).pending_writes

    up_saver = UpstreamSaver()
    up_cfg = {"configurable": {"thread_id": "d04", "checkpoint_ns": ""}}
    up_cfg = up_saver.put(up_cfg, empty_checkpoint(), {}, {})
    for writes in ([("x", 1)], [("x", 2)], [("__interrupt__", ("p1",)), ("__interrupt__", ("p2",))]):
        up_saver.put_writes(up_cfg, writes, "n")
    up_pending = up_saver.get_tuple(up_cfg).pending_writes

    assert _normalized_pending(fg_pending) == _normalized_pending(up_pending)


def test_d06_list_filter_before_and_limit() -> None:
    fg_saver = MemorySaver()
    fg_cfgs = [
        fg_saver.put(RunConfig(thread_id="d06"), values={"x": index}, metadata={"kind": kind})
        for index, kind in enumerate(("a", "b", "a"))
    ]
    fg_cfg = RunConfig(thread_id="d06")
    assert len(list(fg_saver.list(fg_cfg, filter={"kind": "a"}))) == 2
    assert len(list(fg_saver.list(fg_cfg, limit=2))) == 2
    assert len(list(fg_saver.list(fg_cfg, before=fg_cfgs[1]))) == 1

    up_saver = UpstreamSaver()
    up_base = {"configurable": {"thread_id": "d06", "checkpoint_ns": ""}}
    up_cfgs = []
    for kind in ("a", "b", "a"):
        up_cfgs.append(up_saver.put(up_base, empty_checkpoint(), {"kind": kind}, {}))
    assert len(list(up_saver.list(up_base, filter={"kind": "a"}))) == 2
    assert len(list(up_saver.list(up_base, limit=2))) == 2
    assert len(list(up_saver.list(up_base, before=up_cfgs[1]))) == 1


def test_d08_static_before_resume() -> None:
    fg_saver = MemorySaver()
    fg_cfg = RunConfig(thread_id="d08")
    fg_app = _fg_linear().compile(checkpointer=fg_saver, interrupt_before=["b"])
    fg_app.invoke({"x": 0}, fg_cfg)
    assert fg_app.invoke(Command(resume="x"), fg_cfg)["x"] == 2

    up_saver = UpstreamSaver()
    up_cfg = _up_config("d08")
    up_app = _up_linear().compile(checkpointer=up_saver, interrupt_before=["b"])
    up_app.invoke({"x": 0}, up_cfg)
    assert up_app.invoke(UpstreamCommand(resume="x"), up_cfg)["x"] == 2


def test_d09_send_fanout_interrupt_pending_writes() -> None:
    fg_builder = FG_Graph(_State)

    def fg_fan(state):
        return [FGSend("worker", {"n": 1}), FGSend("worker", {"n": 2})]

    def fg_worker(state):
        fg_interrupt("approve?")
        return {}

    fg_builder.add_node("fan", fg_fan)
    fg_builder.add_node("worker", fg_worker)
    fg_builder.add_edge(FG_START, "fan")
    fg_builder.add_edge("fan", "worker")
    fg_saver = MemorySaver()
    fg_cfg = RunConfig(thread_id="d09")
    fg_builder.compile(checkpointer=fg_saver).invoke({"x": 0}, fg_cfg)
    fg_pending = fg_saver.get_tuple(fg_cfg).pending_writes
    assert len([item for item in fg_pending if item[1] == "__interrupt__"]) == 2

    up_builder = UpstreamGraph(_State)

    def up_fan(state):
        return UpstreamCommand(
            goto=[UpstreamSend("worker", {"n": 1}), UpstreamSend("worker", {"n": 2})]
        )

    def up_worker(state):
        upstream_interrupt("approve?")
        return {}

    up_builder.add_node("fan", up_fan)
    up_builder.add_node("worker", up_worker)
    up_builder.add_edge(START, "fan")
    up_saver = UpstreamSaver()
    up_cfg = _up_config("d09")
    up_builder.compile(checkpointer=up_saver).invoke({"x": 0}, up_cfg)
    up_pending = _up_snapshots(up_saver, up_cfg)[0].pending_writes
    assert len([item for item in up_pending if item[1] == "__interrupt__"]) == 2


def test_d10_barrier_seen_and_single_target_run() -> None:
    fg_calls: list[str] = []
    fg_builder = FG_Graph(_State)
    for name in ("a", "b", "c"):
        fg_builder.add_node(name, lambda state, name=name: fg_calls.append(name) or {})
    fg_builder.add_edge(FG_START, "a")
    fg_builder.add_edge(FG_START, "b")
    fg_builder.add_edge(["a", "b"], "c")
    fg_builder.add_edge("c", FG_END)
    fg_saver = MemorySaver()
    fg_cfg = RunConfig(thread_id="d10")
    fg_app = fg_builder.compile(checkpointer=fg_saver, interrupt_before=["c"])
    fg_app.invoke({"x": 0}, fg_cfg)
    fg_app.invoke(Command(resume="x"), fg_cfg)
    assert fg_calls.count("c") == 1

    up_calls: list[str] = []
    up_builder = UpstreamGraph(_State)
    for name in ("a", "b", "c"):
        up_builder.add_node(name, lambda state, name=name: up_calls.append(name) or {})
    up_builder.add_edge(START, "a")
    up_builder.add_edge(START, "b")
    up_builder.add_edge(["a", "b"], "c")
    up_builder.add_edge("c", END)
    up_saver = UpstreamSaver()
    up_cfg = _up_config("d10")
    up_app = up_builder.compile(checkpointer=up_saver, interrupt_before=["c"])
    up_app.invoke({"x": 0}, up_cfg)
    up_app.invoke(UpstreamCommand(resume="x"), up_cfg)
    assert up_calls.count("c") == 1


def test_d11_true_error_with_interrupt_leaves_interrupt_pending_write() -> None:
    class Boom(RuntimeError):
        pass

    def fg_boom(state):
        raise Boom("boom")

    def fg_ask(state):
        fg_interrupt("approve?")
        return {}

    fg_builder = FG_Graph(_State)
    fg_builder.add_node("boom", fg_boom)
    fg_builder.add_node("ask", fg_ask)
    fg_builder.add_edge(FG_START, "boom")
    fg_builder.add_edge(FG_START, "ask")
    fg_saver = MemorySaver()
    fg_cfg = RunConfig(thread_id="d11")
    with pytest.raises(Boom):
        fg_builder.compile(checkpointer=fg_saver).invoke({"x": 0}, fg_cfg)
    assert any(
        channel == "__interrupt__"
        for _task, channel, _value in fg_saver.get_tuple(fg_cfg).pending_writes
    )

    def up_boom(state):
        raise Boom("boom")

    def up_ask(state):
        upstream_interrupt("approve?")
        return {}

    up_builder = UpstreamGraph(_State)
    up_builder.add_node("boom", up_boom)
    up_builder.add_node("ask", up_ask)
    up_builder.add_edge(START, "boom")
    up_builder.add_edge(START, "ask")
    up_saver = UpstreamSaver()
    up_cfg = _up_config("d11")
    with pytest.raises(Boom):
        up_builder.compile(checkpointer=up_saver).invoke({"x": 0}, up_cfg)
    assert any(
        channel == "__interrupt__"
        for _task, channel, _value in _up_snapshots(up_saver, up_cfg)[0].pending_writes
    )
