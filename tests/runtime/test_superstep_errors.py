# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**错误传播**与**``GraphInterrupt`` 合并**的用例 —— 属 **B12F1**（tasks **T027–T037** ·
**T038–T047**）。

覆盖的判定：

* **US2**（**A2** · SC-002 / SC-014 / SC-028 / SC-003 / SC-007 / SC-008）
  —— 首个异常**原样**抛出（类型 / 消息 / **对象 identity**）· **节点名序**决定
  「首个」· 其余失败以**附注**记录（三样齐全）· **取消语义**（机制级夹具）
  · **整轮原子**（出错轮一个都不合并 · 调度状态不落回）· 后续 super-step **不执行**；
* **US3**（SC-009 / SC-010 / SC-011 / SC-012 / SC-013）
  —— 多个中断**完整收集**并**合并抛出**（载荷 = **元组** · **节点名序**）
  · 中断轮**合并**其它节点的写入（**不是**「出错」）· 中断轮**不产出结果对象**
  · 真实异常**优先**于中断。

⚠️ **判定口径纪律**（契约 §6 / §11）：
* 「**首个异常**」由「**节点名序**最靠前」决定 ⇒ **可复现**（**比上游更严** · X-1）；
* **取消语义分两层** —— **端到端**只比「最后被启动了哪些节点」；
  **机制级**用**确定性夹具**断言「尚未启动的任务其 ``cancel()`` 返回 ``True``」；
* ⚠️ **``GraphInterrupt`` 的用户写法 MUST 是 1-元组**
  （``raise GraphInterrupt((Interrupt(...),))`` · **上游同款** · ``langgraph/types.py:967``）
  ⇒ 传**单个** ``Interrupt`` 会抛 ``TypeError``（L1 的 ``payload`` 是**序列**）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
import threading
import time
from concurrent.futures import Future
from typing import Any

import pytest

from freegraph.contracts.errors import GraphInterrupt
from freegraph.contracts.types import Interrupt
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
    """构造通道状态：**覆盖型**（``count``）+ **归约型**（``messages``）。"""
    return {
        "count": LastValue("count", int),
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
    }


#: **入口哨兵节点**（上游 ``START`` 同款 · ``langgraph/constants.py:30``）。
_ENTRY = NodeSpec(subscribes=(), run=lambda state: {})


def _spec(
    nodes: dict[str, NodeSpec], edges: dict[str, tuple[str, ...]]
) -> GraphSpec:
    """组装一张图规格（入口哨兵自动补上）。"""
    table = dict(nodes)
    table["__start__"] = _ENTRY
    return GraphSpec(channels=_channels(), nodes=table, edges=edges)


# ── US2 · 首个异常原样抛出（**A2** · SC-002）───────────────────────────────


def test_the_first_exception_is_raised_verbatim() -> None:
    """**SC-002**（**A2** · I-3）：异常**类型 / 消息 / 对象 identity** 逐字一致。

    ⇒ 被包装成别的异常类型的现象 == **0** 次；被静默吞掉的次数 == **0** 次。
    """
    raised: list[BaseException] = []

    def boom(state: dict[str, Any]) -> dict[str, Any]:
        error = ValueError("boom")
        raised.append(error)
        raise error

    spec = _spec({"bad": NodeSpec(subscribes=(), run=boom)}, {"__start__": ("bad",)})

    with pytest.raises(ValueError) as caught:
        run_super_step(spec, SchedulerState())

    assert type(caught.value) is ValueError
    assert str(caught.value) == "boom"
    assert caught.value is raised[0]


def test_the_first_exception_is_the_node_name_ordered_one() -> None:
    """**SC-002**（X-1）：抛出的那个由「**节点名序**最靠前」的失败节点决定。

    ⇒ **可复现** ⇒ 重复跑 **≥ 3** 次**恒定**（**不**依赖完成时刻的竞态）。
    """
    def make(error_type: type[Exception]) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            raise error_type("boom")

        return _fn

    def build() -> GraphSpec:
        # ⚠️ **声明顺序**与**名字顺序**相反（``z_fail`` < ``a_fail`` 的声明在前）
        return _spec(
            {
                "z_fail": NodeSpec(subscribes=(), run=make(ValueError)),
                "a_fail": NodeSpec(subscribes=(), run=make(KeyError)),
            },
            {"__start__": ("z_fail", "a_fail")},
        )

    for _ in range(3):
        # ⚠️ 「a_fail」在**节点名序**里**更靠前** ⇒ 抛出的 MUST 是它的 ``KeyError``
        with pytest.raises(KeyError):
            run_super_step(build(), SchedulerState())


def test_the_other_failures_are_recorded_as_notes() -> None:
    """**SC-014**（I-4）：其余并发失败**均以附注**记录 ⇒ 被完全丢弃的失败数 == **0**。

    ⚠️ 附注**固定格式**且 MUST 同时含**节点名** · **异常类型名** · **消息**三样。
    """
    started = threading.Event()

    def make(name: str, error_type: type[Exception], message: str) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            if name == "b_fail":
                # ⚠️ 让「b_fail」**先**启动 ⇒ 它**不会**被取消 ⇒ 「其余失败」确实存在
                started.set()
            else:
                started.wait(timeout=5)
            raise error_type(message)

        return _fn

    spec = _spec(
        {
            "a_fail": NodeSpec(subscribes=(), run=make("a_fail", ValueError, "boom-a")),
            "b_fail": NodeSpec(subscribes=(), run=make("b_fail", KeyError, "boom-b")),
        },
        {"__start__": ("a_fail", "b_fail")},
    )

    with pytest.raises(ValueError) as caught:
        run_super_step(spec, SchedulerState())

    notes = getattr(caught.value, "__notes__", [])
    assert len(notes) == 1, f"附注条数应为 1（其余失败只有 1 个），实得 {notes}"
    note = notes[0]
    assert "其它并发失败" in note
    assert "b_fail" in note, f"附注 MUST 含节点名：{note!r}"
    assert "KeyError" in note, f"附注 MUST 含异常类型名：{note!r}"
    assert "boom-b" in note, f"附注 MUST 含异常消息（逐字）：{note!r}"
    # 附注**不改变**异常的**类型 / 消息 / identity**
    assert type(caught.value) is ValueError
    assert str(caught.value) == "boom-a"


def test_the_cancel_semantics_cancels_the_queued_task() -> None:
    """**SC-028**（I-17 · **机制级**）：失败发生时，**尚未启动**的任务其
    ``cancel()`` 返回 **True**；**运行中**的任务**跑完并被等待**（未被中断）。

    ⚠️ **确定性夹具**：``cap=1`` + 四个节点 ⇒ 失败发生时**至少有一个**排队者
    （后面那个慢任务占着跑位）⇒ ``cancel()`` 的返回值**必然**含 ``True`` ⇒
    **不依赖竞态**（上游端到端 15/15 次排队者照跑 ⇒ 端到端 MUST NOT 断言「没跑」）。
    """
    cancel_results: list[bool] = []
    original_cancel = Future.cancel

    def _recording_cancel(self: Future[Any], *args: Any, **kwargs: Any) -> bool:
        outcome = original_cancel(self, *args, **kwargs)
        cancel_results.append(outcome)
        return outcome

    ran: list[str] = []
    lock = threading.Lock()

    def make(name: str, delay: float, fail: bool = False) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            time.sleep(delay)
            with lock:
                ran.append(name)
            if fail:
                raise ValueError("boom")
            return {}

        return _fn

    spec = _spec(
        {
            "a_slow": NodeSpec(subscribes=(), run=make("a_slow", 0.30)),
            "b_fail": NodeSpec(subscribes=(), run=make("b_fail", 0.0, fail=True)),
            "c_slow": NodeSpec(subscribes=(), run=make("c_slow", 0.30)),
            "d_queued": NodeSpec(subscribes=(), run=make("d_queued", 0.0)),
        },
        {"__start__": ("a_slow", "b_fail", "c_slow", "d_queued")},
    )

    Future.cancel = _recording_cancel  # type: ignore[method-assign]
    try:
        with pytest.raises(ValueError):
            run_super_step(spec, SchedulerState(), max_concurrency=1)
    finally:
        Future.cancel = original_cancel  # type: ignore[method-assign]

    assert cancel_results, "失败时 MUST 对未完成的 future 调 cancel()"
    assert True in cancel_results, "排队未启动者的 cancel() MUST 返回 True"
    assert "b_fail" in ran
    assert "a_slow" in ran, "运行中的任务 MUST 跑完并被等待"


def test_an_error_round_is_atomic_and_merges_nothing_at_all() -> None:
    """**SC-007**（I-10 · **X-3**）：出错轮里**全部**通道值 == **轮初**（逐字）；
    **写入版本不推进**；**跑成功**的节点的写入**也不生效**（**比上游更严**）。"""
    started = threading.Event()

    def bad(state: dict[str, Any]) -> dict[str, Any]:
        # ⚠️ 等「b_good」**真的跑起来** ⇒ 它**不会**被取消 ⇒ 「跑成功者的写入」确实存在
        started.wait(timeout=5)
        raise ValueError("boom")

    def good(state: dict[str, Any]) -> dict[str, Any]:
        started.set()
        return {"messages": ["written"], "count": 99}

    spec = _spec(
        {
            "a_bad": NodeSpec(subscribes=(), run=bad),
            "b_good": NodeSpec(subscribes=(), run=good),
        },
        {"__start__": ("a_bad", "b_good")},
    )
    state = SchedulerState()

    with pytest.raises(ValueError):
        run_super_step(spec, state)

    # ⚠️ **归约通道**的初值是**空列表**（不是「无值」）⇒ 与**轮初**逐字相等即可
    assert state.channels["messages"].get() == []
    assert state.channels["count"].is_available() is False
    assert state.channel_versions.get("messages", 0) == 0
    assert state.channel_versions.get("count", 0) == 0


def test_the_downstream_nodes_do_not_run_after_an_error_stop_the_graph() -> None:
    """**SC-003**（**A3** · I-5）：异常之后**后续 super-step 不执行** ⇒ 执行计数 == **0**。"""
    counts = {"bad": 0, "downstream": 0}
    lock = threading.Lock()

    def bad(state: dict[str, Any]) -> dict[str, Any]:
        with lock:
            counts["bad"] += 1
        raise ValueError("boom")

    def downstream(state: dict[str, Any]) -> dict[str, Any]:
        with lock:
            counts["downstream"] += 1
        return {}

    spec = _spec(
        {
            "bad": NodeSpec(subscribes=(), run=bad),
            "downstream": NodeSpec(subscribes=(), run=downstream),
        },
        {"__start__": ("bad",), "bad": ("downstream",)},
    )

    with pytest.raises(ValueError):
        run_super_steps(spec)

    assert counts["bad"] == 1
    assert counts["downstream"] == 0


def test_the_scheduler_state_is_not_written_back_on_an_error_no_ghost_trigger() -> None:
    """**SC-008**（I-11）：出错轮后**全部**节点的「执行版本」与「跳转目标」
    == **轮初**（⇒ 无**幽灵触发**）。"""
    def bad(state: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("boom")

    def good(state: dict[str, Any]) -> dict[str, Any]:
        return {}

    spec = _spec(
        {
            "a_bad": NodeSpec(subscribes=(), run=bad),
            "b_good": NodeSpec(subscribes=(), run=good),
        },
        {"__start__": ("a_bad", "b_good")},
    )
    state = SchedulerState()

    with pytest.raises(ValueError):
        run_super_step(spec, state)

    assert state.node_versions == {}
    assert state.dynamic_edges == {}


# ── US3 · 多个中断被完整收集（SC-009 / SC-010 / SC-011 / SC-012 / SC-013）──


def _interrupt_spec(count: int = 2) -> GraphSpec:
    """两个节点各抛一个 ``GraphInterrupt``（**1-元组**写法 · 上游同款）。"""

    def make(name: str) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            raise GraphInterrupt((Interrupt(value=f"approve-{name}", id=name),))

        return _fn

    nodes = {
        f"n{i}": NodeSpec(subscribes=(), run=make(f"n{i}")) for i in range(count)
    }
    return _spec(nodes, {"__start__": tuple(f"n{i}" for i in range(count))})


def test_the_interrupts_are_merged_into_one_exception() -> None:
    """**SC-009**（I-12）：两个节点同时中断 ⇒ 捕获到**一个** ``GraphInterrupt``；
    其**载荷是长度 == 2 的元组**；「只保留第一个」的现象 == **0** 次。"""
    spec = _interrupt_spec(2)

    with pytest.raises(GraphInterrupt) as caught:
        run_super_step(spec, SchedulerState())

    payload = caught.value.args[0]
    assert isinstance(payload, tuple)
    assert len(payload) == 2
    for item in payload:
        assert isinstance(item, Interrupt), f"元素 MUST 是 Interrupt 对象，实得 {type(item)!r}"
        assert hasattr(item, "value")
        assert hasattr(item, "id")


def test_the_interrupt_elements_are_collected_verbatim() -> None:
    """**SC-010**：每个元素的 ``.value`` / ``.id`` 与节点内传入的**逐字**相同。

    ⚠️ 内核**原样收集**（不生成 / 改写 / 校验）⇒ 元素**被包装**的次数 == **0**。
    """
    spec = _interrupt_spec(2)

    with pytest.raises(GraphInterrupt) as caught:
        run_super_step(spec, SchedulerState())

    payload = caught.value.args[0]
    assert sorted(item.value for item in payload) == ["approve-n0", "approve-n1"]
    assert sorted(item.id for item in payload) == ["n0", "n1"]


def test_a_payload_without_an_id_is_collected_verbatim() -> None:
    """**SC-010** 的**断言范围**补记：用户载荷**缺** ``.id`` ⇒ 内核**原样收集**
    （**不生成 · 不包装 · 不校验**）⇒ MUST **NOT** 报错、**MUST NOT** 中断流程。"""

    def _fn(state: dict[str, Any]) -> dict[str, Any]:
        raise GraphInterrupt((Interrupt(value="no-id"),))

    spec = _spec({"only": NodeSpec(subscribes=(), run=_fn)}, {"__start__": ("only",)})

    with pytest.raises(GraphInterrupt) as caught:
        run_super_step(spec, SchedulerState())

    payload = caught.value.args[0]
    assert len(payload) == 1
    assert payload[0].value == "no-id"


def test_the_interrupt_tuple_follows_the_node_name_order() -> None:
    """**SC-009**（X-7）：元组内元素的顺序 == **节点名序**；重复跑 **≥ 3** 次**逐项相同**。"""
    orders: list[tuple[str, ...]] = []

    for _ in range(3):
        spec = _interrupt_spec(3)
        with pytest.raises(GraphInterrupt) as caught:
            run_super_step(spec, SchedulerState())
        orders.append(tuple(item.id for item in caught.value.args[0]))

    assert orders[0] == ("n0", "n1", "n2")
    assert orders[1] == orders[0]
    assert orders[2] == orders[0]


def test_an_interrupt_merges_the_other_nodes_writes() -> None:
    """**SC-011**（I-13）：**中断轮**里被中断节点的**自身写入不生效**；
    同轮**其它**节点的写入**照常合并**（**中断不是「出错」**）。"""

    def asker(state: dict[str, Any]) -> dict[str, Any]:
        raise GraphInterrupt((Interrupt(value="approve", id="ask"),))

    def writer(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["written"]}

    spec = _spec(
        {
            "a_ask": NodeSpec(subscribes=(), run=asker),
            "b_write": NodeSpec(subscribes=(), run=writer),
        },
        {"__start__": ("a_ask", "b_write")},
    )
    state = SchedulerState()

    with pytest.raises(GraphInterrupt):
        run_super_step(spec, state)

    assert state.channels["messages"].get() == ["written"]


def test_an_error_round_merges_nothing_even_with_an_interrupt() -> None:
    """**SC-011** 的**对照**：**出错轮**（真异常）里同轮**成功**节点的写入
    **照常合并**的比率 MUST == **0%**（整轮原子）。"""

    started = threading.Event()

    def boom(state: dict[str, Any]) -> dict[str, Any]:
        started.wait(timeout=5)
        raise ValueError("boom")

    def writer(state: dict[str, Any]) -> dict[str, Any]:
        started.set()
        return {"messages": ["written"]}

    spec = _spec(
        {
            "a_boom": NodeSpec(subscribes=(), run=boom),
            "b_write": NodeSpec(subscribes=(), run=writer),
        },
        {"__start__": ("a_boom", "b_write")},
    )
    state = SchedulerState()

    with pytest.raises(ValueError):
        run_super_step(spec, state)

    assert state.channels["messages"].get() == []


def test_the_interrupt_round_commits_the_successful_nodes_only() -> None:
    """**SC-011**：**中断轮**的调度状态 —— 成功节点**照常落回**版本；
    被中断节点**不**落回（它**没完成** ⇒ 恢复时会被**重跑**）。"""

    def asker(state: dict[str, Any]) -> dict[str, Any]:
        raise GraphInterrupt((Interrupt(value="approve", id="ask"),))

    def writer(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["written"]}

    spec = _spec(
        {
            "a_ask": NodeSpec(subscribes=(), run=asker),
            "b_write": NodeSpec(subscribes=(), run=writer),
        },
        {"__start__": ("a_ask", "b_write")},
    )
    state = SchedulerState()

    with pytest.raises(GraphInterrupt):
        run_super_step(spec, state)

    assert state.node_versions.get("b_write") == 1
    assert "a_ask" not in state.node_versions


def test_the_interrupt_round_produces_no_result_object() -> None:
    """**SC-009**：**中断轮不产出结果对象** ⇒ 入口**不**返回 ``SuperStepResult``；
    而调用方从**自己持有的调度状态**读到的通道值**已是合并后**的。"""

    def asker(state: dict[str, Any]) -> dict[str, Any]:
        raise GraphInterrupt((Interrupt(value="approve", id="ask"),))

    def writer(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["written"]}

    spec = _spec(
        {
            "a_ask": NodeSpec(subscribes=(), run=asker),
            "b_write": NodeSpec(subscribes=(), run=writer),
        },
        {"__start__": ("a_ask", "b_write")},
    )
    state = SchedulerState()
    outcome: Any = None

    with pytest.raises(GraphInterrupt):
        outcome = run_super_step(spec, state)

    assert outcome is None, "中断轮 MUST NOT 产出结果对象"
    assert state.channels["messages"].get() == ["written"]


def test_the_real_exception_wins_over_the_interrupt() -> None:
    """**SC-013**（I-15）：真实异常与中断**同现** ⇒ 抛**真实异常**（原对象）；
    中断元组**随之丢弃**（**上游同款**）。"""

    def boom(state: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("boom")

    def asker(state: dict[str, Any]) -> dict[str, Any]:
        raise GraphInterrupt((Interrupt(value="approve", id="ask"),))

    spec = _spec(
        {
            "a_boom": NodeSpec(subscribes=(), run=boom),
            "b_ask": NodeSpec(subscribes=(), run=asker),
        },
        {"__start__": ("a_boom", "b_ask")},
    )

    with pytest.raises(ValueError) as caught:
        run_super_step(spec, SchedulerState())

    assert str(caught.value) == "boom"


def test_the_graph_pauses_after_an_interrupt() -> None:
    """**SC-012**（I-14）：中断轮之后**不进入下一轮** ⇒ 下游节点执行计数 == **0**；
    而被中断的节点**确实被启动过**（其节点函数确实执行了）。"""
    counts = {"ask": 0, "downstream": 0}
    lock = threading.Lock()

    def asker(state: dict[str, Any]) -> dict[str, Any]:
        with lock:
            counts["ask"] += 1
        raise GraphInterrupt((Interrupt(value="approve", id="ask"),))

    def downstream(state: dict[str, Any]) -> dict[str, Any]:
        with lock:
            counts["downstream"] += 1
        return {}

    spec = _spec(
        {
            "ask": NodeSpec(subscribes=(), run=asker),
            "downstream": NodeSpec(subscribes=(), run=downstream),
        },
        {"__start__": ("ask",), "ask": ("downstream",)},
    )

    with pytest.raises(GraphInterrupt):
        run_super_steps(spec)

    assert counts["ask"] == 1, "被中断的节点确实被启动过"
    assert counts["downstream"] == 0
