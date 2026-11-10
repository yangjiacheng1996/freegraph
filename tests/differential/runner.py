# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**差分执行与判定** —— 属 **B5F2**（tasks T021 / T022）。

**契约权威**：``specs/b5f2-sparse-state-read/contracts/differential-fixture.md``
§3（三项投影）· §4（**判定**）· §6（与上游的**可核对性**）。

**三项投影**（**归一化**后再比）：

============  ====================================================  ==========
投影          形态                                                 上游来源
============  ====================================================  ==========
**节点入参**  ``dict[str, Any]``（key 集合 + 逐 key 值）           节点函数**内部**留存
**输出状态**  ``dict[str, Any]``（key 集合 + 逐 key 值）           ``invoke()`` 返回值
**事件序列**  ``[(步序, 节点名, 写入)]``（**无更新 ⇒ 写入为 ``None``**）  ``stream(stream_mode="updates")``
============  ====================================================  ==========

⚠️ **判定 MUST 逐字段报告**（哪个 key / 哪个步序 / 期望值 vs 实际值），
MUST NOT 只写「一致」（FR-017 · SC-019）⇒ **判定记录** MUST 含**比对字段名
+ 逐项结果**。

⚠️ **key 的顺序不比对**（契约 §5）⇒ 归一化只取「**key 集合** + 逐 key 值」。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Any, Mapping

from .driver import (
    DriverResult,
    observed_node_inputs,
    reset_observed_node_inputs,
    run_freegraph_spec,
)
from .spec_builder import GraphSpec

__all__ = [
    "DiffReport",
    "FieldResult",
    "Projection",
    "UPSTREAM_BASELINE",
    "compare_projections",
    "measure_upstream_fresh_view",
    "run_differential",
    "run_upstream_spec",
]

#: **上游的实测基线**（`contracts/upstream-parity.md` §2 · 核实于
#: ``langgraph 1.2.11`` · CPython 3.11.16）—— **MUST NOT** 凭记忆写期望值。
#:
#: ⚠️ **换上游版本时 MUST 重新实测该基线**（宪法原则 VIII）⇒ 本常量与
#: 上游版本的对应关系由本文件的 ``UPSTREAM_BASELINE_VERSION`` 钉住。
UPSTREAM_BASELINE: dict[str, Any] = {
    #: **C4 · 稀疏入参** —— 初始输入只给 ``messages`` ⇒ 节点入参的 key 集合
    #: == ``['messages']``（无值 key **不出现**）。
    "c4_sparse_node_input_keys": ["messages"],
    #: **归约语义** —— 两个节点各写一次 ``messages`` ⇒ 归约结果 == ``['a', 'b']``。
    "reduce_result": ["a", "b"],
    #: **空更新** —— 节点返回 ``{}`` ⇒ 事件序列里的「写入」== ``None``。
    "empty_update": None,
    #: **fresh 读** —— ``local_read(fresh=True)`` ⇒ ``{'messages': ['old', 'new']}``。
    "fresh_view": ["old", "new"],
    #: **fresh 读的对照** —— ``local_read(fresh=False)`` ⇒ ``{'messages': ['old']}``。
    "plain_view": ["old"],
}

#: 上游基线所对应的**上游版本**（换版本 MUST 重新实测）。
UPSTREAM_BASELINE_VERSION = "1.2.11"

#: 上游侧「**节点入参**」投影的**节点名**（用于**逐节点**比对）。
NODE_INPUT_FIELD = "节点入参"
#: 上游侧「**输出状态**」投影的字段名。
OUTPUT_STATE_FIELD = "输出状态"
#: 上游侧「**事件序列**」投影的字段名。
EVENT_SEQUENCE_FIELD = "事件序列"


@dataclass(frozen=True)
class Projection:
    """一侧执行的**归一化**结果（三项投影）。"""

    node_inputs: tuple[dict[str, Any], ...]
    output_state: dict[str, Any]
    events: tuple[tuple[int, str, Any], ...]


@dataclass(frozen=True)
class FieldResult:
    """**一个**比对字段的结果（**逐字段** · FR-017 / SC-019）。"""

    field: str
    expected: Any
    actual: Any
    equal: bool


@dataclass(frozen=True)
class DiffReport:
    """**差分判定记录**（含**比对字段名** + **逐项结果**）。"""

    upstream_version: str
    results: tuple[FieldResult, ...]

    @property
    def differences(self) -> tuple[FieldResult, ...]:
        """**不一致**的字段清单（空 = 一致）。"""
        return tuple(result for result in self.results if not result.equal)

    @property
    def equal(self) -> bool:
        """三项投影是否**全部**逐项相等。"""
        return not self.differences

    def to_dict(self) -> dict[str, Any]:
        """可 JSON 序列化的投影（判定记录的落盘形态）。"""
        return {
            "upstream_version": self.upstream_version,
            "equal": self.equal,
            "results": [
                {
                    "field": result.field,
                    "expected": result.expected,
                    "actual": result.actual,
                    "equal": result.equal,
                }
                for result in self.results
            ],
        }


def run_upstream_spec(spec: GraphSpec) -> Projection:
    """在 **langgraph** 侧执行同一份图规格（**线性单链**）。

    * 图**由同一份** ``schema_typed`` 构造（FR-033 · 裁定 21）⇒
      两侧消费**同一个对象**；
    * 节点函数**同一批对象** ⇒ **节点入参**的观测方式**两侧同款**；
    * ``stream_mode=["updates", "values"]`` ⇒ 一次执行同时拿到
      **事件序列**（``updates``）与**输出状态**（最后一条 ``values``）。

    ⚠️ **输出状态取自 ``values`` 模式的最后一条**（与 ``invoke()`` 的返回值
    **同一形态**）⇒ 用 **一次** stream 拿两项投影 ⇒ **MUST NOT** 再跑一遍
    ``invoke()``（那会让节点**跑两次** ⇒ 观测到的入参翻倍）。

    ⚠️ **上游的「空状态」怪癖（实测 · 2026-11-10）**：上游在**整个状态为空**时
    **不产出**状态（``invoke({})`` ⇒ ``None``；``stream`` 无 ``values`` 条目）
    ⇒ 夹具的图规格 MUST 带**至少一个**初始 key ⇒ 否则「输出状态」这一项投影
    会出现**稳定假差异**（freegraph 侧的归约型通道**有值（空值）**）。

    ⚠️ **导入 MUST 在函数体内** —— 上游及其传递依赖（``langchain-core``
    → ``langsmith``）MUST **NOT** 在**收集期**进入共享的 pytest 进程
    ⇒ 否则污染同进程的 ``sys.modules`` 观测（仓库既有教训）。
    """
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(spec.schema_typed)
    names: list[str] = []
    for name, node in spec.nodes:
        builder.add_node(name, node)
        names.append(name)
    builder.add_edge(START, names[0])
    for source, target in zip(names, names[1:]):
        builder.add_edge(source, target)
    builder.add_edge(names[-1], END)
    app = builder.compile()

    reset_observed_node_inputs()
    events: list[tuple[int, str, Any]] = []
    output_state: dict[str, Any] = {}
    for mode, chunk in app.stream(
        spec.initial_input, stream_mode=["updates", "values"]
    ):
        if mode == "updates":
            for node_name, writes in chunk.items():
                events.append((len(events), node_name, writes))
        elif mode == "values":
            output_state = dict(chunk)

    return Projection(
        node_inputs=observed_node_inputs(),
        output_state=output_state,
        events=tuple(events),
    )


def _compare_mapping(
    field_prefix: str,
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
) -> list[FieldResult]:
    """比对两个映射 ⇒ **逐字段**结果（key 集合 + 逐 key 值）。

    ⚠️ **key 的顺序不比对**（契约 §5）⇒ 只比**集合**。
    """
    results: list[FieldResult] = []
    expected_keys = set(expected)
    actual_keys = set(actual)
    results.append(
        FieldResult(
            field=f"{field_prefix}.keys",
            expected=sorted(expected_keys),
            actual=sorted(actual_keys),
            equal=expected_keys == actual_keys,
        )
    )
    for key in sorted(expected_keys | actual_keys):
        if key not in expected:
            results.append(
                FieldResult(
                    field=f"{field_prefix}[{key!r}]",
                    expected=None,
                    actual=actual[key],
                    equal=False,
                )
            )
            continue
        if key not in actual:
            results.append(
                FieldResult(
                    field=f"{field_prefix}[{key!r}]",
                    expected=expected[key],
                    actual=None,
                    equal=False,
                )
            )
            continue
        results.append(
            FieldResult(
                field=f"{field_prefix}[{key!r}]",
                expected=expected[key],
                actual=actual[key],
                equal=expected[key] == actual[key],
            )
        )
    return results


def compare_projections(
    *,
    upstream: Projection,
    freegraph: DriverResult,
    upstream_version: str,
) -> DiffReport:
    """比对两侧的**三项投影** ⇒ **逐字段**的判定记录。

    * **节点入参**（``SC-032``）—— 逐节点比对 key 集合 + 逐 key 值；
    * **输出状态**（``SC-006``）—— key 集合 + 逐 key 值；
    * **事件序列**（``SC-007``）—— 三元组序列**逐项**相等
      （**空更新 ⇒ 写入为 ``None``**）。

    ⚠️ **MUST NOT** 只写「一致」⇒ 判定记录 MUST 含**比对字段名** +
    **逐项结果**（FR-017 · SC-019）。
    """
    results: list[FieldResult] = []

    results.append(
        FieldResult(
            field=f"{NODE_INPUT_FIELD}.count",
            expected=len(freegraph.node_inputs),
            actual=len(upstream.node_inputs),
            equal=len(freegraph.node_inputs) == len(upstream.node_inputs),
        )
    )
    for index in range(max(len(freegraph.node_inputs), len(upstream.node_inputs))):
        freegraph_input = (
            freegraph.node_inputs[index]
            if index < len(freegraph.node_inputs)
            else {}
        )
        upstream_input = (
            upstream.node_inputs[index] if index < len(upstream.node_inputs) else {}
        )
        results.extend(
            _compare_mapping(
                f"{NODE_INPUT_FIELD}[{index}]",
                upstream_input,
                freegraph_input,
            )
        )

    results.extend(
        _compare_mapping(
            OUTPUT_STATE_FIELD,
            upstream.output_state,
            freegraph.output_state,
        )
    )

    results.append(
        FieldResult(
            field=f"{EVENT_SEQUENCE_FIELD}.count",
            expected=len(upstream.events),
            actual=len(freegraph.events),
            equal=len(upstream.events) == len(freegraph.events),
        )
    )
    for index in range(max(len(upstream.events), len(freegraph.events))):
        expected = upstream.events[index] if index < len(upstream.events) else None
        actual = freegraph.events[index] if index < len(freegraph.events) else None
        results.append(
            FieldResult(
                field=f"{EVENT_SEQUENCE_FIELD}[{index}]",
                expected=expected,
                actual=actual,
                equal=expected == actual,
            )
        )

    return DiffReport(upstream_version=upstream_version, results=tuple(results))


def measure_upstream_fresh_view() -> dict[str, Any]:
    """实测上游 ``local_read`` 的 **fresh 视图**与**对照视图**。

    对应 ``contracts/upstream-parity.md`` §2 的「fresh 读」基线行：
    ``fresh=True`` ⇒ ``{'messages': ['old', 'new']}`` · ``fresh=False`` ⇒
    ``{'messages': ['old']}`` · 读后**通道正式值不变**。

    ⚠️ **导入 MUST 在函数体内**（与 :func:`run_upstream_spec` 同款纪律）。
    """
    from langgraph.channels import BinaryOperatorAggregate
    from langgraph.pregel._algo import local_read

    channel = BinaryOperatorAggregate(list, operator.add)
    channel.update([["old"]])

    class _Task:
        writes = [("messages", ["new"])]

    channels = {"messages": channel}
    fresh = local_read({}, channels, {}, _Task(), ["messages"], fresh=True)
    plain = local_read({}, channels, {}, _Task(), ["messages"], fresh=False)
    return {"fresh": fresh, "plain": plain, "official": channel.get()}


def run_differential(
    spec: GraphSpec,
    upstream_version: str,
) -> DiffReport:
    """跑**一次**差分（两侧执行 + 三项投影 + 逐字段判定）。

    ⇒ **可复用的**夹具入口（FR-015 · 契约 §1）⇒ **B8F1 MUST 能直接复用**。
    """
    freegraph_result = run_freegraph_spec(spec)
    upstream_projection = run_upstream_spec(spec)
    return compare_projections(
        upstream=upstream_projection,
        freegraph=freegraph_result,
        upstream_version=upstream_version,
    )
