# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**空操作 / ``resume`` 只被接受**的用例 —— 属 **B9F1**（tasks T026 / T027）。

覆盖的判定：

* **SC-006** —— ``Command(update={})`` / ``Command(goto=())`` /
  ``Command(goto=(), update={})`` / **空列表** ⇒ **零写入 + 零跳转**
  （且节点**仍计入执行记录**）；「因空命令而报错」的现象 == **0** 次；
* **SC-012** —— ``Command(resume="x")`` ⇒ **被接受**（不抛错）+ 产生写入
  **0** 次 + 产生跳转 **0** 次。

⚠️ **L1 契约层**逐字：「某位**显式给了但内容为空**（``update={}`` / ``goto=()``）
亦合法，语义为「该位不产生动作」⇒ 运行期 MUST 照此执行 ⇒ MUST NOT 造成
「契约层说合法、运行期抛错」的**分层分叉**（裁定 10）。

**手写图规格**驱动 ⇒ MUST **不经由** ``StateGraph`` / ``compile()`` /
``invoke()``（FR-020 · SC-016）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

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
    run_super_step,
    run_super_steps,
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


def test_an_empty_update_slot_produces_no_write() -> None:
    """**SC-006**：``Command(update={})`` ⇒ **无任何新增写入**。"""
    result = _run_returning(Command(update={}))

    assert result.state["messages"] == []
    assert result.node_writes == {"writer": {}}


def test_an_empty_goto_slot_produces_no_jump() -> None:
    """**SC-006**：``Command(goto=())`` ⇒ **无跳转**（该位不产生动作）。"""
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("writer")
        return Command(goto=())

    def z(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("z")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=(), run=z),
        },
        edges={},
    )

    run_super_steps(spec)

    assert executed == ["writer"]


def test_both_slots_empty_produces_no_write_and_no_jump() -> None:
    """**SC-006**：``Command(goto=(), update={})`` ⇒ 零写入 + 零跳转。"""
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("writer")
        return Command(goto=(), update={})

    def z(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("z")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=(), run=z),
        },
        edges={},
    )

    result = run_super_steps(spec)

    assert executed == ["writer"]
    assert result.state["messages"] == []
    assert result.node_writes == {"x": {}}


def test_an_empty_command_list_is_a_no_op_and_the_node_still_counts_as_executed() -> None:
    """**SC-006 / SC-021 ④**：**空列表** ⇒ 零写入 + 零跳转 + 节点仍计入执行记录。"""
    result = _run_returning([])

    assert result.executed == ("writer",)
    assert result.state["messages"] == []
    assert result.node_writes == {"writer": {}}


def test_the_execution_version_still_advances_for_a_no_op_command() -> None:
    """**SC-006**：空命令的节点**仍计入执行记录**、其**执行版本**照常 +1。

    ⇒ 空命令**不**是「节点没跑」⇒ 边触发源的版本口径**一致**。
    """
    channels = _channels()
    channels["seed"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(goto=(), update={})
            )
        },
        edges={},
    )

    state = SchedulerState()
    run_super_step(spec, state)

    assert state.node_versions["writer"] == 1


def test_the_resume_slot_is_accepted_and_produces_no_effect() -> None:
    """**SC-012**：``Command(resume="x")`` ⇒ **被接受**（不抛错）+ 零效果。

    ⇒ 写入 **0** 次 · 跳转 **0** 次（FR-011 · 恢复语义归 **B10F1**）。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("writer")
        return Command(resume="x")

    def z(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("z")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=(), run=z),
        },
        edges={},
    )

    result = run_super_steps(spec)

    assert executed == ["writer"]
    assert result.state["messages"] == []
    assert result.node_writes == {"x": {}}


def test_the_resume_slot_does_not_change_the_flow() -> None:
    """**SC-012**：``resume`` **不改变流程**（静态边照常推进）。"""
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("writer")
        return Command(resume="x")

    def y(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("y")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "y": NodeSpec(subscribes=(), run=y),
        },
        edges={"x": ("y",)},
    )

    run_super_steps(spec)

    assert executed == ["writer", "y"]
