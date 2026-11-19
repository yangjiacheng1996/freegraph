# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""B8F2 · ``SuperStepResult.tasks`` / ``PregelTask`` 的运行时判据（T014）。"""

from __future__ import annotations

import dataclasses
from typing import Annotated, TypedDict

import pytest

from freegraph.contracts import GraphInterrupt, PregelTask, Send
from freegraph.graph import END, START, StateGraph, interrupt
from freegraph.runtime import SchedulerState, SuperStepResult, run_super_step, run_super_steps


class _State(TypedDict):
    x: int
    log: Annotated[list[str], lambda left, right: [*left, *right]]


def _linear():
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_node("b", lambda state: {"x": 2})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder.compile()


def test_the_original_four_fields_are_kept_and_tasks_is_appended() -> None:
    """T-1：原 4 字段逐字保留 + 末尾追加 ``tasks``（缺省 ``()``）。"""
    assert [field.name for field in dataclasses.fields(SuperStepResult)] == [
        "state",
        "executed",
        "node_writes",
        "steps",
        "tasks",
    ]
    assert SuperStepResult(state={}, executed=(), node_writes={}, steps=1).tasks == ()


def test_a_successful_round_produces_one_pregel_task_per_task() -> None:
    compiled = _linear()
    result = run_super_step(compiled._spec, SchedulerState())
    assert len(result.tasks) == 1
    task = result.tasks[0]
    assert isinstance(task, PregelTask)
    assert task.name == "a"
    assert task.path == ("a",)
    assert task.error is None
    assert task.interrupts == ()
    assert task.state is None
    assert task.result == {"x": 1}


def test_run_super_steps_accumulates_tasks_in_round_order() -> None:
    compiled = _linear()
    result = run_super_steps(compiled._spec)
    assert [task.name for task in result.tasks] == ["a", "b"]
    assert [task.result for task in result.tasks] == [{"x": 1}, {"x": 2}]


def test_fanout_tasks_have_fanout_path_and_unique_ids() -> None:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: [Send("b", {"x": 1}), Send("b", {"x": 2})])
    builder.add_node("b", lambda state: {"log": [str(state["x"])]})
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    compiled = builder.compile()
    result = run_super_steps(compiled._spec)
    fanout = [task for task in result.tasks if task.name == "b"]
    assert len(fanout) == 2
    assert all(task.path[0] == "b" and len(task.path) == 2 for task in fanout)
    assert len({task.id for task in fanout}) == 2


def test_interrupt_round_does_not_produce_a_superstep_result() -> None:
    class _S(TypedDict):
        x: int

    def stop(state: _S) -> dict[str, int]:
        interrupt("approve?")
        return {"x": 1}

    builder = StateGraph(_S)
    builder.add_node("stop", stop)
    builder.add_edge(START, "stop")
    builder.add_edge("stop", END)
    compiled = builder.compile()
    with pytest.raises(GraphInterrupt):
        run_super_step(compiled._spec, SchedulerState())
