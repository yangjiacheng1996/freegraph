# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**触发判定与版本号**的用例 —— 属 **B7F1**（tasks T029 / T030 / T032 / T033）。

覆盖的判定：

* **SC-003** —— 写入一个与当前值**逐字相等**的值后下游订阅者**仍被触发**；
  「同一版本重复触发同一节点」的出现次数 == **0**；
* **SC-004** —— 未被触发的节点执行次数 == **0**；被触发的节点执行次数 == **1**；
* **SC-012** —— 通道的写入版本**仅**在 `update()` 返回**真**时推进。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Any

from freegraph.runtime import (
    BinaryOperatorAggregate,
    Channel,
    EphemeralValue,
    GraphSpec,
    LastValue,
    NodeSpec,
    SchedulerState,
    run_super_step,
    run_super_steps,
)


def _channels() -> dict[str, Channel]:
    """构造通道状态：**覆盖型**（``count``）+ **归约型**（``messages``）。"""
    return {
        "count": LastValue("count", int),
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
    }


# ── T029 · 未被触发的节点不执行（SC-004）────────────────────────────────


def test_an_untriggered_node_never_runs_while_a_triggered_one_runs_once() -> None:
    """**SC-004**：未被触发的节点执行次数 == **0**；被触发的节点执行次数 == **1**。"""
    channels = _channels()
    channels["count"].update([1])
    calls: list[str] = []

    def triggered(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("triggered")
        return {}

    def untriggered(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("untriggered")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "triggered": NodeSpec(subscribes=("count",), run=triggered),
            "untriggered": NodeSpec(subscribes=(), run=untriggered),
        },
        edges={},
    )

    result = run_super_step(spec, SchedulerState())

    assert calls == ["triggered"]
    assert result.executed == ("triggered",)


# ── T030 · 同一版本不重复触发（SC-003）──────────────────────────────────


def test_the_same_version_never_triggers_the_same_node_twice() -> None:
    """**SC-003**：同一版本再次进入触发判定 ⇒ 该节点**不被重复触发**。

    ⚠️ 用**同一个**调度状态跑两轮 ⇒ 第二轮看到的版本**未变** ⇒ 不触发。
    """
    channels = _channels()
    channels["count"].update([1])
    calls: list[str] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("node")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={"node": NodeSpec(subscribes=("count",), run=node)},
        edges={},
    )
    state = SchedulerState()

    first = run_super_step(spec, state)
    second = run_super_step(spec, state)

    assert calls == ["node"]
    assert first.executed == ("node",)
    assert second.executed == ()


def test_advancing_one_trigger_source_does_not_mask_another_one() -> None:
    """**SC-003**：一个触发源的推进 MUST **不**掩盖另一个触发源的推进。

    ⚠️ 「推进」MUST 由**调度层**的写入产生（调用方的直接写入**不**进版本推进
    路径 · 裁定 31）⇒ 用一个**节点写入**另一个触发源来制造推进。
    """
    channels = _channels()
    channels["count"].update([1])
    calls: list[str] = []

    def writer(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("writer")
        return {"other": 1}

    def reader(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("reader")
        return {}

    spec = GraphSpec(
        channels={**channels, "other": LastValue("other", int)},
        nodes={
            "writer": NodeSpec(subscribes=("count",), run=writer),
            "reader": NodeSpec(subscribes=("count", "other"), run=reader),
        },
        edges={},
    )
    state = SchedulerState()

    first = run_super_step(spec, state)
    assert calls == ["writer", "reader"]
    assert first.executed == ("writer", "reader")

    # 第 2 轮：``count`` 的版本**未推进** ⇒ 只有 ``other`` 触发 ``reader``。
    second = run_super_step(spec, state)

    assert calls == ["writer", "reader", "reader"]
    assert second.executed == ("reader",)


# ── T032 · 值逐字相等仍触发下游（SC-003）───────────────────────────────


def test_writing_a_literally_equal_value_still_triggers_the_subscriber() -> None:
    """**SC-003**：写入一个与当前值**逐字相等**的值 ⇒ 下游订阅者**仍被触发**。

    ⚠️ 触发判定 MUST 依据**版本号**，MUST NOT 依据「值是否变化」（FR-002）。

    ⚠️ 第 1 轮里订阅者被「**跑之前**的初始值」触发（第 1 次）；
    第 2 轮里它被「**逐字相等**的那次写入」触发（第 2 次）⇒ 两次触发之间
    通道的**值完全没变** ⇒ 版本推进 ⇒ 仍被触发。
    """
    channels: dict[str, Channel] = {
        "seed": LastValue("seed", int),
        "count": LastValue("count", int),
    }
    channels["seed"].update([1])
    channels["count"].update([5])
    calls: list[str] = []

    def writer(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("writer")
        return {"count": 5}  # 与当前值**逐字相等**

    def sink(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("sink")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "sink": NodeSpec(subscribes=("count",), run=sink),
        },
        edges={},
    )
    state = SchedulerState()

    run_super_step(spec, state)
    assert calls == ["writer", "sink"]

    # ⚠️ 通道的值**完全没变**（仍是 5）⇒ 版本推进 ⇒ 订阅者**仍被触发**。
    run_super_step(spec, state)

    assert calls == ["writer", "sink", "sink"]
    assert channels["count"].get() == 5
    assert state.channel_versions["count"] == 2


# ── T033 · 版本推进的口径（SC-003 / SC-012）────────────────────────────


def test_the_channel_version_advances_only_on_a_successful_write() -> None:
    """**SC-003**：通道的写入版本**仅**在 ``update()`` 返回**真**时推进。

    ⚠️ 写一个**逐字相等**的值 ⇒ ``update()`` 仍返回**真** ⇒ 版本**推进**
    ⇒ 订阅者**仍被触发**（FR-002）。
    """
    channels = _channels()
    channels["count"].update([5])
    state = SchedulerState()

    def node(state: dict[str, Any]) -> dict[str, Any]:
        return {"count": 5}

    spec = GraphSpec(
        channels=channels,
        nodes={"node": NodeSpec(subscribes=("count",), run=node)},
        edges={},
    )

    run_super_step(spec, state)

    assert state.channel_versions["count"] == 2


def test_clearing_a_routing_channel_does_not_advance_its_version() -> None:
    """**SC-012**：路由型通道被清空后其版本**未推进** ⇒ 订阅者**不**被再次触发。

    ⚠️ 「清空不是写入」（FR-014）⇒ 版本不动 ⇒ 下一轮**不**触发。
    """
    channels: dict[str, Channel] = {
        "count": LastValue("count", int),
        "route": EphemeralValue("route", str),
    }
    channels["count"].update([1])
    channels["route"].update(["payload"])
    calls: list[str] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("node")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={"node": NodeSpec(subscribes=("count", "route"), run=node)},
        edges={},
    )
    state = SchedulerState()

    run_super_step(spec, state)

    # 「有值」即版本 1（裁定 21）⇒ 步末清空**不**推进它（清空不是写入）。
    assert state.channel_versions["route"] == 1
    assert channels["route"].is_available() is False


class _SilentChannel(Channel):
    """一个**拒绝写入**的自定义通道（``update()`` 返回**假**）。

    ⚠️ B5F1 的通道契约允许第三方实现 ⇒ 「本轮是否写入过」的判定 MUST 以
    ``Channel.update()`` 的**返回值**为准（契约 §5.1 · FR-002 ⚠️）⇒ 本用例
    守住「返回**假** ⇒ 版本**不**推进」这条口径。
    """

    def __init__(self, key: str, value_type: Any) -> None:
        super().__init__(key, value_type)
        self.update_calls = 0

    def update(self, values: Any) -> bool:
        self.update_calls += 1
        return False

    def get(self) -> Any:
        raise AssertionError("本通道永远无值")

    def is_available(self) -> bool:
        return False


def test_a_channel_whose_update_returns_false_does_not_advance_its_version() -> None:
    """**SC-003**：``update()`` 返回**假** ⇒ 该通道的写入版本**不**推进。

    ⚠️ 「本轮写入了值」的判定 MUST 以 ``Channel.update()`` 的**返回值**为准
    （契约 §5.1 · FR-002 ⚠️）⇒ 返回**假** ⇒ 版本**不**推进 ⇒ 订阅者**不**被
    再次触发。
    """
    channels: dict[str, Channel] = {
        "count": LastValue("count", int),
        "silent": _SilentChannel("silent", int),
    }
    channels["count"].update([1])
    calls: list[str] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("node")
        return {"silent": 5}

    spec = GraphSpec(
        channels=channels,
        nodes={"node": NodeSpec(subscribes=("count", "silent"), run=node)},
        edges={},
    )
    state = SchedulerState()

    run_super_step(spec, state)
    assert calls == ["node"]

    run_super_step(spec, state)

    assert calls == ["node"]
    assert state.channel_versions.get("silent", 0) == 0
