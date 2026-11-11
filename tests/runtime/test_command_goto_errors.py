# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**非法跳转目标 / 非法形态**的用例 —— 属 **B9F1**（tasks T022 / T023）。

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
    """构造通道状态：**归约型**（``messages``）+ **覆盖型**（``seed``）。"""
    return {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "seed": LastValue("seed", int),
    }


def _run_returning(result: Any) -> Any:
    """跑一个**只返回** ``result`` 的单节点图。"""
    channels = _channels()
    channels["seed"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("seed",), run=lambda state: result)},
        edges={},
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
    """**SC-009**：``goto="__start__"`` ⇒ ``ValueError``（``START`` 不是合法目标）。"""
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
    """**FR-001 / V-9**：节点返回 ``None`` / 其它类型 ⇒ 内置 ``TypeError``。"""
    for bad in (None, 42, "text"):
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
