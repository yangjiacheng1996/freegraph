# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 的 **L2 执行内核层** —— 状态 schema 解析 · 通道实现。

本包承载三个 feature 的交付物：

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
  （C7 / C8 · 每 super-step 清空）；
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

⚠️ **本包是 L2 内部 API，不是公开门面**——用户**可以** import，但
freegraph **不承诺**其稳定性。由 **B5F2**（读取层）· **B6F1**
（``StateGraph`` 构建器）· **B7F1**（调度层）消费。

**零新增公开 API**：契约层仍 **18** 个符号、门面仍 **7** 个
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
from .errors import EmptyChannelError, InvalidChannelUpdateError, InvalidSchemaError
from .mapping import build_channel, build_channels
from .read import local_read, read_channels
from .schema import ChannelSpec, SchemaSpec, parse_state_schema

__all__ = [
    "BinaryOperatorAggregate",
    "Channel",
    "ChannelSpec",
    "EmptyChannelError",
    "EphemeralValue",
    "InvalidChannelUpdateError",
    "InvalidSchemaError",
    "LastValue",
    "SchemaSpec",
    "build_channel",
    "build_channels",
    "local_read",
    "parse_state_schema",
    "read_channels",
]
