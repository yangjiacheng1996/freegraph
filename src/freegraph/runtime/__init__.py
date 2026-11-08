# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 的 **L2 执行内核层** —— 状态 schema 解析 · 属 **B4F1**。

本包承载 B4F1 的交付物：

* :func:`freegraph.runtime.parse_state_schema` —— **唯一**解析入口
  （把标准 ``TypedDict`` 状态 schema 翻译成通道规格集）；
* :class:`freegraph.runtime.ChannelSpec` / :class:`freegraph.runtime.SchemaSpec`
  —— 不可变的**纯数据**解析产物；
* :class:`freegraph.runtime.InvalidSchemaError` —— 非法 schema 的
  **显式失败**信号（结构化字段 ``key`` + ``reason``）。

⚠️ **本包是 L2 内部 API，不是公开门面**——用户**可以** import，但
freegraph **不承诺**其稳定性。由 **B5F1**（通道实现）与 **B6F1**
（``StateGraph`` 构建器）消费。

**零新增公开 API**：契约层仍 **18** 个符号、门面仍 **7** 个
（SC-015 · FR-015）⇒ 本包的导出**不进** API 兼容矩阵。

**顶层包惰性**（G1 / L-1）：``src/freegraph/__init__.py`` MUST NOT import
本包 ⇒ ``import freegraph`` 不会连带加载它（quickstart §8.1 的判据）。

**层纪律**（FR-014 · ARCH-1）：本包属 **L2**，只向下依赖 **L1**
（``freegraph.contracts``），MUST NOT import L3 / L4 / L5。

**依赖纪律**（FR-013）：本包只依赖**标准库**；MUST NOT import
``langchain*`` / ``langgraph*`` / ``langsmith`` / ``pydantic`` /
``typing_extensions``。
"""

from __future__ import annotations

from .errors import InvalidSchemaError
from .schema import ChannelSpec, SchemaSpec, parse_state_schema

__all__ = [
    "ChannelSpec",
    "SchemaSpec",
    "InvalidSchemaError",
    "parse_state_schema",
]
