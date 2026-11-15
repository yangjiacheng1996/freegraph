# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B11F1 · ``Send`` 动态 fan-out 的运行期语义。"""

from __future__ import annotations

import operator

import pytest

from freegraph.graph import Command, Send, interrupt
from freegraph.runtime.channel import BinaryOperatorAggregate, LastValue
from freegraph.runtime.superstep import (
    GraphSpec,
    NodeSpec,
    SchedulerState,
    run_super_step,
    run_super_steps,
)


def _spec(nodes, edges, channels=None):
    return GraphSpec(
        channels=channels or {"out": BinaryOperatorAggregate("out", list, operator.add)},
        nodes=nodes,
        edges=edges,
    )


def test_carrier_b_calls_same_target_once_per_send_with_its_arg() -> None:
    calls = []

    def fan(state):
        return [Send("worker", {"n": 1}), Send("worker", {"n": 2})]

    def worker(state):
        calls.append(state)
        return {"out": [state["n"]]}

    spec = _spec(
        {"fan": NodeSpec((), fan), "worker": NodeSpec((), worker)},
        {"__start__": ("fan",), "fan": ("worker",)},
    )
    result = run_super_steps(spec, SchedulerState(), max_steps=10)
    assert sorted(calls, key=lambda item: item["n"]) == [{"n": 1}, {"n": 2}]
    assert result.state["out"] == [1, 2]
    assert result.executed.count("worker") == 2


def test_single_send_and_tuple_send_are_accepted() -> None:
    seen = []

    def single(state):
        return Send("worker", {"n": 1})

    def worker(state):
        seen.append(state["n"])
        return {}

    spec = _spec(
        {"fan": NodeSpec((), single), "worker": NodeSpec((), worker)},
        {"__start__": ("fan",), "fan": ("worker",)},
    )
    run_super_steps(spec, SchedulerState(), max_steps=10)
    assert seen == [1]


def test_fanout_runs_next_round_and_payload_is_one_shot() -> None:
    rounds = []

    def fan(state):
        rounds.append("fan")
        return [Send("worker", {"n": 1})]

    def worker(state):
        rounds.append("worker")
        return {}

    spec = _spec(
        {"fan": NodeSpec((), fan), "worker": NodeSpec((), worker)},
        {"__start__": ("fan",), "fan": ("worker",)},
    )
    run_super_steps(spec, SchedulerState(), max_steps=10)
    assert rounds == ["fan", "worker"]


def test_carrier_b_suppresses_static_edge_standard_call() -> None:
    calls = []

    def fan(state):
        return [Send("worker", {"n": 1}), Send("worker", {"n": 2})]

    def worker(state):
        calls.append(state["n"])
        return {"out": [state["n"]]}

    spec = _spec(
        {"fan": NodeSpec((), fan), "worker": NodeSpec((), worker)},
        {"__start__": ("fan",), "fan": ("worker",)},
    )
    result = run_super_steps(spec, SchedulerState(), max_steps=10)
    assert sorted(calls) == [1, 2]
    assert result.executed.count("worker") == 2


def test_carrier_a_goto_send_overlays_static_edge() -> None:
    calls = []

    def fan(state):
        return Command(
            goto=[Send("worker", {"n": 1}), Send("worker", {"n": 2})],
            update={"msgs": ["from-fan"]},
        )

    def worker(state):
        calls.append(state.get("n", 0))
        return {"out": [state.get("n", 0)]}

    spec = GraphSpec(
        channels={
            "out": BinaryOperatorAggregate("out", list, operator.add),
            "msgs": BinaryOperatorAggregate("msgs", list, operator.add),
        },
        nodes={"fan": NodeSpec((), fan), "worker": NodeSpec((), worker)},
        edges={"__start__": ("fan",), "fan": ("worker",)},
    )
    result = run_super_steps(spec, SchedulerState(), max_steps=10)
    assert sorted(calls) == [0, 1, 2]
    assert result.state["msgs"] == ["from-fan"]


def test_carrier_a_mixed_goto_str_and_send() -> None:
    seen = []

    def fan(state):
        return Command(goto=["other", Send("worker", {"n": 3})])

    def other(state):
        seen.append("other")
        return {}

    def worker(state):
        seen.append(state["n"])
        return {}

    spec = _spec(
        {
            "fan": NodeSpec((), fan),
            "other": NodeSpec((), other),
            "worker": NodeSpec((), worker),
        },
        {"__start__": ("fan",)},
    )
    run_super_steps(spec, SchedulerState(), max_steps=10)
    assert set(seen) == {3, "other"}


def test_unknown_target_fails_and_names_producer_and_target() -> None:
    def fan(state):
        return Send("nope", {})

    spec = _spec({"fan": NodeSpec((), fan)}, {"__start__": ("fan",)})
    with pytest.raises(ValueError) as exc:
        run_super_steps(spec, SchedulerState(), max_steps=5)
    assert "fan" in str(exc.value)
    assert "nope" in str(exc.value)


@pytest.mark.parametrize(
    ("send", "exc_type"),
    [
        (Send(Command.PARENT, {}), NotImplementedError),
        (Send("__start__", {}), ValueError),
        (Send("__end__", {}), ValueError),
        (Send("", {}), ValueError),
        (Send(123, {}), TypeError),  # type: ignore[arg-type]
    ],
)
def test_reserved_and_invalid_targets(send, exc_type) -> None:
    def fan(state):
        return send

    spec = _spec(
        {"fan": NodeSpec((), fan), "worker": NodeSpec((), lambda s: {})},
        {"__start__": ("fan",)},
    )
    with pytest.raises(exc_type):
        run_super_steps(spec, SchedulerState(), max_steps=5)


def test_validate_send_rejects_non_send_element() -> None:
    from freegraph.runtime._fanout import validate_send

    with pytest.raises(TypeError):
        validate_send({"node": "worker"}, {"worker"}, "fan")


def test_payload_shape_errors() -> None:
    def empty(state):
        return []

    def mixed(state):
        return [Send("worker", {}), {"x": 1}]

    def bad_command_list(state):
        return [Send("worker", {}), Command()]

    for fn in (empty, mixed, bad_command_list):
        spec = _spec(
            {"fan": NodeSpec((), fn), "worker": NodeSpec((), lambda s: {})},
            {"__start__": ("fan",)},
        )
        with pytest.raises(TypeError):
            run_super_steps(spec, SchedulerState(), max_steps=5)


def test_fanout_writes_are_reduced_in_deterministic_order() -> None:
    def fan(state):
        return [Send("worker", {"n": 1}), Send("worker", {"n": 2})]

    def worker(state):
        return {"out": [state["n"]]}

    spec = _spec(
        {"fan": NodeSpec((), fan), "worker": NodeSpec((), worker)},
        {"__start__": ("fan",), "fan": ("worker",)},
    )
    first = run_super_steps(spec, SchedulerState(), max_steps=10).state["out"]
    for _ in range(3):
        assert run_super_steps(spec, SchedulerState(), max_steps=10).state["out"] == first


def test_fanout_round_is_atomic_on_error() -> None:
    def fan(state):
        return [Send("worker", {"n": 1}), Send("worker", {"n": 2})]

    def worker(state):
        if state["n"] == 2:
            raise RuntimeError("boom")
        return {"out": [state["n"]]}

    spec = _spec(
        {"fan": NodeSpec((), fan), "worker": NodeSpec((), worker)},
        {"__start__": ("fan",), "fan": ("worker",)},
    )
    state = SchedulerState()
    with pytest.raises(RuntimeError):
        run_super_steps(spec, state, max_steps=10)
    assert state.channel_versions.get("out", 0) == 0
    assert not state.channels["out"].is_available() or state.channels["out"].get() == []


def test_each_fanout_task_gets_an_independent_interrupt_id() -> None:
    def fan(state):
        return [Send("worker", {"n": 1}), Send("worker", {"n": 2})]

    def worker(state):
        interrupt({"n": state["n"]})
        return {}

    spec = _spec(
        {"fan": NodeSpec((), fan), "worker": NodeSpec((), worker)},
        {"__start__": ("fan",), "fan": ("worker",)},
    )
    with pytest.raises(Exception) as exc:
        run_super_steps(spec, SchedulerState(), max_steps=10)
    payload = exc.value.args[0]
    assert len(payload) == 2
    assert len({item.id for item in payload}) == 2
