# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B13F1 · fan-out × 静态断点：N 个任务独立命中、现场保留、空载荷。"""

from __future__ import annotations

import operator

from freegraph.contracts import RunConfig, Send
from freegraph.runtime import GraphSpec, InterruptResult, NodeSpec, run_graph
from freegraph.runtime.channel import BinaryOperatorAggregate

from .test_interrupt_checkpoint import StubCheckpointer


def _fanout_spec(*, before=(), after=(), mixed: bool = False):
    calls = {"fan": 0, "worker": 0, "other": 0}

    def fan(state: dict):
        calls["fan"] += 1
        return [Send("worker", {"n": 1}), Send("worker", {"n": 2})]

    def worker(state: dict) -> dict:
        calls["worker"] += 1
        return {"out": [state["n"]]}

    def other(state: dict) -> dict:
        calls["other"] += 1
        return {"out": ["other"]}

    nodes = {"fan": NodeSpec((), fan), "worker": NodeSpec((), worker)}
    edges = {"__start__": ("fan",)}
    if mixed:
        nodes["other"] = NodeSpec((), other)
        edges["fan"] = ("other",)
    return (
        GraphSpec(
            channels={"out": BinaryOperatorAggregate("out", list, operator.add)},
            nodes=nodes,
            edges=edges,
            interrupt_before=before,
            interrupt_after=after,
        ),
        calls,
    )


def test_before_fanout_keeps_all_tasks_and_executes_none() -> None:
    spec, calls = _fanout_spec(before=("worker",))
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-fan-before")
    paused = run_graph(spec, checkpointer=stub, config=config)
    assert isinstance(paused, InterruptResult)
    assert calls["worker"] == 0
    assert paused.interrupts == ()
    assert paused.executed == ("fan",)
    assert paused.steps == 1
    metadata = stub.snapshots["t-fan-before"]["metadata"]
    assert metadata["next"] == ()
    assert metadata["suspension_kind"] == "static_before"
    assert len(metadata["scheduler"]["fanout"]) == 1
    tasks = next(iter(metadata["scheduler"]["fanout"].values()))["tasks"]
    assert [task["target"] for task in tasks] == ["worker", "worker"]
    assert [task["arg"] for task in tasks] == [{"n": 1}, {"n": 2}]


def test_before_fanout_resume_retries_the_exact_two_tasks() -> None:
    spec, calls = _fanout_spec(before=("worker",))
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-fan-resume")
    assert isinstance(run_graph(spec, checkpointer=stub, config=config), InterruptResult)
    resumed = run_graph(spec, None, checkpointer=stub, config=config)
    assert not isinstance(resumed, InterruptResult)
    assert calls["worker"] == 2
    assert resumed.executed == ("worker", "worker")
    assert resumed.state["out"] == [1, 2]


def test_after_fanout_executes_n_times_then_suspends() -> None:
    spec, calls = _fanout_spec(after=("worker",))
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-fan-after")
    paused = run_graph(spec, checkpointer=stub, config=config)
    assert isinstance(paused, InterruptResult)
    assert calls["worker"] == 2
    assert paused.executed.count("worker") == 2
    assert paused.state["out"] == [1, 2]
    assert paused.interrupts == ()
    resumed = run_graph(spec, None, checkpointer=stub, config=config)
    assert not isinstance(resumed, InterruptResult)
    assert calls["worker"] == 2


def test_before_mixed_round_skips_standard_tasks_too() -> None:
    spec, calls = _fanout_spec(before=("worker",), mixed=True)
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-fan-mixed")
    paused = run_graph(spec, checkpointer=stub, config=config)
    assert isinstance(paused, InterruptResult)
    assert calls["other"] == 0
    assert calls["worker"] == 0
    assert paused.executed == ("fan",)


def test_static_fanout_does_not_forge_interrupt_payloads() -> None:
    spec, _ = _fanout_spec(before=("worker",))
    stub = StubCheckpointer()
    paused = run_graph(spec, checkpointer=stub, config=RunConfig(thread_id="t-fan-payload"))
    assert isinstance(paused, InterruptResult)
    assert paused.interrupts == ()
    assert paused.as_result_dict()["__interrupt__"] == ()
