# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**命令列表**的用例 —— 属 **B9F1**（tasks T018 的**专属**用例）。

⚠️ **触发模型**（上游对齐 · 2026-11-12）：触发源**恒为边** ⇒ 每张图 MUST 有
**入口边** ``{"__start__": (首节点,)}``（上游 ``add_edge(START, "a")`` 的同款写法）。

覆盖的判定：

* **SC-021** —— 命令列表（**上游同款**）：① 写入按**列表顺序**合并 ·
  ② 每条命令的 ``goto`` **各自成边** · ③ 混入的 ``dict`` 按**所在位置**生效 ·
  ④ **空列表** = 无操作 · ⑤ 元素类型非法 ⇒ ``TypeError`` · ⑥ 与单条命令
  **行为分叉**的现象 == **0** 次。

⚠️ 与 ``test_command_merge_parity.py`` 的分工：后者验「三形态**共用同一条**
合并路径」的**等价性**；本文件验命令列表**自身**的**顺序 / 位置 / 空列表**
语义。

**手写图规格**驱动 ⇒ MUST **不经由** ``StateGraph`` / ``compile()`` /
``invoke()``（FR-020 · SC-016）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Any

import pytest

from freegraph.contracts import Command
from freegraph.runtime import (
    BinaryOperatorAggregate,
    Channel,
    GraphSpec,
    LastValue,
    NodeSpec,
    SchedulerState,
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


def _run_returning(result: Any) -> Any:
    """跑一个**只返回** ``result`` 的单节点图（靠**入口边**起跑）。"""
    channels = _channels()
    channels["seed"].update([1])
    spec = _graph(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("seed",), run=lambda state: result)},
        edges={_START: ("writer",)},
    )
    return run_super_step(spec, SchedulerState())


def test_the_command_list_writes_are_merged_in_the_list_order() -> None:
    """**SC-021 ①**：多条命令的写入按**列表顺序**归约（**逐元素相等**）。

    ⇒ 与上游 ``_get_updates`` 的 ``updates.extend(...)`` 顺序**逐字一致**。
    """
    result = _run_returning(
        [
            Command(update={"messages": ["a"]}),
            Command(update={"messages": ["b"]}),
            Command(update={"messages": ["c"]}),
        ]
    )

    assert result.state["messages"] == ["a", "b", "c"]


@pytest.mark.parametrize("max_concurrency", [1, None], ids=["serial", "concurrent"])
def test_the_command_list_gotos_become_separate_edges(max_concurrency: int | None) -> None:
    """**SC-021 ②**：列表里**每条**命令的 ``goto`` **各自成边**。

    ⇒ **全部**目标在下一轮被触发（与「单条命令 + 多目标 ``goto``」**同款**）。
    
    ⚠️ **B12F1（T069）**：本用例断言「用户侧副作用的**同轮完成顺序**」⇒
    并发下该顺序**不再确定** ⇒ **拆分而不删** —— ① **串行模式**
    （``max_concurrency=1``）**保留原逐字顺序断言**（**一条不删**）·
    ② **并发模式**（缺省）断言**顺序无关但有力**的性质
    （**元素多重集相等** + **次数相等**）⇒ **MUST NOT** 写成「跑过了就行」的弱断言。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> list[Command]:
        executed.append("writer")
        return [Command(goto="one"), Command(goto="two")]

    def one(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("one")
        return {}

    def two(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("two")
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "one": NodeSpec(subscribes=(), run=one),
            "two": NodeSpec(subscribes=(), run=two),
        },
        edges={_START: ("writer",)},
    )

    run_super_steps(spec, max_concurrency=max_concurrency)

    if max_concurrency == 1:
        # ⚠️ **串行模式**：**原逐字**顺序断言（**一条不删**）
        assert executed == ["writer", "one", "two"]
    else:
        # ⚠️ **并发模式**：**顺序无关**但**有力**（元素多重集相等 + 次数相等）
        assert sorted(executed) == ['one', 'two', 'writer']
        assert len(executed) == 3


def test_the_command_list_gotos_are_deduplicated_in_order() -> None:
    """**SC-021 ②**：重复的 ``goto`` 目标**去重**（保序）⇒ 不重复触发。"""
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> list[Command]:
        executed.append("writer")
        return [Command(goto="one"), Command(goto="one")]

    def one(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("one")
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "one": NodeSpec(subscribes=(), run=one),
        },
        edges={_START: ("writer",)},
    )

    run_super_steps(spec)

    assert executed == ["writer", "one"]


def test_a_goto_sequence_with_a_duplicate_target_is_deduplicated() -> None:
    """**SC-011 / I-5**：多目标 ``goto`` 里的**重复**目标**去重**（保序）。

    ⇒ 重复目标**只**成为**一条**边 ⇒ 该目标**只**被执行一次
    （契约 §3「保序去重」）。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("writer")
        return Command(goto=("one", "one"))

    def one(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("one")
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "one": NodeSpec(subscribes=(), run=one),
        },
        edges={_START: ("writer",)},
    )

    run_super_steps(spec)

    assert executed == ["writer", "one"]


def test_a_dict_element_in_the_command_list_applies_at_its_own_position() -> None:
    """**SC-021 ③**：混入的 ``dict`` 按其**所在位置**生效。

    ⇒ 与「单独返回该 dict」**逐项一致**。
    """
    listed = _run_returning(
        [Command(update={"messages": ["a"]}), {"messages": ["b"]}, Command(update={"messages": ["c"]})]
    )

    assert listed.state["messages"] == ["a", "b", "c"]


def test_an_empty_command_list_is_an_explicit_no_op() -> None:
    """**SC-021 ④**：**空列表** ⇒ **显式失败**（**上游同款** · 2026-11-12 上游对齐 P3）。

    ⚠️ 上游的判据是 ``isinstance(input,(list,tuple)) and input and any(...)``
    ⇒ **空列表落 ``else``** ⇒ 抛 ``InvalidUpdateError("Expected dict, got []")``
    （上游 ``langgraph/graph/state.py:1488-1492``）
    ⇒ freegraph 抛内置 ``TypeError``（**类型不同 · 语义等价**）。
    """
    with pytest.raises(TypeError):
        _run_returning([])


def test_an_illegal_command_list_element_fails_with_a_type_error() -> None:
    """**SC-021 ⑤**：元素类型非法 ⇒ 内置 ``TypeError``（V-10）。"""
    for bad in ([1], ["text"], [None]):
        with pytest.raises(TypeError):
            _run_returning(bad)


def test_the_command_list_and_a_single_command_do_not_diverge() -> None:
    """**SC-021 ⑥**：命令列表与单条命令**行为分叉**的现象 == **0** 次。

    ⇒ 同一组写入分别以两种形态给出 ⇒ 合并结果**逐项一致**。
    """
    single = _run_returning(Command(update={"messages": ["x"], "count": 3}))
    listed = _run_returning([Command(update={"messages": ["x"], "count": 3})])

    assert single.state["messages"] == listed.state["messages"]
    assert single.state["count"] == listed.state["count"]
    assert single.node_writes == listed.node_writes
    assert single.executed == listed.executed
