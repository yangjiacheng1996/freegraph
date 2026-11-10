# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 侧的**规格驱动器** —— 属 **B5F2**（tasks T020 / T046）。

**契约权威**：``specs/b5f2-sparse-state-read/contracts/differential-fixture.md``
§3（三项投影的口径）。

⚠️ **本模块 MUST NOT 含调度逻辑**（裁定 6 · FR-024）—— 它只是「测试侧的替身」：
线性单链（按 ``nodes`` 顺序串行）· 只用 **B5F1 通道层 + B5F2 读取层** ⇒
**不含**触发判定 / 分支路由 / 版本号 / 并发（调度循环属 **B7F1**）。

**节点入参的观测方式**（FR-030 · 裁定 17）：在**节点函数内部**把收到的字典
**复制一份**留存，且该副本 MUST 取自**节点执行前**（节点就地改写入参时，
观测到的仍是**原始入参**）⇒ 由 :func:`record_node_input` 承担 ——
**两侧的节点函数是同一个对象** ⇒ **两侧 MUST 以同一方式观测**。

**「节点返回值 → 通道写入」的最小合并**（T046 · FR-014 / FR-024）：
节点函数返回的部分状态 MUST 按通道**自身的写入语义**写入通道
（覆盖型 = 覆盖 · 归约型 = 通道无值时**直存首值**（不调归约器 · B5F1 裁定 4）
+ 其余按序归约 · 路由型 = 同覆盖型）⇒ 复用 ``Channel.update()``
⇒ **MUST NOT** 在本模块另写一份归约逻辑。

⚠️ 该「最小合并」= **一次写入**的模拟 ⇒ MUST **NOT** 长成第二个调度器。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from freegraph.runtime import build_channels, parse_state_schema, read_channels

from .spec_builder import GraphSpec, check_node_output

__all__ = [
    "DriverResult",
    "observed_node_inputs",
    "record_node_input",
    "reset_observed_node_inputs",
    "run_freegraph_spec",
]

#: **节点入参**的观测槽（**节点函数内部**调用 :func:`record_node_input` 写入）。
_OBSERVED_NODE_INPUTS: list[dict[str, Any]] = []


def record_node_input(state: Mapping[str, Any]) -> None:
    """在**节点函数内部**调用 —— 把收到的字典**复制一份**留存。

    副本 MUST 取自**节点执行前**（FR-030 · 裁定 17）⇒ 节点就地改写入参时，
    观测到的仍是**原始入参**。

    ⚠️ **两侧的节点函数是同一个对象** ⇒ 观测方式**两侧同款** ⇒
    「节点入参」这一项投影可比（契约 §3.1）。
    """
    _OBSERVED_NODE_INPUTS.append(dict(state))


def reset_observed_node_inputs() -> None:
    """清空观测槽（**每次执行前** MUST 调用一次）。"""
    _OBSERVED_NODE_INPUTS.clear()


def observed_node_inputs() -> tuple[dict[str, Any], ...]:
    """取回本次执行观测到的**节点入参**（按执行顺序）。"""
    return tuple(_OBSERVED_NODE_INPUTS)


@dataclass(frozen=True)
class DriverResult:
    """**规格驱动器**的执行结果（三项投影的 freegraph 侧）。

    * ``node_inputs`` —— 每个节点观测到的**入参**（**执行前**的副本）；
    * ``output_state`` —— 终态（**稀疏** · 无值 key **缺席**）；
    * ``events`` —— ``[(步序, 节点名, 写入)]``（**写入** = 节点函数返回的
      部分状态 · **原样 · 未归约** · **无更新 ⇒ ``None``**）。
    """

    node_inputs: tuple[dict[str, Any], ...]
    output_state: dict[str, Any]
    events: tuple[tuple[int, str, Any], ...]


def write_values(channels: dict[str, Any], values: Mapping[str, Any]) -> None:
    """把「部分状态」按通道**自身的写入语义**写入通道。

    * **一次写入**的模拟 ⇒ 每个 key 调**一次** ``update([value])``；
    * 覆盖型 ⇒ 覆盖 · 归约型 ⇒ 通道无值时**直存首值**（不调归约器）
      + 其余按序归约 · 路由型 ⇒ 同覆盖型
      ⇒ **MUST NOT** 在本模块另写一份归约逻辑；
    * 空序列 ⇒ 无操作。
    """
    for key, value in values.items():
        channels[key].update([value])


def run_freegraph_spec(spec: GraphSpec) -> DriverResult:
    """在 freegraph 侧执行一份图规格（**线性单链** · **无调度逻辑**）。

    流程：

    ① 用 **B4F1 的解析入口** + **B5F1 的映射入口**建通道；
    ② **初始输入**按「**一次写入**」进通道（FR-029 · 裁定 16）；
    ③ 逐个节点（按 ``nodes`` 顺序串行）：

       * **读取层**产出节点的**入参**（**稀疏** · B5F2 的读取层）；
       * 节点函数**返回**部分状态 ⇒ **校验**（schema 之外的 key ⇒ 显式失败）；
       * 记一条**事件**（``(步序, 节点名, 写入)`` · **无更新 ⇒ ``None``**）；
       * **最小合并** ⇒ 把返回值写入通道。

    ④ **终态** = 读取层再读一次（**稀疏**）。

    ⚠️ **节点返回值与归约器不兼容时** ⇒ 错误**向上传播**且通道正式值**不变**
    ⇒ 通道在**失败的写入**前后的**绑定与可用性判定不变**。
    """
    channels = build_channels(parse_state_schema(spec.schema_typed))
    write_values(channels, spec.initial_input)

    reset_observed_node_inputs()
    events: list[tuple[int, str, Any]] = []
    for step, (name, node) in enumerate(spec.nodes):
        state = read_channels(channels)
        output = check_node_output(spec, name, node(state))
        events.append((step, name, dict(output) if output else None))
        write_values(channels, output)

    return DriverResult(
        node_inputs=observed_node_inputs(),
        output_state=read_channels(channels),
        events=tuple(events),
    )
