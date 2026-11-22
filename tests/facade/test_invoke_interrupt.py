# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B7F3 · US5 —— **挂起与恢复**（``__interrupt__`` 键 / 静态挂起 / 恢复取值）。

**共享夹具**：``tests/facade/_invoke_support.py``。

**判据**：spec FR-014 / FR-015 / FR-019 · SC-010 · 契约 §6 的 **I-04 / I-05**。
"""

from __future__ import annotations

from typing import Any

import pytest

from freegraph.contracts.types import Command, RunConfig
from freegraph.runtime.errors import InterruptError
from freegraph.graph import END, START, StateGraph, interrupt

from ._invoke_support import State, StubCheckpointer


def _interrupting_graph(checkpointer: Any = None) -> StateGraph:
    """一个在节点内请求人工审批的图。"""
    seen: list[Any] = []

    def _asker(state: dict[str, Any]) -> dict[str, Any]:
        answer = interrupt("approve?")
        seen.append(answer)
        return {"messages": [f"answer={answer}"]}

    builder = StateGraph(State)
    builder.add_node("ask", _asker)
    builder.add_edge(START, "ask")
    builder.add_edge("ask", END)
    builder._asker_seen = seen  # type: ignore[attr-defined]
    if checkpointer is not None:
        builder._checkpointer = checkpointer  # type: ignore[attr-defined]
    return builder


class TestSuspension:
    def test_suspended_result_carries_the_interrupt_key(self) -> None:
        """挂起时 MUST 返回含 ``"__interrupt__"`` 的结果（**不是**抛控制流异常）。"""
        builder = _interrupting_graph()
        out = builder.compile().invoke({"messages": []})
        assert "__interrupt__" in out

    def test_interrupt_payload_exposes_value_and_id(self) -> None:
        """中断载荷 MUST 带 ``.value`` 与 ``.id``（C17）。"""
        builder = _interrupting_graph()
        out = builder.compile().invoke({"messages": []})
        payload = out["__interrupt__"]
        first = payload[0]
        assert first.value == "approve?"
        assert first.id

    def test_suspended_key_set_is_schema_keys_plus_interrupt(self) -> None:
        """挂起结果的键集 MUST == **schema 全集 +** ``"__interrupt__"``（契约 I-05）。"""
        builder = _interrupting_graph()
        out = builder.compile().invoke({"messages": []})
        assert list(out) == ["messages", "llm_calls", "__interrupt__"]

    def test_non_suspended_run_has_no_interrupt_key(self) -> None:
        """**未挂起**的运行 MUST **不含** ``"__interrupt__"`` 键（出现次数 == 0）。"""
        builder = StateGraph(State)
        builder.add_node("a", lambda state: {"messages": ["a"]})
        builder.add_edge(START, "a")
        builder.add_edge("a", END)
        out = builder.compile().invoke({"messages": []})
        assert "__interrupt__" not in out

    def test_static_suspension_uses_the_same_conversion_path(self) -> None:
        """**静态挂起** MUST 走**同一条**转成路径 ⇒ ⇒ 值 = **空元组** ``()``（FR-014）。"""
        builder = StateGraph(State)
        builder.add_node("a", lambda state: {"messages": ["a"]})
        builder.add_edge(START, "a")
        builder.add_edge("a", END)
        out = builder.compile(interrupt_before=["a"]).invoke({"messages": []})
        assert "__interrupt__" in out
        assert out["__interrupt__"] == ()


class TestResume:
    def test_resume_re_runs_the_interrupted_node(self) -> None:
        """恢复时**被中断的节点 MUST 从头重跑**并拿到恢复值（FR-015 · SC-010）。

        ⚠️ **载体** = 测试侧的**自足桩 checkpointer**（tasks **T002** 交付）⇒ ⇒
        ``src/freegraph/**`` 内**零** saver 实现（``MemorySaver`` 归 **B14F1**）。
        """
        seen: list[Any] = []
        stub = StubCheckpointer()

        def _asker(state: dict[str, Any]) -> dict[str, Any]:
            answer = interrupt("approve?")
            seen.append(answer)
            return {"messages": [f"answer={answer}"]}

        builder = StateGraph(State)
        builder.add_node("ask", _asker)
        builder.add_edge(START, "ask")
        builder.add_edge("ask", END)
        app = builder.compile(checkpointer=stub)
        config = RunConfig(thread_id="t-resume")

        first = app.invoke({"messages": []}, config)
        assert "__interrupt__" in first

        second = app.invoke(Command(resume="yes"), config)
        assert seen == ["yes"]
        assert "answer=yes" in second["messages"]

    def test_resume_without_checkpointer_raises_interrupt_error(self) -> None:
        """**未挂** checkpointer 时提交 ``Command(resume=...)`` ⇒ ⇒ MUST 抛**明确异常**
        ⇒ ⇒ **MUST NOT** 静默降级为「内存态恢复」（FR-019 · H-4 ④）。"""
        builder = _interrupting_graph()
        app = builder.compile()
        app.invoke({"messages": []})
        with pytest.raises(InterruptError) as excinfo:
            app.invoke(Command(resume="yes"))
        assert excinfo.value.reason == InterruptError.REASON_CHECKPOINTER_REQUIRED

    def test_interrupt_error_reason_is_in_the_closed_value_domain(self) -> None:
        """``InterruptError.reason`` MUST 落在**封闭取值域**内（FR-019）。"""
        builder = _interrupting_graph()
        app = builder.compile()
        app.invoke({"messages": []})
        with pytest.raises(InterruptError) as excinfo:
            app.invoke(Command(resume="yes"))
        assert excinfo.value.reason in InterruptError.REASONS
