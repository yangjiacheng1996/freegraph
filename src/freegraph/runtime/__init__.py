# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 的 **L2 执行内核层** —— 状态 schema 解析 · 通道实现。

本包承载四个 feature 的交付物：

**B4F1（状态 schema 解析）**

* :func:`freegraph.runtime.parse_state_schema` —— **唯一**解析入口
  （把标准 ``TypedDict`` 状态 schema 翻译成通道规格集）；
* :class:`freegraph.runtime.ChannelSpec` / :class:`freegraph.runtime.SchemaSpec`
  —— 不可变的**纯数据**解析产物；
* :class:`freegraph.runtime.InvalidSchemaError` —— 非法 schema 的
  **显式失败**信号（结构化字段 ``key`` + ``reason``）。

**B5F1（通道实现）**

* :class:`freegraph.runtime.Channel` —— 通道**抽象基类**（状态读写的
  **唯一**实现单元）；
* :class:`freegraph.runtime.LastValue` —— **覆盖型**通道（C3 · 无归约器 ⇒ 覆盖）；
* :class:`freegraph.runtime.BinaryOperatorAggregate` —— **归约型**通道
  （C2 · 有归约器 ⇒ ``reducer(current, new)``）；
* :class:`freegraph.runtime.EphemeralValue` —— **路由型**通道
  （C7 / C8 · **步末只清「本轮未被写入的」路由型通道** —— FR-014 · 裁定 10）；
* :func:`freegraph.runtime.build_channel` /
  :func:`freegraph.runtime.build_channels` —— **schema → 通道**的**唯一**
  映射入口；
* :class:`freegraph.runtime.EmptyChannelError` /
  :class:`freegraph.runtime.InvalidChannelUpdateError` —— 通道层的两个
  **显式失败**信号（结构化字段 ``key`` / ``received_count`` /
  ``expected_count``）。

**B5F2（状态读取）**

* :func:`freegraph.runtime.read_channels` —— **稀疏读**：只返回「**当前有值**」
  的通道（**C4** 的载荷 · 无值通道的 key **MUST NOT** 出现）；
* :func:`freegraph.runtime.local_read` —— 「**当前值 + 本任务本次写入**」的
  视图（``fresh=True`` ⇒ C8 的读取原语）· **零污染**（通道的**绑定与可用性
  判定**读取前后**不变**）。

**B7F1（调度内核 · super-step）**

* :class:`freegraph.runtime.GraphSpec` —— **手写图规格**（通道映射 + **保序**
  节点表 + 边表 + **预留的条件边字段**）· 校验在**构造时**执行；
* :class:`freegraph.runtime.NodeSpec` —— **节点规格**（订阅集**既管触发、也管
  入参** · 节点函数 ``f(state: dict) -> dict``）；
* :class:`freegraph.runtime.SchedulerState` —— **调度状态**（「已消费版本」+
  轮次计数 · **由调用方持有** ⇒ 同一份图规格可安全跑多次）；
* :class:`freegraph.runtime.SuperStepResult` —— **单轮结果**（执行记录 /
  待写入 / 合并后状态 / 轮数 · 五阶段产物**逐项可观测**）；
* :func:`freegraph.runtime.run_super_step` —— **单轮入口**（跑**一轮**
  super-step）；
* :func:`freegraph.runtime.run_super_steps` —— **多轮入口**（跑到收敛或触到
  步数上限 · 缺省 **25**）。

⚠️ **本包是 L2 内部 API，不是公开门面**——用户**可以** import，但
freegraph **不承诺**其稳定性。由 **B5F2**（读取层）· **B6F1**
（``StateGraph`` 构建器）· **B7F1**（调度层）消费。

**B10F1（中断 / 恢复）**

* :func:`freegraph.runtime.run_graph` —— **图级入口**（首次运行 / 恢复 ·
  返回 ``SuperStepResult | InterruptResult``）；
* :class:`freegraph.runtime.InterruptResult` —— **挂起态**的结果对象
  （**4 字段** · ``state`` / ``interrupts`` / ``executed`` / ``steps``）；
* :class:`freegraph.runtime.InterruptError` —— 中断 / 恢复路径的**失败信号**
  （**封闭 5 码**的 ``reason`` 原因码）。

⚠️ **``interrupt()`` 的实现体**在 **私有**模块 ``freegraph.runtime._interrupt``
⇒ ⇒ **不进**本包的 ``__all__`` ⇒ ⇒ 不进 API 兼容矩阵（同 B12F1 的
``_concurrency.py`` **同款**）。

**零新增公开 API**：契约层仍 **20** 个符号、门面仍 **7** 个
（SC-012 · FR-018）⇒ 本包的导出**不进** API 兼容矩阵
（沿用 B4F1 裁定 6 ③：「``freegraph.runtime`` 的导出属 L2 内部 API」）。

**顶层包惰性**（G1 / L-1）：``src/freegraph/__init__.py`` MUST NOT import
本包 ⇒ ``import freegraph`` 不会连带加载它（quickstart §6 的判据）。

**层纪律**（FR-016 · ARCH-1）：本包属 **L2**，只向下依赖 **L1**
（``freegraph.contracts``），MUST NOT import L3 / L4 / L5。

**依赖纪律**（FR-015）：本包只依赖**标准库**；MUST NOT import
``langchain*`` / ``langgraph*`` / ``langsmith`` / ``pydantic`` /
``typing_extensions``。
"""

from __future__ import annotations

from .channel import BinaryOperatorAggregate, Channel, EphemeralValue, LastValue
from .errors import (
    EmptyChannelError,
    InterruptError,
    InvalidChannelUpdateError,
    InvalidSchemaError,
)
from .mapping import build_channel, build_channels
from .read import local_read, read_channels
from .schema import ChannelSpec, SchemaSpec, parse_state_schema
from .superstep import (
    GraphSpec,
    InterruptResult,
    NodeSpec,
    SchedulerState,
    SuperStepResult,
    run_graph,
    run_super_step,
    run_super_steps,
)

__all__ = [
    "BinaryOperatorAggregate",
    "Channel",
    "ChannelSpec",
    "EmptyChannelError",
    "EphemeralValue",
    "GraphSpec",
    "InterruptError",
    "InterruptResult",
    "InvalidChannelUpdateError",
    "InvalidSchemaError",
    "LastValue",
    "NodeSpec",
    "SchedulerState",
    "SchemaSpec",
    "SuperStepResult",
    "build_channel",
    "build_channels",
    "local_read",
    "parse_state_schema",
    "read_channels",
    "run_graph",
    "run_super_step",
    "run_super_steps",
]
