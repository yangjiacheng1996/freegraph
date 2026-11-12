# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**触发判定与版本号**的用例 —— 属 **B7F1**（tasks T029 / T030 / T032 / T033）。

覆盖的判定：

* **SC-003** —— 写入一个与当前值**逐字相等**的值后下游节点**仍被触发**；
  「同一版本重复触发同一节点」的出现次数 == **0**；
* **SC-004** —— 未被触发的节点执行次数 == **0**；被触发的节点执行次数 == **1**；
* **SC-012** —— 通道的写入版本**仅**在 `update()` 返回**真**时推进。

⚠️ **2026-11-12 · 上游对齐（P1-0-2）**：触发源**恒为边**（上游 ``branch:to:<node>``
· ``langgraph/graph/state.py:1531-1532``）⇒ 本文件的夹具一律带**入口边**
（``edges={"__start__": ("首节点",)}`）⇒ ``subscribes`` **只**决定「读哪些通道」
（上游 ``langgraph/graph/state.py:1534``），**不再**是触发源 ⇒ 「写通道 ⇒ 订阅者
被触发」的现象出现次数 == **0**（**上游同款**）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import pytest

import operator
from typing import Any

from freegraph.runtime.channel import MISSING
from freegraph.runtime import (
    EmptyChannelError,
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


#: **入口哨兵节点**（上游 ``START`` 同款 · ``langgraph/constants.py:30``）。
#:
#: ⚠️ 它**无入边** ⇒ **永不执行**（永不进 ``executed``）⇒ 它只作「入口边」的**源**。
#:
#: ⚠️ **为什么它 MUST 在节点表里** —— ``GraphSpec`` 的校验规则 **V-2** 要求
#: 「边的**源** MUST 在节点表里」⇒ 入口边 ``edges={"__start__": ("首节点",)}``
#: 的源 ``__start__`` 也 MUST 在节点表里（上游的 ``START`` 是**编译期**补进去的
#: 伪节点 · ``langgraph/graph/state.py:321`` ⇒ freegraph 在**手写图规格**层面
#: 用「节点表里的一个哨兵节点」表达**同款**语义）。
_ENTRY = NodeSpec(subscribes=(), run=lambda state: {})


# ── T029 · 未被触发的节点不执行（SC-004）────────────────────────────────


def test_an_untriggered_node_never_runs_while_a_triggered_one_runs_once() -> None:
    """**SC-004**：未被触发的节点执行次数 == **0**；被触发的节点执行次数 == **1**。

    ⚠️ **上游同款**：未被触发的节点**订阅了有值的通道**（``count``）却**无入边**
    ⇒ 触发源**恒为边** ⇒ 它**永不**执行。
    """
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
            "__start__": _ENTRY,
            "triggered": NodeSpec(subscribes=("count",), run=triggered),
            "untriggered": NodeSpec(subscribes=("count",), run=untriggered),
        },
        edges={"__start__": ("triggered",)},
    )

    result = run_super_step(spec, SchedulerState())

    assert calls == ["triggered"]
    assert result.executed == ("triggered",)


# ── T030 · 同一版本不重复触发（SC-003）──────────────────────────────────


def test_the_same_version_never_triggers_the_same_node_twice() -> None:
    """**SC-003**：同一版本再次进入触发判定 ⇒ 该节点**不被重复触发**。

    ⚠️ 用**同一个**调度状态跑两轮 ⇒ 第二轮看到的版本**未变** ⇒ 不触发。

    ⚠️ **上游同款**：入口哨兵的版本**恒为 1** ⇒ 入口节点**只在第 1 轮**被触发
    一次（上游 ``add_edge(START, "a")`` 的入口边只写过一次）。
    """
    channels = _channels()
    channels["count"].update([1])
    calls: list[str] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("node")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={"__start__": _ENTRY, "node": NodeSpec(subscribes=("count",), run=node)},
        edges={"__start__": ("node",)},
    )
    state = SchedulerState()

    first = run_super_step(spec, state)
    second = run_super_step(spec, state)

    assert calls == ["node"]
    assert first.executed == ("node",)
    assert second.executed == ()


@pytest.mark.parametrize("max_concurrency", [1, None], ids=["serial", "concurrent"])
def test_advancing_one_trigger_source_does_not_mask_another_one(
    max_concurrency: int | None,
) -> None:
    """**SC-003**：一个触发源的推进 MUST **不**掩盖另一个触发源的推进。

    ⚠️ 触发源**恒为边** ⇒ 两个触发源 = 两条**入边**的**源**（``__start__`` 与
    ``writer``）⇒ 第 2 轮里 ``__start__`` 的版本**未推进**（恒为 1）、
    ``writer`` 的**执行版本**推进到 1 ⇒ ``reader`` **仍被触发**。

    ⚠️ 「推进」MUST 由**节点执行**产生（调用方在跑之前的直接写入**不**进版本
    推进路径 · 裁定 31）⇒ 用一个**节点执行**来制造推进。

    ⚠️ **B12F1（T069）**：本用例断言「用户侧副作用的**同轮完成顺序**」⇒
    并发下该顺序**不再确定** ⇒ **拆分而不删** —— ① **串行模式**
    （``max_concurrency=1``）**保留原逐字顺序断言**（**一条不删**）·
    ② **并发模式**（缺省）断言**顺序无关但有力**的性质
    （**元素多重集相等** + **次数相等**）⇒ **MUST NOT** 写成「跑过了就行」的弱断言。
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
            "__start__": _ENTRY,
            "writer": NodeSpec(subscribes=("count",), run=writer),
            "reader": NodeSpec(subscribes=("count", "other"), run=reader),
        },
        edges={"__start__": ("writer", "reader"), "writer": ("reader",)},
    )
    state = SchedulerState()

    first = run_super_step(spec, state, max_concurrency=max_concurrency)
    if max_concurrency == 1:
        # ⚠️ **串行模式**：**原逐字**顺序断言（**一条不删**）
        assert calls == ["reader", "writer"]
    else:
        # ⚠️ **并发模式**：**顺序无关**但**有力**（元素多重集相等 + 次数相等）
        assert sorted(calls) == ["reader", "writer"]
        assert len(calls) == 2
    # ⚠️ ``executed`` 是**结果对象**的口径（**节点名序**）⇒ **两种模式都确定**
    assert first.executed == ("reader", "writer")

    # 第 2 轮：``__start__`` 的版本**未推进** ⇒ 只有 ``writer`` 的边触发源触发
    # ``reader``。
    second = run_super_step(spec, state, max_concurrency=max_concurrency)

    if max_concurrency == 1:
        # ⚠️ **串行模式**：**原逐字**顺序断言（**一条不删**）
        assert calls == ["reader", "writer", "reader"]
    else:
        # ⚠️ **并发模式**：**顺序无关**但**有力**（元素多重集相等 + 次数相等）
        assert sorted(calls) == ["reader", "reader", "writer"]
        assert len(calls) == 3
    assert second.executed == ("reader",)


# ── T032 · 值逐字相等仍触发下游（SC-003）───────────────────────────────


def test_writing_a_literally_equal_value_still_triggers_the_downstream_node() -> None:
    """**SC-003**：写入一个与当前值**逐字相等**的值 ⇒ 下游节点**仍被触发**。

    ⚠️ 触发判定 MUST 依据**版本号**，MUST NOT 依据「值是否变化」（FR-002）。
    ⚠️ **上游同款**：触发源**恒为边** ⇒ 触发依据 = **源节点的执行版本**
    ⇒ 下游节点由 ``writer → sink`` 的**边**触发，**与通道的值是否变化无关**。

    ⚠️ 第 1 轮里 ``writer`` 执行（并写入与当前值**逐字相等**的值）；第 2 轮里
    ``sink`` 被 ``writer`` 的**边触发源**触发 ⇒ 两次触发之间通道的**值完全没变**
    ⇒ 版本推进 ⇒ 仍被触发。
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
            "__start__": _ENTRY,
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "sink": NodeSpec(subscribes=("count",), run=sink),
        },
        edges={"__start__": ("writer",), "writer": ("sink",)},
    )
    state = SchedulerState()

    run_super_step(spec, state)
    assert calls == ["writer"]

    # ⚠️ 通道的值**完全没变**（仍是 5）⇒ 版本推进 ⇒ 下游**仍被触发**。
    run_super_step(spec, state)

    assert calls == ["writer", "sink"]
    assert channels["count"].get() == 5
    assert state.channel_versions["count"] == 1
    # 触发依据 = **源节点的执行版本**（不是通道的值）。
    assert state.node_versions["writer"] == 1
    assert state.versions_seen["sink"][("e", "writer")] == 1


# ── T033 · 版本推进的口径（SC-003 / SC-012）────────────────────────────


def test_the_channel_version_advances_only_on_a_successful_write() -> None:
    """**SC-003**：通道的写入版本**仅**在 ``update()`` 返回**真**时推进。

    ⚠️ 写一个**逐字相等**的值 ⇒ ``update()`` 仍返回**真** ⇒ 版本**推进**
    （FR-002）。

    ⚠️ 节点跑**两轮**（第 2 轮由**自环边**触发）⇒ 两次**逐字相等**的写入
    ⇒ 写入版本 == **2**。
    """
    channels = _channels()
    channels["count"].update([5])
    state = SchedulerState()

    def node(state: dict[str, Any]) -> dict[str, Any]:
        return {"count": 5}

    spec = GraphSpec(
        channels=channels,
        nodes={"__start__": _ENTRY, "node": NodeSpec(subscribes=("count",), run=node)},
        edges={"__start__": ("node",), "node": ("node",)},
    )

    run_super_step(spec, state)
    run_super_step(spec, state)

    assert state.channel_versions["count"] == 2


def test_clearing_a_routing_channel_does_not_advance_its_version() -> None:
    """**SC-012**：路由型通道被清空后其版本**未推进** ⇒ 节点**不**被再次触发。

    ⚠️ 「清空不是写入」（FR-014）⇒ 版本不动 ⇒ 下一轮**不**触发。

    ⚠️ **上游同款**：旧口径的「首次查看 ⇒ 版本 1」（通道触发源）**已删除**
    （触发源**恒为边**）⇒ 该通道的写入版本恒为**基值 0** ⇒ 清空**不**推进它。
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
        nodes={
            "__start__": _ENTRY,
            "node": NodeSpec(subscribes=("count", "route"), run=node),
        },
        edges={"__start__": ("node",)},
    )
    state = SchedulerState()

    run_super_step(spec, state)

    # 「清空不是写入」⇒ 版本**未推进**（仍为基值 0）⇒ 步末被清空。
    assert state.channel_versions.get("route", 0) == 0
    # ⚠️ 观测**本次运行**的通道实例（上游同款 · P2-b）⇒ 而非图规格里的**模板**
    assert state.channels["route"].is_available() is False

    # 第 2 轮：入口哨兵的版本**恒为 1** ⇒ 节点**不再**被触发。
    second = run_super_step(spec, state)

    assert calls == ["node"]
    assert second.executed == ()


class _SilentChannel(Channel):
    """一个**拒绝写入**的自定义通道（``update()`` 返回**假**）。

    ⚠️ B5F1 的通道契约允许第三方实现 ⇒ 「本轮是否写入过」的判定 MUST 以
    ``Channel.update()`` 的**返回值**为准（契约 §5.1 · FR-002 ⚠️）⇒ 本用例
    守住「返回**假** ⇒ 版本**不**推进」这条口径。
    """


    def from_checkpoint(self, checkpoint: Any) -> "Channel":
        """按检查点**新建**同种通道（**上游同款** · ``langgraph/channels/base.py:60-65``
        的 ``from_checkpoint`` 是**抽象方法** ⇒ 第三方自定义通道**必须**自己实现）。"""
        empty = type(self)(self._key, self._value_type)
        if checkpoint is not MISSING:
            empty._value = checkpoint
        return empty
    def __init__(self, key: str, value_type: Any) -> None:
        super().__init__(key, value_type)
        self.update_calls = 0

    def update(self, values: Any) -> bool:
        self.update_calls += 1
        return False

    def get(self) -> Any:
        """永远无值 ⇒ 抛**标准**的「无值」信号（**上游同款** · ``EmptyChannelError``
        · ``langgraph/channels/base.py:69-72``）⇒ 基类的 ``checkpoint()``
        （``base.py:49-58``）能把它转成「缺失」⇒ 克隆实例时**不会**误触。"""
        raise EmptyChannelError(self._key)

    def is_available(self) -> bool:
        """**永远无值**（**上游同款** · 上游的具体通道都**覆写** ``is_available``
        以避免走 ``get()`` 的默认实现 · ``langgraph/channels/base.py:75-85``）⇒
        步末的「未更新且**仍有值**」判定不会触发本通道的 ``get()``。"""
        return False

    def is_available(self) -> bool:
        return False


def test_a_channel_whose_update_returns_false_does_not_advance_its_version() -> None:
    """**SC-003**：``update()`` 返回**假** ⇒ 该通道的写入版本**不**推进。

    ⚠️ 「本轮写入了值」的判定 MUST 以 ``Channel.update()`` 的**返回值**为准
    （契约 §5.1 · FR-002 ⚠️）⇒ 返回**假** ⇒ 版本**不**推进。

    ⚠️ **上游同款**：触发源**恒为边** ⇒ 通道写入**永远不是**触发依据 ⇒ 订阅了
    该通道却**无入边**的 ``watcher`` **一次都不跑**（即便同轮里该通道**确实**被
    写成了值 —— ``log`` 通道）。
    """
    channels: dict[str, Channel] = {
        "count": LastValue("count", int),
        "log": LastValue("log", str),
        "silent": _SilentChannel("silent", int),
    }
    channels["count"].update([1])
    calls: list[str] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("node")
        return {"silent": 5, "log": "written"}

    def watcher(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("watcher")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "node": NodeSpec(subscribes=("count", "silent"), run=node),
            "watcher": NodeSpec(subscribes=("log",), run=watcher),
        },
        edges={"__start__": ("node",)},
    )
    state = SchedulerState()

    run_super_step(spec, state)
    assert calls == ["node"]

    run_super_step(spec, state)

    assert calls == ["node"]
    assert state.channel_versions.get("silent", 0) == 0
    # 「写通道 ⇒ 订阅者被触发」的现象出现次数 == **0**（**上游同款**）。
    assert state.channel_versions["log"] == 1
