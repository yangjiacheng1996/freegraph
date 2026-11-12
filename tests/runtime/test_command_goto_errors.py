# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**非法跳转目标 / 非法形态**的用例 —— 属 **B9F1**（tasks T022 / T023）。

⚠️ **触发模型**（上游对齐 · 2026-11-12）：触发源**恒为边** ⇒ 每张图 MUST 有
**入口边** ``{"__start__": (首节点,)}``（上游 ``add_edge(START, "a")`` 的同款写法）。

覆盖的判定：

* **SC-009** —— ``goto`` 指向**不在节点表**中的名字 ⇒ 内置 ``ValueError``
  （消息**点名该目标**）；``goto=""`` / ``goto="__start__"`` ⇒ ``ValueError``；
  ``goto=123`` / ``goto=("a", 1)`` ⇒ 内置 ``TypeError``；``update`` 非 ``dict``
  ⇒ ``TypeError``；「静默忽略 / warning 后继续」的现象 == **0** 次；
* **SC-005** —— ``goto=Command.PARENT`` ⇒ ``NotImplementedError``（**可区分**）。

⚠️ **上游对照**：上游对未知目标是 **warning + 忽略** ⇒ freegraph **刻意分叉**
（parity **P-07 / X-1**）。

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
)


def _channels() -> dict[str, Channel]:
    """构造通道状态：**归约型**（``messages``）+ **覆盖型**（``seed``）。

    ⚠️ ``seed`` 的**初值**只作**入参**（``subscribes`` 只决定「读哪些通道」·
    上游 ``langgraph/graph/state.py:1534``）⇒ **不再**是触发源。
    """
    return {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
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


def test_an_unknown_goto_target_fails_explicitly_and_names_the_target() -> None:
    """**SC-009**：``goto="no-such-node"`` ⇒ ``ValueError``（**点名目标**）。

    ⇒ **MUST NOT** 静默忽略（上游同款是 warning + 忽略 ⇒ freegraph **分叉**）。
    """
    with pytest.raises(ValueError) as excinfo:
        _run_returning(Command(goto="no-such-node"))

    assert "no-such-node" in str(excinfo.value)


def test_an_empty_goto_target_fails_explicitly() -> None:
    """**SC-009**：``goto=""`` ⇒ ``ValueError``（空串不是合法节点名）。"""
    with pytest.raises(ValueError):
        _run_returning(Command(goto=""))


def test_goto_start_fails_explicitly() -> None:
    """**SC-009**：``goto="__start__"`` ⇒ ``ValueError``（``START`` 不是合法目标）。

    ⚠️ **上游同款**：入口哨兵**只**作边的**源**（``"__start__" → 首节点``）⇒
    它**不是**合法的跳转目标（与上游 ``START`` 的语义一致）。
    """
    with pytest.raises(ValueError) as excinfo:
        _run_returning(Command(goto="__start__"))

    assert "__start__" in str(excinfo.value)


def test_a_non_string_goto_fails_with_a_type_error() -> None:
    """**SC-009**：``goto=123`` ⇒ 内置 ``TypeError``。

    ⇒ **MUST NOT** 把 ``123`` 当成字符序列拆开（L1 docstring 逐字点名）。
    """
    with pytest.raises(TypeError):
        _run_returning(Command(goto=123))


def test_a_goto_sequence_with_a_non_string_item_fails_with_a_type_error() -> None:
    """**SC-009**：``goto=("a", 1)`` ⇒ 内置 ``TypeError``。"""
    with pytest.raises(TypeError):
        _run_returning(Command(goto=("a", 1)))


def test_a_non_dict_command_update_fails_with_a_type_error() -> None:
    """**SC-009 / FR-010**：``Command(update=["a"])`` ⇒ 内置 ``TypeError``。"""
    with pytest.raises(TypeError):
        _run_returning(Command(update=["a"]))  # type: ignore[arg-type]


def test_an_illegal_node_return_type_fails_with_a_type_error() -> None:
    """**FR-001 / V-9**：节点返回**非法类型** ⇒ 内置 ``TypeError``。

    ⚠️ **2026-11-12 上游对齐 P3**：``None`` **已合法**（**无写入** · 上游
    ``langgraph/graph/state.py:1459-1460``）⇒ 非法样例里**去掉** ``None``。
    """
    for bad in (42, "text"):
        with pytest.raises(TypeError):
            _run_returning(bad)


def test_an_illegal_command_list_element_fails_with_a_type_error() -> None:
    """**FR-001 / V-10**：命令列表的元素类型非法 ⇒ 内置 ``TypeError``。"""
    with pytest.raises(TypeError):
        _run_returning([1, 2])


def test_the_unknown_target_failure_is_distinguishable_from_the_parent_failure() -> None:
    """**SC-005 / SC-009**：两条失败信号**类型不同** ⇒ 可**分别捕获**。

    ⇒ 「**写错了**」（``ValueError``）与「**合法但未实现**」
    （``NotImplementedError``）是**两种语义**（裁定 7）。
    """
    with pytest.raises(ValueError):
        _run_returning(Command(goto="no-such-node"))
    with pytest.raises(NotImplementedError):
        _run_returning(Command(goto=Command.PARENT))
