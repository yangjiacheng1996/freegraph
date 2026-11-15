# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B11F1 · 机械层一键验收（``Send`` 动态 fan-out / map-reduce）。"""

from __future__ import annotations

import operator
import sys

from freegraph.graph import Command, Send
from freegraph.runtime.channel import BinaryOperatorAggregate
from freegraph.runtime.superstep import GraphSpec, NodeSpec, SchedulerState, run_super_steps


def _channel(key: str):
    return BinaryOperatorAggregate(key, list, operator.add)


def _carrier_b() -> None:
    calls: list[dict] = []

    def fan(state):
        return [Send("worker", {"n": 1}), Send("worker", {"n": 2})]

    def worker(state):
        calls.append(state)
        return {"out": [state["n"]]}

    spec = GraphSpec(
        channels={"out": _channel("out")},
        nodes={"fan": NodeSpec((), fan), "worker": NodeSpec((), worker)},
        edges={"__start__": ("fan",), "fan": ("worker",)},
    )
    result = run_super_steps(spec, SchedulerState(), max_steps=10)
    assert calls == [{"n": 1}, {"n": 2}]
    assert result.state["out"] == [1, 2]


def _carrier_a() -> None:
    calls: list[dict] = []

    def fan(state):
        return Command(
            goto=[Send("worker", {"n": 1}), Send("worker", {"n": 2})],
            update={"msgs": ["from-fan"]},
        )

    def worker(state):
        calls.append(state)
        return {"out": [state.get("n", 0)]}

    spec = GraphSpec(
        channels={"out": _channel("out"), "msgs": _channel("msgs")},
        nodes={"fan": NodeSpec((), fan), "worker": NodeSpec((), worker)},
        edges={"__start__": ("fan",), "fan": ("worker",)},
    )
    result = run_super_steps(spec, SchedulerState(), max_steps=10)
    assert calls == [{}, {"n": 1}, {"n": 2}]
    assert result.state["msgs"] == ["from-fan"]


def _invalid_target() -> None:
    def fan(state):
        return Send("nope", {})

    spec = GraphSpec(
        channels={},
        nodes={"fan": NodeSpec((), fan)},
        edges={"__start__": ("fan",)},
    )
    try:
        run_super_steps(spec, SchedulerState(), max_steps=5)
    except ValueError as exc:
        assert "fan" in str(exc) and "nope" in str(exc)
    else:  # pragma: no cover - 防御
        raise AssertionError("未知目标未显式失败")


def main() -> int:
    _carrier_b()
    _carrier_a()
    _invalid_target()
    print("B11F1 acceptance: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
