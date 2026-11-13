# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**US2 / US3** · 提交审批结果后图继续跑完 + 恢复时节点从头重跑。

**判据**：SC-002（恢复后跑到结束态）· SC-003（**从节点起点重跑**）·
SC-013（恢复后再挂起 ⇒ 可**再次**恢复）· SC-014（同节点多 ``interrupt()``
按**节点内顺序**匹配）· SC-015（跨节点多挂起：单值**失败** · 按 id 的映射
**成功**）· FR-013 末两行（**会话连续**）。

**契约权威**：``specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md``
§6（恢复）· §6.3（「从节点起点重跑」）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from typing import Any

import pytest

from freegraph.contracts.types import Command
from freegraph.graph import interrupt
from freegraph.runtime import GraphSpec, InterruptResult, NodeSpec, SuperStepResult, run_graph
from freegraph.runtime.channel import LastValue

from .test_interrupt_checkpoint import StubCheckpointer

#: 图的通道（**覆盖型** · 无归约器 ⇒ 覆盖）。
_CHANNELS: dict[str, LastValue] = {
    "messages": LastValue("messages", list),
    "count": LastValue("count", int),
}


def _spec(nodes: dict[str, NodeSpec], edges: dict[str, tuple[str, ...]]) -> GraphSpec:
    """组装一张图规格（**入口哨兵** ``__start__`` 作为边源）。"""
    return GraphSpec(channels=dict(_CHANNELS), nodes=nodes, edges=edges)


def _ask_node(log: list[str] | None = None, value: str = "approve?") -> NodeSpec:
    """一个调用 ``interrupt(value)`` 的节点（**记录**副作用）。"""

    def _run(state: dict[str, Any]) -> dict[str, Any]:
        if log is not None:
            log.append("enter")
        answer = interrupt(value)
        return {"messages": [f"answer={answer}"]}

    return NodeSpec(subscribes=(), run=_run)


def test_the_resume_completes_the_graph() -> None:
    """**SC-002** / **A1**：挂桩 ⇒ 中断 ⇒ ``Command(resume="yes")`` ⇒ ⇒ 二次
    执行结果**无** ``__interrupt__`` ⇒ ⇒ 状态含 resume 值 ⇒ ⇒ 节点内计数 == 2。

    ⇒ 「恢复」与「首次运行」**共用同一条执行路径**（**上游同款**）。
    """
    stub = StubCheckpointer()
    config = RunConfigFactory("t-resume")
    log: list[str] = []
    spec = _spec({"ask": _ask_node(log)}, {"__start__": ("ask",)})

    paused = run_graph(spec, checkpointer=stub, config=config)
    assert isinstance(paused, InterruptResult)

    finished = run_graph(spec, Command(resume="yes"), checkpointer=stub, config=config)

    assert isinstance(finished, SuperStepResult)
    assert "__interrupt__" not in finished.as_result_dict() if hasattr(
        finished, "as_result_dict"
    ) else "__interrupt__" not in finished.state
    assert finished.state["messages"] == ["answer=yes"]
    # ⚠️ 节点被**执行了两次**（首次挂起 + 恢复重跑）⇒ ⇒ 「从节点起点重跑」
    assert log.count("enter") == 2


def test_the_resume_reruns_from_start() -> None:
    """**SC-003** / **A2**：恢复时节点**前半段**的副作用**再次出现** ⇒ ⇒
    副作用序列 == ``['enter', 'enter', 'got yes']`` ⇒ ⇒ **不**是从中断点继续。

    ⚠️ 这是「**最容易实现错**」的语义（裁定 5 · **上游同款** · 实测 E-8）。
    """
    stub = StubCheckpointer()
    config = RunConfigFactory("t-rerun")
    log: list[str] = []
    spec = _spec({"ask": _ask_node(log)}, {"__start__": ("ask",)})

    run_graph(spec, checkpointer=stub, config=config)
    finished = run_graph(spec, Command(resume="yes"), checkpointer=stub, config=config)

    assert isinstance(finished, SuperStepResult)
    assert log == ["enter", "enter"]
    assert finished.state["messages"] == ["answer=yes"]


def test_the_multiple_interrupts_in_one_node() -> None:
    """**SC-014**：同一节点内**两个** ``interrupt()`` ⇒ 第 1 个恢复值落在第 1 个
    ``interrupt()`` · 第 2 个落在第 2 个（**按节点内顺序** · **上游同款**）。

    ⇒ 恢复值**不足** ⇒ **再次挂起**（**不**报错 · 裁定 7）。
    """
    stub = StubCheckpointer()
    config = RunConfigFactory("t-order")
    seen: list[str] = []

    def _run(state: dict[str, Any]) -> dict[str, Any]:
        seen.append(f"a={interrupt('first?')}")
        seen.append(f"b={interrupt('second?')}")
        return {"messages": ["done"]}

    spec = _spec(
        {"ask": NodeSpec(subscribes=(), run=_run)}, {"__start__": ("ask",)}
    )

    run_graph(spec, checkpointer=stub, config=config)
    run_graph(spec, Command(resume="X"), checkpointer=stub, config=config)
    finished = run_graph(spec, Command(resume="Y"), checkpointer=stub, config=config)

    assert isinstance(finished, SuperStepResult)
    # ⇒ 第 1 个恢复值被**复用**（**上游同款** · 实测 E-18）· 第 2 个落在第 2 个
    assert seen == ["a=X", "a=X", "b=Y"]


def test_the_resume_then_interrupt_again() -> None:
    """**SC-013**（补记 **F-1**）：恢复值**不足** ⇒ 节点在下一个
    ``interrupt()`` 处**再次挂起**（**不**报错）⇒ ⇒ 第二次挂起的 ``.id`` 与
    第一次**逐字相同**（**跨恢复稳定**）⇒ ⇒ 第三次提交恢复值后**跑完**。"""
    stub = StubCheckpointer()
    config = RunConfigFactory("t-again")

    def _run(state: dict[str, Any]) -> dict[str, Any]:
        interrupt("first?")
        interrupt("second?")
        return {"messages": ["done"]}

    spec = _spec(
        {"ask": NodeSpec(subscribes=(), run=_run)}, {"__start__": ("ask",)}
    )

    first = run_graph(spec, checkpointer=stub, config=config)
    assert isinstance(first, InterruptResult)
    first_id = first.interrupts[0].id

    second = run_graph(spec, Command(resume="X"), checkpointer=stub, config=config)
    assert isinstance(second, InterruptResult)
    # ⇒ 新的**载荷**（"second?"）· 但**同一个 id**（**跨恢复稳定** · F-1）
    assert second.interrupts[0].value == "second?"
    assert second.interrupts[0].id == first_id

    third = run_graph(spec, Command(resume="Y"), checkpointer=stub, config=config)
    assert isinstance(third, SuperStepResult)
    assert third.state["messages"] == ["done"]


def test_the_multiple_pending_interrupts() -> None:
    """**SC-015** 的两半（**T052** ①）：跨节点两个挂起中断 ⇒ 单值 ⇒
    ``ambiguous_resume``；按 id 的映射 ⇒ 指定的**已恢复** · 未指定的**仍挂起**。

    ⇒ ⚠️ **map 的「值」原样投递**（**标量即可** · **上游同款**）⇒ ⇒ 节点拿到的
    就是那个**标量**本身（**不是**「节点内全部中断值的列表」）。
    """
    stub = StubCheckpointer()
    config = RunConfigFactory("t-map")

    def _make(name: str) -> NodeSpec:
        def _run(state: dict[str, Any]) -> dict[str, Any]:
            answer = interrupt(f"approve-{name}")
            return {"messages": [f"{name}={answer}"]}

        return NodeSpec(subscribes=(), run=_run)

    spec = _spec(
        {"a": _make("a"), "b": _make("b")},
        {"__start__": ("a", "b")},
    )

    paused = run_graph(spec, checkpointer=stub, config=config)
    assert isinstance(paused, InterruptResult)
    by_value = {item.value: item for item in paused.interrupts}

    # ⚠️ **单值** + 多挂起 ⇒ ⇒ `ambiguous_resume`（**上游同款** · 实测 E-12）
    from freegraph.runtime.errors import InterruptError

    with pytest.raises(InterruptError) as caught:
        run_graph(spec, Command(resume="A"), checkpointer=stub, config=config)
    assert caught.value.reason == "ambiguous_resume"

    # ⇒ **按 id 的映射** ⇒ 指定的**已恢复** · 未指定的**仍挂起**
    target = by_value["approve-b"]
    resumed = run_graph(
        spec,
        Command(resume={target.id: "B"}),
        checkpointer=stub,
        config=config,
    )
    assert isinstance(resumed, InterruptResult)
    # ⇒ 未指定的**仍挂起** ⇒ ⇒ 结果里还有那一条中断
    remaining = [item.value for item in resumed.interrupts]
    assert remaining == ["approve-a"]


def test_the_map_value_is_delivered_verbatim() -> None:
    """**SC-015** 的兼容半边（**T052** ① · **补记 F-2** 之外的第三段）：同一
    用例另以 ``{id: [值]}``（**列表**形态）再跑一次 ⇒ ⇒ 节点拿到的**就是那个
    列表** ⇒ ⇒ **两种形态都合法**（**不**强制列表）。"""
    stub = StubCheckpointer()
    config = RunConfigFactory("t-map-list")
    seen: list[Any] = []

    def _run(state: dict[str, Any]) -> dict[str, Any]:
        seen.append(interrupt("approve?"))
        return {"messages": ["done"]}

    spec = _spec({"ask": NodeSpec(subscribes=(), run=_run)}, {"__start__": ("ask",)})

    paused = run_graph(spec, checkpointer=stub, config=config)
    assert isinstance(paused, InterruptResult)
    target = paused.interrupts[0]

    run_graph(
        spec,
        Command(resume={target.id: ["V"]}),
        checkpointer=stub,
        config=config,
    )
    assert seen == [["V"]]


def test_the_resume_and_the_update_take_separate_channels() -> None:
    """**FR-013 ⑧**（补记 **F-2** · **上游同款**）：``Command(resume=…)`` 与
    ``Command(update=…)`` **并存** ⇒ ⇒ 两者**各走各的通道**（``update`` 落在
    通道上 · ``resume`` 被节点拿到）⇒ ⇒ **互不排斥**。"""
    stub = StubCheckpointer()
    config = RunConfigFactory("t-both")
    seen: list[Any] = []

    def _run(state: dict[str, Any]) -> dict[str, Any]:
        seen.append(interrupt("approve?"))
        return {"messages": ["done"]}

    spec = _spec({"ask": NodeSpec(subscribes=(), run=_run)}, {"__start__": ("ask",)})

    run_graph(spec, checkpointer=stub, config=config)
    finished = run_graph(
        spec,
        Command(resume="yes", update={"count": 42}),
        checkpointer=stub,
        config=config,
    )

    assert isinstance(finished, SuperStepResult)
    assert seen == ["yes"]
    assert finished.state["count"] == 42


def test_the_session_continues_on_the_same_thread() -> None:
    """**FR-013** 末两行（补记 **F-4** / **F-5** · **上游同款** · 实测 E-26）：

    ① **状态字典**输入 ⇒ 先读 ``.snapshot.values`` · 再把 ``input`` **叠加**
    上去（既有状态**不丢**）⇒ ⇒ **不**消费 ``__resume__`` ⇒ ⇒ **不**触发恢复
    ⇒ ⇒ **续跑**（MUST 读 ``.scheduler`` 重建调度状态）⇒ ⇒ 写通道 ⇒ 通道版本
    推进 ⇒ **订阅节点重新触发**（被触及的节点**重跑**）⇒ ⇒ ``.id`` **可变**；

    ② ``input = None`` ⇒ ⇒ **只有被中断的节点**重跑（其它节点**不**重跑）
    ⇒ ⇒ 且 ``.id`` 与先前交给调用方的那个**逐字相同**。
    """
    stub = StubCheckpointer()
    config = RunConfigFactory("t-session")
    log: list[str] = []

    def _pre(state: dict[str, Any]) -> dict[str, Any]:
        log.append("pre")
        return {"count": 99}

    def _ask(state: dict[str, Any]) -> dict[str, Any]:
        log.append("ask")
        answer = interrupt("approve?")
        return {"messages": [f"answer={answer}"]}

    spec = _spec(
        {"ask": NodeSpec(subscribes=(), run=_ask), "pre": NodeSpec(subscribes=(), run=_pre)},
        {"__start__": ("pre",), "pre": ("ask",)},
    )

    paused = run_graph(spec, checkpointer=stub, config=config)
    assert isinstance(paused, InterruptResult)
    first_id = paused.interrupts[0].id

    # ── ① 状态字典输入 ⇒ 会话连续（**写通道** ⇒ 订阅节点重新触发）──
    log.clear()
    continued = run_graph(
        spec, {"messages": ["extra"], "count": 7}, checkpointer=stub, config=config
    )
    assert isinstance(continued, InterruptResult)
    # ⇒ 「pre」被**重新触发**（入口边重跑）⇒ ⇒ 「ask」**级联**重跑
    assert log == ["pre", "ask"]
    # ⇒ ``.id`` **可变**（新一轮的检查点 ⇒ 新的任务路径 ⇒ 新命名空间）
    assert continued.interrupts[0].id != first_id

    # ── ② input = None ⇒ 只有被中断的节点重跑 ⇒ .id 逐字不变 ──
    log.clear()
    resumed = run_graph(spec, None, checkpointer=stub, config=config)
    assert isinstance(resumed, InterruptResult)
    assert log == ["ask"]
    # ⇒ ``.id`` 与**先前交给调用方的那个**（上一轮挂起时交出去的那个）
    # **逐字相同**（**跨恢复稳定** · 补记 **F-1** · **上游同款** · 实测 E-26 ①）
    assert resumed.interrupts[0].id == continued.interrupts[0].id


def RunConfigFactory(thread_id: str) -> Any:
    """造一个带 ``thread_id`` 的运行配置（**会话标识**）。"""
    from freegraph.contracts.types import RunConfig

    return RunConfig(thread_id=thread_id)
