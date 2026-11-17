# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B7F3 · US4 —— **配置面**（``RunConfig`` / 普通映射双形态 / 递归上限 / 并发度旋钮）。

**共享夹具**：``tests/facade/_invoke_support.py``。

**判据**：spec FR-021 / FR-022 / FR-023 · SC-006 / SC-007 · 契约 §6 的 **I-08**。
"""

from __future__ import annotations

import threading
from types import MappingProxyType
from typing import Any

import pytest

from freegraph.contracts.errors import GraphRecursionError
from freegraph.contracts.types import RunConfig

from ._invoke_support import (
    State,
    build_fanout_graph,
    build_loop_graph,
    build_two_node_graph,
)

#: **互等到齐**的超时（秒）—— 远大于线程调度抖动 · 远小于 CI 超时上限。
#: ⚠️ **超时**只用于「等不到对端」的**串行档**（串行**正是**期望）⇒ ⇒
#: **超时本身不判失败**。
BARRIER_TIMEOUT = 2.0


class TestConfigShapes:
    def test_run_config_instance_is_accepted(self) -> None:
        """``RunConfig`` 实例 MUST 被接受（FR-021）。"""
        out = build_two_node_graph().compile().invoke(
            {"messages": ["seed"]}, RunConfig(max_concurrency=1)
        )
        assert list(out) == ["messages", "llm_calls"]

    def test_plain_dict_is_accepted(self) -> None:
        """普通 ``dict`` MUST 被接受（FR-021）。"""
        out = build_two_node_graph().compile().invoke({"messages": ["seed"]}, {})
        assert list(out) == ["messages", "llm_calls"]

    def test_another_mapping_type_is_accepted(self) -> None:
        """**别的**映射类型（**非**字面 ``dict``）MUST 也被接受（Edge Cases）。"""
        out = build_two_node_graph().compile().invoke(
            {"messages": ["seed"]}, MappingProxyType({"recursion_limit": 10})
        )
        assert list(out) == ["messages", "llm_calls"]

    def test_unknown_mapping_keys_are_ignored(self) -> None:
        """映射里的**未知键** MUST 被**宽容忽略**（FR-021 · 上游同款）。"""
        out = build_two_node_graph().compile().invoke(
            {"messages": ["seed"]}, {"bogus_key": 1}
        )
        assert list(out) == ["messages", "llm_calls"]

    def test_none_config_is_accepted(self) -> None:
        """``config=None`` MUST 被接受。"""
        out = build_two_node_graph().compile().invoke({"messages": ["seed"]}, None)
        assert list(out) == ["messages", "llm_calls"]

    def test_invalid_config_type_raises_type_error(self) -> None:
        """非 ``RunConfig`` / 非映射 / 非 ``None`` ⇒ MUST 抛 ``TypeError``（契约 F-06）。"""
        with pytest.raises(TypeError):
            build_two_node_graph().compile().invoke(
                {"messages": []}, 42  # type: ignore[arg-type]
            )


class TestRecursionLimit:
    def test_recursion_limit_from_mapping_takes_effect(self) -> None:
        """``{"recursion_limit": N}`` MUST 生效 ⇒ ⇒ 超限抛 ``GraphRecursionError``
        （FR-022 · SC-007）。"""
        with pytest.raises(GraphRecursionError) as excinfo:
            build_loop_graph().compile().invoke({"messages": []}, {"recursion_limit": 3})
        assert type(excinfo.value) is GraphRecursionError
        assert excinfo.value.recursion_limit == 3

    def test_recursion_error_is_not_wrapped(self) -> None:
        """``GraphRecursionError`` MUST **不被包装**（契约 I-08）。"""
        with pytest.raises(GraphRecursionError):
            build_loop_graph().compile().invoke({"messages": []}, {"recursion_limit": 3})


def _fanout_overlap_graph() -> tuple[Any, dict[str, int]]:
    """**复用** ``build_fanout_graph()`` ⇒ ⇒ 记录「同时在飞」的**重叠计数**。

    ⚠️ **重叠 MUST 用确定性同步构造**（``threading.Event`` 互等到齐）⇒ ⇒
    **MUST NOT** 依赖「时间流逝」（⇒ CI 慢档 / Windows 档会假红）。
    """
    overlap = {"current": 0, "max": 0}
    lock = threading.Lock()
    arrived = threading.Event()

    def _make(tag: str) -> Any:
        def _node(state: dict[str, Any]) -> dict[str, Any]:
            with lock:
                # ⚠️ **重叠计数** = 进入时**已有多少个别的节点同时在飞**
                # ⇒ ⇒ 串行档（一次只跑一个）恒为 **0** · 并发档 ≥ **1**。
                overlap["max"] = max(overlap["max"], overlap["current"])
                overlap["current"] += 1
            # ⚠️ **确定性**互等：两个节点**都到齐**才继续（缺省档必然到齐）。
            arrived.wait(BARRIER_TIMEOUT)
            with lock:
                overlap["current"] -= 1
            return {"messages": [tag]}

        return _node

    builder = build_fanout_graph(node_a=_make("a"), node_b=_make("b"))
    return builder, overlap


class TestConcurrencyKnob:
    """**并发度旋钮**（FR-023 · SC-006）。

    ⚠️ **可观测并发度**才是**判定性**的断言（最终状态与并发度**无关** ⇒ ⇒
    「结果逐字相等」**无法**判定旋钮是否生效）⇒ ⇒ MUST 用**重叠计数**判定。
    """

    def test_serial_baseline_has_zero_overlap(self) -> None:
        """``max_concurrency=1`` ⇒ ⇒ 重叠计数 MUST == **0**（**串行基线**）。"""
        builder, overlap = _fanout_overlap_graph()
        builder.compile().invoke({"messages": []}, RunConfig(max_concurrency=1))
        assert overlap["max"] == 0

    def test_default_run_has_overlap(self) -> None:
        """缺省档 ⇒ ⇒ 重叠计数 MUST **≥ 1**（⇒ ⇒ 这是「旋钮生效」的判定性证据）。"""
        builder, overlap = _fanout_overlap_graph()
        builder.compile().invoke({"messages": []})
        assert overlap["max"] >= 1

    def test_explicit_knob_in_mapping_takes_effect(self) -> None:
        """``config`` 映射形态的旋钮 MUST **同样生效**（读取点在 L2 · 裁定 13）。"""
        builder, overlap = _fanout_overlap_graph()
        builder.compile().invoke({"messages": []}, {"max_concurrency": 1})
        assert overlap["max"] == 0

    def test_serial_and_concurrent_results_are_byte_identical(self) -> None:
        """**补充**判据：串行档与并发档的最终状态 MUST **逐字相等**（SC-006）。"""
        serial = build_two_node_graph().compile().invoke(
            {"messages": ["seed"]}, RunConfig(max_concurrency=1)
        )
        concurrent = build_two_node_graph().compile().invoke({"messages": ["seed"]})
        assert serial == concurrent

    def test_invalid_knob_value_raises_type_error(self) -> None:
        """类型不符 ⇒ MUST **入口即**抛内置 ``TypeError``（FR-023 · 契约 F-07）。"""
        with pytest.raises(TypeError) as excinfo:
            build_two_node_graph().compile().invoke(
                {"messages": []}, {"max_concurrency": "x"}
            )
        assert "max_concurrency" in str(excinfo.value)

    def test_invalid_knob_value_raises_value_error(self) -> None:
        """``< 1`` ⇒ MUST **入口即**抛内置 ``ValueError``（FR-023 · 契约 F-07）。"""
        with pytest.raises(ValueError) as excinfo:
            build_two_node_graph().compile().invoke(
                {"messages": []}, {"max_concurrency": 0}
            )
        assert "max_concurrency" in str(excinfo.value)
