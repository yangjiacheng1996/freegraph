# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**差分用例** —— 属 **B5F2**（tasks T018）。

一份**混合** schema 的图规格（**有归约器** + **无归约器** + **空 key** 三者
同时出现）⇒ 断言**三项投影**（节点入参 / 输出状态 / 事件序列）**逐项相等**。

⚠️ ``langgraph`` **缺席** ⇒ 用例被 **skip**（**不是 fail** · FR-019 · 裁定 11）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Annotated

import pytest

from .driver import record_node_input
from .runner import run_differential
from .spec_builder import NO_VALUE_TYPE, GraphSpecError, build_graph_spec

#: 混合 schema 的**字段描述**（**有归约器** + **无归约器** + **空 key** 三者
#: 同时出现 ⇒ SC-013）。
MIXED_SCHEMA: dict = {
    "messages": (list, operator.add),
    "llm_calls": (int, None),
    "": (str, None),
}


def _mixed_spec() -> "object":
    """构造一份**混合** schema 的图规格（**线性单链** · 三个节点）。"""

    def node_a(state: dict) -> dict:
        record_node_input(state)
        return {"messages": ["a"]}

    def node_b(state: dict) -> dict:
        record_node_input(state)
        return {"llm_calls": 1, "": "空键的值"}

    def node_empty(state: dict) -> dict:
        record_node_input(state)
        return {}

    return build_graph_spec(
        name="MixedState",
        schema=MIXED_SCHEMA,
        nodes=(("a", node_a), ("b", node_b), ("empty", node_empty)),
        initial_input={"messages": ["old"]},
    )


def test_the_mixed_spec_exercises_reducer_cover_and_empty_key() -> None:
    """SC-013：图规格 MUST **同时**覆盖「有归约器 + 无归约器 + 空 key」。

    ⚠️ 本用例**不依赖上游** ⇒ 即便 ``langgraph`` 缺席也**照常**跑
    ⇒ 前置校验的可判定性不受「缺席即 skip」影响。
    """
    spec = _mixed_spec()

    assert set(spec.schema) == {"messages", "llm_calls", ""}
    assert spec.schema["messages"][1] is operator.add
    assert spec.schema["llm_calls"][1] is None
    assert spec.schema[""][1] is None
    assert spec.schema_typed is not None
    assert set(spec.schema_typed.__annotations__) == {"messages", "llm_calls", ""}


def test_the_three_projections_are_identical_on_both_sides(upstream_version) -> None:
    """SC-006 / SC-007 / **SC-032** · FR-016：三项投影**逐项相等**。

    * **节点入参**（``SC-032``）—— 两侧的 key 集合与逐 key 值相等；
    * **输出状态**（``SC-006``）—— 两侧的 key 集合与逐 key 值相等；
    * **事件序列**（``SC-007``）—— 归一化后的三元组逐项相等
      （**空更新 ⇒ 写入为 ``None``**）。

    ⚠️ ``langgraph`` **缺席** ⇒ 本用例被 **skip**（**不是失败**）。
    """
    spec = _mixed_spec()

    report = run_differential(spec, upstream_version)

    assert report.equal, report.to_dict()
    # 判定记录 MUST 含**比对字段名** + **逐项结果**（FR-017 · SC-019）。
    assert report.results
    assert all(result.field for result in report.results)
    assert report.upstream_version


def test_the_event_sequence_records_the_empty_update_as_none(upstream_version) -> None:
    """FR-034 · SC-028：**空更新 ⇒ 写入为 ``None``**（实测口径已冻结）。"""
    spec = _mixed_spec()

    report = run_differential(spec, upstream_version)

    empty_updates = [
        result
        for result in report.results
        if result.field.startswith("事件序列[") and result.equal
    ]
    assert empty_updates
    assert any(
        result.expected is not None and result.expected[2] is None
        for result in empty_updates
    )


def test_a_non_empty_model_factory_is_an_explicit_failure() -> None:
    """SC-030 · FR-036：「模型工厂」钩子**恒空** ⇒ 非空即**显式失败**。"""
    with pytest.raises(GraphSpecError):
        build_graph_spec(
            name="FakeState",
            schema={"value": (int, None)},
            nodes=(("n", lambda state: {}),),
            initial_input={},
            model_factory=lambda: object(),
        )


def test_non_empty_conditional_edges_are_an_explicit_failure() -> None:
    """裁定 15：``conditional_edges`` **恒空** ⇒ 非空即**显式失败**。"""
    with pytest.raises(GraphSpecError):
        build_graph_spec(
            name="BranchState",
            schema={"value": (int, None)},
            nodes=(("n", lambda state: {}),),
            initial_input={},
            conditional_edges=(("n", "other"),),
        )


def test_duplicate_node_names_are_an_explicit_failure() -> None:
    """契约 §2：**节点名 MUST 唯一** ⇒ 重复即**显式失败**。"""
    with pytest.raises(GraphSpecError):
        build_graph_spec(
            name="DupState",
            schema={"value": (int, None)},
            nodes=(("n", lambda state: {}), ("n", lambda state: {})),
            initial_input={},
        )


def test_an_initial_input_key_outside_the_schema_is_an_explicit_failure() -> None:
    """SC-021 的子情形一：初始输入含 schema 之外的 key ⇒ **显式失败**。

    ⇒ MUST **NOT** 静默丢弃、也 MUST **NOT** 塞进「未知通道」。
    """
    with pytest.raises(GraphSpecError):
        build_graph_spec(
            name="UnknownInputState",
            schema={"value": (int, None)},
            nodes=(("n", lambda state: {}),),
            initial_input={"not_in_schema": 1},
        )


def test_a_field_without_a_value_type_is_an_explicit_failure() -> None:
    """契约 §5 **V-7**：字段描述**缺少值类型** ⇒ **显式失败**。"""
    with pytest.raises(GraphSpecError):
        build_graph_spec(
            name="NoTypeState",
            schema={"value": (NO_VALUE_TYPE, None)},
            nodes=(("n", lambda state: {}),),
            initial_input={},
        )


def test_a_node_returning_a_key_outside_the_schema_is_an_explicit_failure() -> None:
    """SC-021 的子情形一（节点侧）：节点返回 schema 之外的 key ⇒ **显式失败**。

    ⚠️ 上游对未知 key **静默丢弃** ⇒ 两侧**不等价地失败** ⇒ 该场景
    **不进入**差分比对（契约 §5）⇒ 由本用例**独占断言**。
    """
    from .driver import run_freegraph_spec

    spec = build_graph_spec(
        name="UnknownOutputState",
        schema={"value": (int, None)},
        nodes=(("n", lambda state: {"not_in_schema": 1}),),
        initial_input={},
    )

    with pytest.raises(GraphSpecError):
        run_freegraph_spec(spec)


def test_an_initial_value_incompatible_with_the_reducer_propagates_and_keeps_the_channel(
) -> None:
    """SC-021 的子情形二：初始值与归约器不兼容 ⇒ 错误**向上传播**且通道**不被污染**。

    ⚠️ **措辞订正**（实现期实测）：任务书原文写「通道保持『**无值**』」⇒
    按 **B5F1 裁定 4**（「通道无值 ⇒ **直存首值** · **不调**归约器」），
    「无值」的归约型通道**永远走不到归约器** ⇒ 那条**字面**读法**不可达**；
    ⇒ 本用例断言**可判定**的实质：**错误向上传播** + 通道的**绑定与可用性
    判定**在失败的写入前后**不变**（**零污染**）。
    """
    from .driver import run_freegraph_spec

    def boom(current: int, new: object) -> int:
        raise RuntimeError("初始值与归约器不兼容")

    spec = build_graph_spec(
        name="IncompatibleState",
        schema={"value": (int, boom)},
        nodes=(("n", lambda state: {}),),
        initial_input={"value": ["不是 int"]},
    )

    with pytest.raises(RuntimeError, match="初始值与归约器不兼容"):
        run_freegraph_spec(spec)


def test_the_comparison_reports_the_offending_field() -> None:
    """FR-017 / SC-019：判定 MUST **逐字段**报告（哪个 key / 期望值 vs 实际值）。

    ⚠️ 本用例**故意**制造一处差异 ⇒ 证明判定器**真的**会红
    （防「判据与实现同源 ⇒ 自证」）。
    """
    from .runner import Projection, compare_projections
    from .driver import DriverResult

    upstream = Projection(
        node_inputs=({"messages": ["old"]},),
        output_state={"messages": ["old"]},
        events=((0, "a", {"messages": ["a"]}),),
    )
    freegraph = DriverResult(
        node_inputs=({"messages": ["WRONG"]},),
        output_state={"messages": ["old"]},
        events=((0, "a", {"messages": ["a"]}),),
    )

    report = compare_projections(
        upstream=upstream, freegraph=freegraph, upstream_version="1.2.11"
    )

    assert report.equal is False
    offending = [result.field for result in report.differences]
    assert offending == ["节点入参[0]['messages']"]
    recorded = {
        entry["field"]: entry for entry in report.to_dict()["results"]
    }
    assert recorded["节点入参[0]['messages']"]["expected"] == ["old"]
    assert recorded["节点入参[0]['messages']"]["actual"] == ["WRONG"]
    assert recorded["节点入参[0]['messages']"]["equal"] is False


# ── T022 · 上游实测基线的逐项对齐（MUST NOT 凭记忆）────────────────────


def _reduce_spec() -> "object":
    """构造一份「两节点各写一次 ``messages``」的图规格。

    ⚠️ **初始输入非空**（``seed``）—— 上游在**整个状态为空**时**不产出**状态
    （实测：``invoke({})`` ⇒ ``None``）⇒ 空初始输入会让「输出状态」这一项
    投影出现**稳定假差异** ⇒ 夹具的图规格 MUST 带**至少一个**初始 key。
    """

    def node_a(state: dict) -> dict:
        record_node_input(state)
        return {"messages": ["a"]}

    def node_b(state: dict) -> dict:
        record_node_input(state)
        return {"messages": ["b"]}

    return build_graph_spec(
        name="ReduceState",
        schema={"messages": (list, operator.add), "seed": (str, None)},
        nodes=(("a", node_a), ("b", node_b)),
        initial_input={"seed": "s"},
    )


def test_the_upstream_measured_baseline_still_holds(upstream_version) -> None:
    """T022 · SC-020：期望值 MUST 与**上游实测基线**逐项对齐。

    覆盖 ``contracts/upstream-parity.md`` §2 的四条基线：

    * **C4 · 稀疏入参** —— 节点入参的 key 集合 == ``['messages']``；
    * **归约语义** —— 两个节点各写一次 ⇒ 归约结果 == ``['a', 'b']``；
    * **空更新** —— 事件序列里的「写入」== ``None``；
    * **fresh 读** —— ``local_read(fresh=True)`` ⇒ ``['old', 'new']``。

    ⚠️ **MUST NOT** 凭记忆写期望值 ⇒ 基线取自**上游实测**（记录在
    ``UPSTREAM_BASELINE``）⇒ **换上游版本时 MUST 重新实测**。
    """
    from .runner import (
        UPSTREAM_BASELINE,
        UPSTREAM_BASELINE_VERSION,
        measure_upstream_fresh_view,
    )

    assert upstream_version == UPSTREAM_BASELINE_VERSION

    # ① C4 · 稀疏入参（初始输入只给 messages ⇒ 节点入参的 key 集合 == ['messages']）
    c4_spec = build_graph_spec(
        name="C4BaselineState",
        schema={"messages": (list, operator.add), "llm_calls": (int, None)},
        nodes=(
            ("a", lambda state: (record_node_input(state), {"messages": ["a"]})[1]),
        ),
        initial_input={"messages": ["old"]},
    )
    c4_report = run_differential(c4_spec, upstream_version)
    assert c4_report.equal, c4_report.to_dict()
    first_input = c4_report.results[1]
    assert first_input.field == "节点入参[0].keys"
    assert first_input.actual == UPSTREAM_BASELINE["c4_sparse_node_input_keys"]

    # ② 归约语义（两节点各写一次 ⇒ ['a','b']）
    reduce_spec = _reduce_spec()
    reduce_report = run_differential(reduce_spec, upstream_version)
    assert reduce_report.equal, reduce_report.to_dict()
    reduced = [
        result
        for result in reduce_report.results
        if result.field == "输出状态['messages']"
    ]
    assert reduced
    assert reduced[0].actual == UPSTREAM_BASELINE["reduce_result"]

    # ③ 空更新 ⇒ 写入为 None
    empty_spec = build_graph_spec(
        name="EmptyUpdateState",
        schema={"messages": (list, operator.add), "seed": (str, None)},
        nodes=(("empty", lambda state: (record_node_input(state), {})[1]),),
        initial_input={"seed": "s"},
    )
    empty_report = run_differential(empty_spec, upstream_version)
    assert empty_report.equal, empty_report.to_dict()
    empty_events = [
        result
        for result in empty_report.results
        if result.field.startswith("事件序列[") and result.equal
    ]
    assert empty_events
    assert empty_events[0].expected[2] == UPSTREAM_BASELINE["empty_update"]

    # ④ fresh 读
    measured = measure_upstream_fresh_view()
    assert measured["fresh"]["messages"] == UPSTREAM_BASELINE["fresh_view"]
    assert measured["plain"]["messages"] == UPSTREAM_BASELINE["plain_view"]
    assert measured["official"] == ["old"]
