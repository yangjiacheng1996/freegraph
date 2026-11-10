# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**步末清空范围**的用例 —— 属 **B7F1**（tasks T043）。

覆盖的判定：

* **SC-012** —— 步末对**覆盖型 / 归约型**通道调用 `clear()` 的次数 == **0**；
  步末对**本轮被写入过的**路由型通道调用 `clear()` 的次数 == **0**
  （其值 MUST 保留到下一轮）；
  步末对**本轮未被写入的**路由型通道调用的比例 == **100%**；
* 步末清空**不推进**通道的写入版本（清空**不是**写入）。

⚠️ **计数窗口 MUST 限定在「步末清空阶段」** —— 合并阶段的**回滚路径**也会调
`clear()`，那些调用**不计入**本文件的判据（裁定 29 的豁免）。

⚠️ **探针 MUST 保持通道的**类型**（``isinstance``）** —— FR-014 把「路由型」的
判定**冻结**为 ``isinstance(channel, EphemeralValue)`` ⇒ 探针 MUST 是
``EphemeralValue`` 的**子类**（MUST NOT 用一个无关的包装类）。

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


class _CountingMixin:
    """**计数混入** —— 记录 ``clear()`` 的调用次数（**不改变**语义）。"""

    clear_calls: int

    def _count_clear(self) -> None:
        self.clear_calls += 1


class _CountingLastValue(_CountingMixin, LastValue):
    """**计数覆盖型**通道（``isinstance(channel, LastValue)`` 仍成立）。"""

    def __init__(self, key: str, value_type: Any) -> None:
        super().__init__(key, value_type)
        self.clear_calls = 0

    def clear(self) -> bool:
        self.clear_calls += 1
        return super().clear()


class _CountingBinaryOperator(_CountingMixin, BinaryOperatorAggregate):
    """**计数归约型**通道（``isinstance(..., BinaryOperatorAggregate)`` 仍成立）。"""

    def __init__(self, key: str, value_type: Any, reducer: Any) -> None:
        super().__init__(key, value_type, reducer)
        self.clear_calls = 0

    def clear(self) -> bool:
        self.clear_calls += 1
        return super().clear()


class _CountingEphemeral(_CountingMixin, EphemeralValue):
    """**计数路由型**通道（``isinstance(channel, EphemeralValue)`` 仍成立）。"""

    def __init__(self, key: str, value_type: Any) -> None:
        super().__init__(key, value_type)
        self.clear_calls = 0

    def clear(self) -> bool:
        self.clear_calls += 1
        return super().clear()


def _channels() -> dict[str, Channel]:
    """构造通道状态：**覆盖型** + **归约型** + **路由型**各一（**计数探针**）。"""
    return {
        "overwrite": _CountingLastValue("overwrite", int),
        "reduce": _CountingBinaryOperator("reduce", list, operator.add),
        "route": _CountingEphemeral("route", str),
    }


def _spec(channels: dict[str, Channel], writes: dict[str, Any]) -> GraphSpec:
    """构造一份「跑一轮、写指定内容」的图规格。"""
    channels["seed"] = LastValue("seed", int)
    channels["seed"].update([1])
    return GraphSpec(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("seed",), run=lambda state: writes)},
        edges={},
    )


# ── T043 · 步末清空的范围（SC-012）──────────────────────────────────────


def test_no_overwriting_or_reducing_channel_is_ever_cleared() -> None:
    """**SC-012**：步末对**覆盖型 / 归约型**通道调 `clear()` 的次数 == **0**。"""
    channels = _channels()
    spec = _spec(channels, {"overwrite": 5, "reduce": ["x"]})

    run_super_step(spec, SchedulerState())

    assert channels["overwrite"].clear_calls == 0
    assert channels["reduce"].clear_calls == 0


def test_a_routing_channel_written_this_round_is_kept() -> None:
    """**SC-012**：步末对**本轮被写入过的**路由型通道调 `clear()` 的次数 == **0**。

    ⚠️ 它的值 MUST **保留到下一轮**（⇒ B8F1 的条件边路由读得到「本节点本次
    写入」）。
    """
    channels = _channels()
    spec = _spec(channels, {"route": "payload"})

    run_super_step(spec, SchedulerState())

    assert channels["route"].clear_calls == 0
    assert channels["route"].get() == "payload"


def test_every_unwritten_routing_channel_is_cleared() -> None:
    """**SC-012**：步末对**本轮未被写入的**路由型通道调用的比例 == **100%**。"""
    channels = _channels()
    channels["route"].update(["payload"])
    spec = _spec(channels, {"overwrite": 5})

    run_super_step(spec, SchedulerState())

    assert channels["route"].clear_calls == 1
    assert channels["route"].is_available() is False


def test_both_entries_clear_the_routing_channels_the_same_way() -> None:
    """**SC-012**：两个入口的步末清空**调用集合与次数逐项相等**（裁定 33）。

    ⚠️ 单轮入口 MUST **不**存在「保留路由型通道的值」这第三种语义。
    """
    single_calls: list[int] = []
    multi_calls: list[int] = []

    for sink in (single_calls, multi_calls):
        channels = _channels()
        channels["route"].update(["payload"])
        spec = _spec(channels, {"overwrite": 5})
        if sink is single_calls:
            run_super_step(spec, SchedulerState())
        else:
            run_super_steps(spec)
        sink.append(channels["route"].clear_calls)

    assert single_calls == multi_calls == [1]


def test_clearing_a_routing_channel_does_not_advance_its_version() -> None:
    """**SC-012**：路由型通道被清空 ⇒ 其写入版本**未推进**（清空不是写入）。"""
    channels = _channels()
    channels["route"].update(["payload"])
    spec = _spec(channels, {"overwrite": 5})
    state = SchedulerState()

    run_super_step(spec, state)

    assert state.channel_versions.get("route", 0) == 0
    assert state.channel_versions["overwrite"] == 1
