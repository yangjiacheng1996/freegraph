# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**跳转语义**（叠加 / 生命周期 / 触发门槛 / 入参）的用例 —— 属 **B9F1**
（tasks T024 / T025）。

⚠️ **触发模型**（上游对齐 · 2026-11-12）：触发源**恒为边**（上游
``branch:to:<node>``）⇒ ``subscribes`` 只决定「读哪些通道」⇒ 每张图 MUST 有
**入口边** ``{"__start__": (首节点,)}``（上游 ``add_edge(START, "a")`` 的同款写法）。

覆盖的判定：

* **SC-007** —— 静态边目标与 ``goto`` 目标**都**在下一轮被触发（**叠加**）；
  同一对 (源, 目标) 在一轮内被触发**两次**的次数 == **0**；
* **SC-008** —— ``END`` **不跳转、不终止**（静态边目标仍被执行 + 更新生效）；
* **SC-010** —— 源节点再次执行且**不**返回 ``goto`` ⇒ 旧目标**不再**被触发
  （「残留触发 / 幽灵触发」的现象 == **0**）；
* **SC-011** —— **多目标** ``goto`` ⇒ 全部目标在下一轮被执行；``goto=()`` ⇒ 无跳转；
* **SC-023** —— ``goto`` 目标**无「有值」门槛**；其入参 == **正常稀疏读**；
  目标**读得到**源节点本次 ``update`` 的内容。

**手写图规格**驱动 ⇒ MUST **不经由** ``StateGraph`` / ``compile()`` /
``invoke()``（FR-020 · SC-016）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import pytest

import operator
from typing import Any

from freegraph.contracts import Command
from freegraph.runtime import (
    BinaryOperatorAggregate,
    Channel,
    GraphSpec,
    LastValue,
    NodeSpec,
    SchedulerState,
    read_channels,
    run_super_step,
    run_super_steps,
)


def _channels() -> dict[str, Channel]:
    """构造通道状态：**归约型**（``messages``）+ **覆盖型**（``count`` / ``seed``）。

    ⚠️ ``seed`` 的**初值**只作**入参**（``subscribes`` 只决定「读哪些通道」·
    上游 ``langgraph/graph/state.py:1534``）⇒ **不再**是触发源。
    """
    return {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "count": LastValue("count", int),
        "seed": LastValue("seed", int),
    }


#: **入口哨兵**（上游 ``START`` 的值 · ``langgraph/constants.py:30``）——
#: 触发源**恒为边**（上游 ``branch:to:<node>`` · ``langgraph/graph/state.py:1531``）
#: ⇒ 每张图 MUST 有**入口边** ``{"__start__": (首节点,)}``（上游
#: ``add_edge(START, "a")`` 的同款写法 · ``langgraph/graph/state.py:321``）。
_START = "__start__"


def _never(state: dict[str, Any]) -> dict[str, Any]:
    """**入口哨兵**的节点函数 —— 恒**不被调用**（哨兵无入边 ⇒ 永不被触发）。"""
    raise AssertionError("入口哨兵 __start__ 恒不被执行")


#: **入口哨兵节点**（上游 ``START`` **伪节点**）—— 恒**不被执行**。
_SENTINEL = NodeSpec(subscribes=(), run=_never)


def _graph(
    channels: dict[str, Channel],
    nodes: dict[str, NodeSpec],
    edges: dict[str, tuple[str, ...]],
) -> GraphSpec:
    """组装图规格 —— **注入**入口哨兵节点（``edges`` MUST 已含**入口边**）。

    ⚠️ 边的**源** MUST 在节点表里（V-2）⇒ 入口边的**源**（``__start__``）由
    **哨兵节点**承载（上游的 ``START`` 亦是图里的**伪节点**）。
    """
    return GraphSpec(
        channels=channels,
        nodes={_START: _SENTINEL, **nodes},
        edges=edges,
    )


@pytest.mark.parametrize("max_concurrency", [1, None], ids=["serial", "concurrent"])
def test_the_goto_target_and_the_static_edge_target_are_both_triggered(max_concurrency: int | None) -> None:
    """**SC-007**：静态边目标与 ``goto`` 目标**都**在下一轮被触发（**叠加**）。

    ⇒ 「``goto`` 取消静态边」或「静态边取消 ``goto``」的现象 == **0** 次
    （裁定 3 · 发起者的概念锚点：「两者同类 ⇒ 叠加自洽」）。
    
    ⚠️ **B12F1（T069）**：本用例断言「用户侧副作用的**同轮完成顺序**」⇒
    并发下该顺序**不再确定** ⇒ **拆分而不删** —— ① **串行模式**
    （``max_concurrency=1``）**保留原逐字顺序断言**（**一条不删**）·
    ② **并发模式**（缺省）断言**顺序无关但有力**的性质
    （**元素多重集相等** + **次数相等**）⇒ **MUST NOT** 写成「跑过了就行」的弱断言。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("x")
        return Command(goto="z")

    def y(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("y")
        return {}

    def z(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("z")
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "y": NodeSpec(subscribes=(), run=y),
            "z": NodeSpec(subscribes=(), run=z),
        },
        edges={_START: ("x",), "x": ("y",)},
    )

    run_super_steps(spec, max_concurrency=max_concurrency)

    if max_concurrency == 1:
        # ⚠️ **串行模式**：**原逐字**顺序断言（**一条不删**）
        assert executed == ["x", "y", "z"]
    else:
        # ⚠️ **并发模式**：**顺序无关**但**有力**（元素多重集相等 + 次数相等）
        assert sorted(executed) == ['x', 'y', 'z']
        assert len(executed) == 3


def test_the_same_source_target_pair_is_triggered_at_most_once_per_round() -> None:
    """**SC-007**：同一对 (源, 目标) 在一轮内被触发**两次**的次数 == **0**。

    ⇒ 静态边与动态边指向**同一**目标时，仍**只执行一次**。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("x")
        return Command(goto="y")

    def y(state: dict[str[str, Any]]) -> dict[str, Any]:
        executed.append("y")
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "y": NodeSpec(subscribes=(), run=y),
        },
        edges={_START: ("x",), "x": ("y",)},
    )

    run_super_steps(spec)

    assert executed == ["x", "y"]


def test_the_goto_target_is_not_triggered_again_after_the_source_reruns_without_a_goto() -> None:
    """**SC-010**：源节点再次执行且**不**返回 ``goto`` ⇒ 旧目标**不再**被触发。

    ⇒ 「残留触发（幽灵触发）」的现象 == **0** 次（裁定 2 · FR-009）。

    ⚠️ **上游同款**（上游对齐 · 2026-11-12）：触发源**恒为边** ⇒ 源节点的
    **再次执行** MUST 由**显式边**驱动（本例：静态边 ``z → x``）⇒ 旧目标被
    清空的证据 = ``z`` 在 ``x`` 的**第二次**执行之后**不再**被触发 ⇒ 执行序列
    里 ``z`` **只出现一次**（若动态边**未**被整体替换 ⇒ ``z`` 会**再**被执行）。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []
    calls = {"count": 0}

    def writer(state: dict[str, Any]) -> Any:
        calls["count"] += 1
        executed.append(f"x#{calls['count']}")
        if calls["count"] == 1:
            return Command(goto="z", update={"count": 2})
        return {}

    def z(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("z")
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed", "count"), run=writer),
            "z": NodeSpec(subscribes=("count",), run=z),
        },
        edges={_START: ("x",), "z": ("x",)},
    )

    run_super_steps(spec)

    assert executed == ["x#1", "z", "x#2"]


def test_the_goto_target_runs_even_when_its_subscribed_channels_have_no_value() -> None:
    """**SC-023**：``goto`` 目标订阅的通道**都没值** ⇒ 目标**照跑**（入参为空）。

    ⇒ 「目标因为入参为空而**没跑**」的现象 == **0** 次（裁定 17 · 上游实测同款）。
    """
    channels = _channels()
    channels["seed"].update([1])
    captured: list[dict[str, Any]] = []

    def writer(state: dict[str, Any]) -> Command:
        return Command(goto="z")

    def z(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(state)
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=("count",), run=z),
        },
        edges={_START: ("x",)},
    )

    run_super_steps(spec)

    assert captured == [{}]


def test_the_goto_target_input_equals_the_sparse_read_of_the_sub_mapping() -> None:
    """**SC-023**：目标的入参 == ``read_channels(子映射)`` 的结果（**逐字相等**）。

    ⚠️ 子映射 MUST 按「**通道映射的顺序**」构造（裁定 26）⇒ 入参的 key 顺序
    与**整张状态表**的 key 顺序**天然一致**。
    """
    channels = _channels()
    channels["seed"].update([1])
    channels["count"].update([7])
    captured: list[dict[str, Any]] = []

    def writer(state: dict[str, Any]) -> Command:
        return Command(goto="z")

    def z(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(state)
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=("count", "messages"), run=z),
        },
        edges={_START: ("x",)},
    )

    run_super_steps(spec)

    sub_mapping = {
        key: channel for key, channel in channels.items() if key in ("count", "messages")
    }
    expected = read_channels(sub_mapping)
    assert captured[0] == expected
    assert list(captured[0]) == list(expected)


def test_the_goto_target_reads_the_source_update() -> None:
    """**SC-023**：源节点 ``goto`` + ``update`` ⇒ 目标**读得到**这次更新。

    ⇒ 目标读的是**上一轮合并后**的状态（裁定 17 · 上游实测同款）。
    """
    channels = _channels()
    channels["seed"].update([1])
    captured: list[dict[str, Any]] = []

    def writer(state: dict[str, Any]) -> Command:
        return Command(goto="z", update={"count": 5})

    def z(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(state)
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=("count",), run=z),
        },
        edges={_START: ("x",)},
    )

    run_super_steps(spec)

    assert captured[0]["count"] == 5


@pytest.mark.parametrize("max_concurrency", [1, None], ids=["serial", "concurrent"])
def test_a_multi_target_goto_triggers_every_target(max_concurrency: int | None) -> None:
    """**SC-011**：``goto=("one", "two")`` ⇒ **全部**目标在下一轮被执行。

    ⇒ 与「单条命令 + 多目标 ``goto``」**同款**（裁定 9 · 上游实测同款）。
    
    ⚠️ **B12F1（T069）**：本用例断言「用户侧副作用的**同轮完成顺序**」⇒
    并发下该顺序**不再确定** ⇒ **拆分而不删** —— ① **串行模式**
    （``max_concurrency=1``）**保留原逐字顺序断言**（**一条不删**）·
    ② **并发模式**（缺省）断言**顺序无关但有力**的性质
    （**元素多重集相等** + **次数相等**）⇒ **MUST NOT** 写成「跑过了就行」的弱断言。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("x")
        return Command(goto=("one", "two"))

    def one(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("one")
        return {}

    def two(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("two")
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "one": NodeSpec(subscribes=(), run=one),
            "two": NodeSpec(subscribes=(), run=two),
        },
        edges={_START: ("x",)},
    )

    run_super_steps(spec, max_concurrency=max_concurrency)

    if max_concurrency == 1:
        # ⚠️ **串行模式**：**原逐字**顺序断言（**一条不删**）
        assert executed == ["x", "one", "two"]
    else:
        # ⚠️ **并发模式**：**顺序无关**但**有力**（元素多重集相等 + 次数相等）
        assert sorted(executed) == ['one', 'two', 'x']
        assert len(executed) == 3


def test_an_empty_goto_sequence_produces_no_jump() -> None:
    """**SC-011**：``goto=()`` ⇒ **不产生跳转**（该位不产生动作）。"""
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("x")
        return Command(goto=())

    def z(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("z")
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=(), run=z),
        },
        edges={_START: ("x",)},
    )

    run_super_steps(spec)

    assert executed == ["x"]


def test_goto_end_does_not_terminate_the_graph_and_the_update_still_applies() -> None:
    """**SC-008**：``goto=END`` ⇒ **不跳转、不终止**（静态边目标仍被执行）。

    ⇒ 终止是「**收敛**」的结果（裁定 5 · 上游实测同款）。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("x")
        return Command(goto="__end__", update={"messages": ["via-command"]})

    def y(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("y")
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "y": NodeSpec(subscribes=(), run=y),
        },
        edges={_START: ("x",), "x": ("y",)},
    )

    result = run_super_steps(spec)

    assert executed == ["x", "y"]
    assert result.state["messages"] == ["via-command"]


def test_the_goto_target_is_not_executed_in_the_same_round() -> None:
    """**SC-001**：``goto`` 目标在**同一轮**内被执行的现象 == **0** 次。"""
    channels = _channels()
    channels["seed"].update([1])
    state = SchedulerState()

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=lambda state: Command(goto="z")),
            "z": NodeSpec(subscribes=(), run=lambda state: {}),
        },
        edges={_START: ("x",)},
    )

    first = run_super_step(spec, state)

    assert first.executed == ("x",)
