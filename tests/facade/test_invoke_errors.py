# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B7F3 · US3 —— **失败信号**（未知 key / 真异常原样传播 / 不包装）。

**共享夹具**：``tests/facade/_invoke_support.py``。

**判据**：spec FR-016 / FR-017 / FR-020 · SC-004 / SC-005 · 契约 §6 的 **I-06 / I-07**。
"""

from __future__ import annotations

from typing import Any

import pytest

from freegraph.contracts.errors import InvalidUpdateError
from freegraph.graph import END, START, StateGraph

from ._invoke_support import State, build_two_node_graph


def _graph_with(node: Any) -> StateGraph:
    builder = StateGraph(State)
    builder.add_node("a", node)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    return builder


class TestUnknownKey:
    def test_unknown_node_key_raises_invalid_update_error(self) -> None:
        """节点返回**未知 key** ⇒ MUST 抛 ``InvalidUpdateError``（FR-016）。"""
        builder = _graph_with(lambda state: {"messages": ["x"], "typo_key": 1})
        with pytest.raises(InvalidUpdateError):
            builder.compile().invoke({"messages": []})

    def test_unknown_node_key_message_names_the_offending_key(self) -> None:
        """异常消息 MUST **点名**违规 key（FR-016 · 契约 I-06）。"""
        builder = _graph_with(lambda state: {"messages": ["x"], "typo_key": 1})
        with pytest.raises(InvalidUpdateError) as excinfo:
            builder.compile().invoke({"messages": []})
        assert "typo_key" in str(excinfo.value)

    def test_several_unknown_keys_are_all_named(self) -> None:
        """**多个**未知 key ⇒ ⇒ 消息 MUST 含**全部**未知 key 名（FR-016）。"""
        builder = _graph_with(
            lambda state: {"messages": ["x"], "typo_one": 1, "typo_two": 2}
        )
        with pytest.raises(InvalidUpdateError) as excinfo:
            builder.compile().invoke({"messages": []})
        message = str(excinfo.value)
        assert "typo_one" in message
        assert "typo_two" in message

    def test_invalid_update_error_carries_structured_invalid_keys(self) -> None:
        """``InvalidUpdateError`` MUST 带**结构化**的 ``invalid_keys``（Key Entities）。"""
        builder = _graph_with(lambda state: {"messages": ["x"], "typo_key": 1})
        with pytest.raises(InvalidUpdateError) as excinfo:
            builder.compile().invoke({"messages": []})
        assert "typo_key" in tuple(excinfo.value.invalid_keys)

    def test_unknown_input_key_raises_invalid_update_error(self) -> None:
        """**初始输入**含未知 key ⇒ ⇒ 同样抛 ``InvalidUpdateError``（FR-013）。"""
        with pytest.raises(InvalidUpdateError):
            build_two_node_graph().compile().invoke({"messages": [], "bogus": 1})

    def test_no_partial_result_is_returned_on_failure(self) -> None:
        """失败时 MUST **不返回**任何部分结果（FR-017 · US3 验收场景 3）。"""
        builder = _graph_with(lambda state: {"messages": ["x"], "typo_key": 1})
        with pytest.raises(InvalidUpdateError):
            builder.compile().invoke({"messages": []})


class TestExceptionIdentity:
    def test_user_exception_reaches_the_caller_unchanged(self) -> None:
        """节点的真异常 MUST 以**原始类型 + 原始消息**到达调用方（FR-017 · 契约 I-07）。"""

        class Boom(RuntimeError):
            pass

        builder = _graph_with(_raiser(Boom))
        with pytest.raises(Boom) as excinfo:
            builder.compile().invoke({"messages": []})
        assert type(excinfo.value) is Boom
        assert str(excinfo.value) == "原始消息 payload"

    def test_exception_is_not_wrapped_into_runtime_error(self) -> None:
        """异常 MUST **不**被包装（**不是** ``RuntimeError`` · FR-017）。"""

        class Boom(RuntimeError):
            pass

        builder = _graph_with(_raiser(Boom))
        with pytest.raises(Boom):
            builder.compile().invoke({"messages": []})
        try:
            builder.compile().invoke({"messages": []})
        except Exception as exc:  # noqa: BLE001
            assert type(exc) is not RuntimeError or type(exc).__name__ == "Boom"

    def test_recursion_error_is_not_wrapped(self) -> None:
        """``GraphRecursionError`` MUST **原样**传播（FR-018 · 契约 I-08）。"""
        from freegraph.contracts.errors import GraphRecursionError

        builder = StateGraph(State)
        builder.add_node("loop", lambda state: {"llm_calls": 1})
        builder.add_edge(START, "loop")
        builder.add_edge("loop", "loop")
        builder.add_edge("loop", END)
        with pytest.raises(GraphRecursionError) as excinfo:
            builder.compile().invoke({"messages": []}, {"recursion_limit": 3})
        assert type(excinfo.value) is GraphRecursionError
        assert excinfo.value.recursion_limit == 3


def _raiser(exc_type: type[Exception]) -> Any:
    """构造一个**抛出**指定类型异常的节点替身。"""

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        raise exc_type("原始消息 payload")

    return _node
