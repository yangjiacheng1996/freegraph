# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B7F3 · US1 / US2 —— ``invoke()`` 的**完整状态**（键集 / 顺序 / 补齐 / 合并 / 覆盖）。

**共享夹具**：``tests/facade/_invoke_support.py``。

**判据**：spec FR-007 / FR-008 / FR-010 / FR-011 / FR-012 · SC-001 / SC-002 / SC-003 / SC-013
· 契约 §6 的 **I-01 / I-02 / I-03 / I-05 / I-13**。
"""

from __future__ import annotations

from typing import Any

import pytest

from freegraph import runtime
from freegraph.graph import END, START, StateGraph

from ._invoke_support import (
    State,
    build_conditional_graph,
    build_fanout_graph,
    build_two_node_graph,
)

#: **schema 声明顺序**（= 通道表扣除路由通道后的顺序）。
SCHEMA_KEYS = ["messages", "llm_calls"]


# ── US1 · 完整状态 ───────────────────────────────────────────────────────────


class TestFullState:
    def test_result_is_a_plain_dict(self) -> None:
        """返回值的类型 MUST 是**普通 ``dict``**（FR-007）。"""
        out = build_two_node_graph().compile().invoke({"messages": ["seed"]})
        assert type(out) is dict

    def test_key_set_equals_the_full_schema_key_set(self) -> None:
        """键集 MUST == **schema 全部 key**（**一个都不漏** · FR-008）。"""
        out = build_two_node_graph().compile().invoke({"messages": ["seed"]})
        assert list(out) == SCHEMA_KEYS

    def test_key_order_matches_the_schema_declaration_order(self) -> None:
        """键的**顺序** MUST 与 schema 声明顺序**逐字一致**（FR-008）。"""
        out = build_two_node_graph().compile().invoke({"messages": ["seed"]})
        assert list(out) == ["messages", "llm_calls"]

    def test_messages_contains_initial_plus_every_new_value(self) -> None:
        """``messages`` == **初始 + 全部新增**（**不是**增量 · FR-010 · SC-002）。"""
        out = build_two_node_graph().compile().invoke({"messages": ["seed"]})
        assert out["messages"] == ["seed", "a", "b"]

    def test_result_is_not_a_delta(self) -> None:
        """返回值**不是**增量 ⇒ ⇒ 初始消息**仍在**结果里（US1 验收场景 3）。"""
        out = build_two_node_graph().compile().invoke({"messages": ["seed"]})
        assert "seed" in out["messages"]

    def test_graph_runs_to_termination(self) -> None:
        """图 MUST 跑到**终止** ⇒ ⇒ **每个可达节点**都执行过（FR-003 · SC-013）。"""
        seen: list[str] = []

        def _a(state: dict[str, Any]) -> dict[str, Any]:
            seen.append("a")
            return {"messages": ["a"]}

        def _b(state: dict[str, Any]) -> dict[str, Any]:
            seen.append("b")
            return {"messages": ["b"]}

        builder = StateGraph(State)
        builder.add_node("a", _a)
        builder.add_node("b", _b)
        builder.add_edge(START, "a")
        builder.add_edge("a", "b")
        builder.add_edge("b", END)
        builder.compile().invoke({"messages": []})
        assert seen == ["a", "b"]

    def test_result_does_not_alias_the_caller_input(self) -> None:
        """返回值 MUST **不是**调用方传入的字典对象（不得就地改写调用方的数据）。"""
        payload: dict[str, Any] = {"messages": ["seed"]}
        out = build_two_node_graph().compile().invoke(payload)
        assert out is not payload
        assert payload == {"messages": ["seed"]}

    def test_multi_source_barrier_lands_after_every_source(self) -> None:
        """**多源汇合（屏障）**：屏障目标 MUST 在**所有**源之后出现（FR-003 · SC-013）。

        ⚠️ **静态多源边**（``add_edge(["a", "b"], "c")`` · **B7F4 已交付于 L2**）⇒ ⇒
        **不依赖** B8F1 的条件边路由 ⇒ ⇒ ⇒ 本条**物理可达**。
        """
        builder = build_fanout_graph()
        builder.add_edge(["a", "b"], "c")
        out = builder.compile().invoke({"messages": ["seed"]})
        messages = list(out["messages"])
        # a 与 b 的写入都在 c 的写入之前 ⇒ c 的消息是**最后**一条
        assert messages[-1] == "b"  # c 与 b 写入同款内容 ⇒ c 落在最后
        assert messages.count("b") == 2  # b 自己的写入 + c 的写入
        assert messages[:3] == ["seed", "a", "b"]

    def test_route_channels_are_excluded_from_the_key_set(self) -> None:
        """路由通道 MUST **不进**返回键集（FR-012 · 契约 I-03）。

        ⚠️ 用**带** ``path_map`` 的条件边图 ⇒ ⇒ 才有 ``branch:to:*`` 通道 ⇒ ⇒
        否则该断言**恒真**（空洞）。
        """
        out = build_conditional_graph().compile().invoke({"messages": ["seed"]})
        assert list(out) == SCHEMA_KEYS
        assert not any(key.startswith("branch:to:") for key in out)

    def test_conditional_graph_actually_has_route_channels(self) -> None:
        """**反向护栏**：条件边图 MUST **真的有**路由通道 ⇒ ⇒ 上条不是空洞断言。"""
        builder = build_conditional_graph()
        spec = builder._build_spec()  # type: ignore[attr-defined]
        assert any(key.startswith("branch:to:") for key in spec.channels)


# ── US2 · 计数型 key 与「无值」补齐 ──────────────────────────────────────────


class TestFillAndCoverage:
    def test_unwritten_overwriting_key_is_present_with_none(self) -> None:
        """**从未被写**的**覆盖型（无归约器）**key MUST 在键集里 · 值 = ``None``
        （FR-009 · 契约 I-02）。"""
        out = build_two_node_graph().compile().invoke({"messages": ["seed"]})
        assert "llm_calls" in out
        assert out["llm_calls"] is None

    def test_unwritten_reducer_key_keeps_its_type_empty_value(self) -> None:
        """**从未被写**的**归约型**key MUST 保留**类型空值**（``[]``）⇒ ⇒
        **MUST NOT** 被改写成 ``None``（FR-009 · 契约 R-06）。"""
        builder = StateGraph(State)
        builder.add_node("a", lambda state: {"llm_calls": 1})
        builder.add_edge(START, "a")
        builder.add_edge("a", END)
        out = builder.compile().invoke({"messages": []})
        assert out["messages"] == []
        assert out["messages"] is not None

    def test_overwriting_key_holds_the_last_written_value(self) -> None:
        """**无归约器**的 key MUST 是**覆盖**后的最终值（**不是**累加 · FR-011）。"""
        builder = StateGraph(State)
        builder.add_node("a", lambda state: {"llm_calls": 1})
        builder.add_node("b", lambda state: {"llm_calls": 2})
        builder.add_edge(START, "a")
        builder.add_edge("a", "b")
        builder.add_edge("b", END)
        out = builder.compile().invoke({"messages": []})
        assert out["llm_calls"] == 2

    def test_node_input_stays_sparse(self) -> None:
        """**节点入参仍稀疏**（C4）⇒ ⇒ 「无值 key 填 ``None``」MUST NOT 泄漏到入参
        （FR-025）。"""
        seen: list[dict[str, Any]] = []

        def _a(state: dict[str, Any]) -> dict[str, Any]:
            seen.append(dict(state))
            return {}

        builder = StateGraph(State)
        builder.add_node("a", _a)
        builder.add_edge(START, "a")
        builder.add_edge("a", END)
        builder.compile().invoke({"messages": []})
        assert seen
        assert "llm_calls" not in seen[0]
        assert seen[0].get("llm_calls") is None
        assert seen[0].get("llm_calls", 0) == 0

    def test_explicit_none_initial_value_is_still_written(self) -> None:
        """用户**显式传入** ``None`` 作为初始值 ⇒ ⇒ **仍被写进通道**
        （FR-009 · SC-020 的「只约束返回值」半边）。"""
        seen: list[Any] = []

        def _a(state: dict[str, Any]) -> dict[str, Any]:
            seen.append(state.get("llm_calls"))
            return {}

        builder = StateGraph(State)
        builder.add_node("a", _a)
        builder.add_edge(START, "a")
        builder.add_edge("a", END)
        builder.compile().invoke({"messages": [], "llm_calls": None})
        assert seen == [None]


# ── 冻结持有面（FR-028 / SC-016 · 契约 I-10）────────────────────────────────


class TestFrozenHoldingFace:
    PRIVATE = {"_spec", "_builder_spec", "_conditional_edges"}
    PUBLIC = {
        "checkpointer",
        "store",
        "cache",
        "debug",
        "name",
        "transformers",
        "interrupt_before_nodes",
        "interrupt_after_nodes",
    }

    def test_vars_is_exactly_the_eleven_frozen_names(self) -> None:
        """``vars(compiled)`` MUST **恰好**是那 **11** 个冻结名（B7F2 冻结面）。"""
        compiled = build_two_node_graph().compile()
        assert set(vars(compiled)) == self.PRIVATE | self.PUBLIC
        assert len(vars(compiled)) == 11

    def test_runtime_export_surface_is_unchanged(self) -> None:
        """``freegraph.runtime.__all__`` MUST 仍**恰好 23** 个符号（**零新增**导出）。"""
        assert len(runtime.__all__) == 23

    def test_facade_export_surface_is_unchanged(self) -> None:
        """门面导出面 MUST 仍**恰好 8** 个符号（B8F2 +1）。"""
        import freegraph.graph as facade

        assert len(facade.__all__) == 8


@pytest.mark.parametrize("payload", [{}, {"messages": []}])
def test_invoke_never_raises_not_implemented(payload: dict[str, Any]) -> None:
    """``invoke()`` 在**任何合法路径**上 MUST **不**抛 ``NotImplementedError``
    （FR-001 · SC-015 · 契约 I-12）。"""
    builder = build_two_node_graph()
    out = builder.compile().invoke(payload)
    assert list(out) == SCHEMA_KEYS
