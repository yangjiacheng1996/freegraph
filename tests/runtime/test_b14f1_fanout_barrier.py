# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B14F1 · fan-out task_id / pending writes / 多源屏障跨 checkpoint。"""

from __future__ import annotations

from freegraph.contracts import RunConfig, Send
from freegraph.graph import interrupt
from freegraph.persistence import MemorySaver
from freegraph.runtime import (
    GraphSpec,
    InterruptResult,
    LastValue,
    NodeSpec,
    run_graph,
)


def test_fanout_interrupt_pending_writes_use_unique_task_ids() -> None:
    def fan(state):
        return [Send("worker", {"n": 1}), Send("worker", {"n": 2})]

    def worker(state):
        interrupt("approve?")
        return {}

    spec = GraphSpec(
        channels={},
        nodes={"fan": NodeSpec((), fan), "worker": NodeSpec((), worker)},
        edges={"__start__": ("fan",), "fan": ("worker",)},
    )
    saver = MemorySaver()
    cfg = RunConfig(thread_id="fanout")
    result = run_graph(spec, checkpointer=saver, config=cfg)
    assert isinstance(result, InterruptResult)

    stored = saver.get_tuple(cfg)
    assert stored is not None
    task_ids = [
        task_id
        for task_id, channel, _value in stored.pending_writes
        if channel == "__interrupt__"
    ]
    assert task_ids == ["worker:0", "worker:1"]
    assert len(set(task_ids)) == 2
    assert len(stored.snapshot.interrupts) == 2


def test_standard_task_uses_node_name_as_task_id() -> None:
    def ask(state):
        interrupt("approve?")
        return {}

    spec = GraphSpec(
        channels={},
        nodes={"ask": NodeSpec((), ask)},
        edges={"__start__": ("ask",)},
    )
    saver = MemorySaver()
    cfg = RunConfig(thread_id="standard")
    run_graph(spec, checkpointer=saver, config=cfg)
    stored = saver.get_tuple(cfg)
    assert stored is not None
    assert [item[0] for item in stored.pending_writes] == ["ask"]


def test_barrier_seen_survives_checkpoint_and_target_runs_once() -> None:
    calls: list[str] = []
    entry = NodeSpec((), lambda state: {})

    def recorder(name: str):
        def run(state):
            calls.append(name)
            return {}

        return run

    spec = GraphSpec(
        channels={"x": LastValue("x", int)},
        nodes={
            "__start__": entry,
            "a": NodeSpec((), recorder("a")),
            "b": NodeSpec((), recorder("b")),
            "c": NodeSpec((), recorder("c")),
        },
        edges={"__start__": ("a", "b"), ("a", "b"): ("c",)},
        interrupt_before=("c",),
    )
    saver = MemorySaver()
    cfg = RunConfig(thread_id="barrier")
    paused = run_graph(spec, checkpointer=saver, config=cfg)
    assert isinstance(paused, InterruptResult)
    # a / b 同轮并发 ⇒ 记录顺序不可观察；只断言两者都跑过（屏障语义）。
    assert sorted(calls) == ["a", "b"]

    resumed = run_graph(spec, None, checkpointer=saver, config=cfg)
    assert not isinstance(resumed, InterruptResult)
    assert calls.count("c") == 1

    stored = saver.get_tuple(cfg)
    assert stored is not None
    seen = stored.scheduler["versions_seen"]["c"]
    assert ["e", "a", 1] in seen
    assert ["e", "b", 1] in seen
