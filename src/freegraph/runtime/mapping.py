# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**schema → 通道的映射入口** —— 属 **B5F1**。

本模块是**唯一** import B4F1 ``ChannelSpec`` / ``SchemaSpec`` 的地方 ⇒
下游（**B6F1** 的 ``StateGraph`` 构建器）只需 import 这一个模块，
不必碰通道实现细节。

**契约权威**：``specs/b5f1-channels/contracts/channel-contract.md`` §4
（映射契约 M-1…M-4）。

**两条映射规则**（FR-012 · 契约 §4）：

* 通道规格标注「**有归约器**」⇒ ``BinaryOperatorAggregate``
  （归约器**同一引用** · **身份**判定 · FR-014）；
* 通道规格标注「**无归约器**」⇒ ``LastValue``。

⚠️ **路由通道不由 schema 派生**（FR-012 ③ · M-2）⇒ ``EphemeralValue``
MUST 支持**直接实例化**（本模块**不**提供它的派生入口 —— 那是**故意**的：
路由通道不是 schema key）。

**上游对照**（``langgraph 1.2.11`` · 契约 ``upstream-parity`` **S-04**）：
``graph/state.py:1850-1873``（``_get_channel``）—— 先剥 ``Required`` /
``NotRequired`` → 有归约器走 ``_is_field_binop`` → 否则 ``LastValue`` 兜底。

**依赖纪律**（FR-015 · FR-016）：本模块只 import **同层**（L2）的
``schema`` / ``channel`` 模块 ⇒ **不**引入新的层间依赖。
"""

from __future__ import annotations

from .channel import BinaryOperatorAggregate, Channel, LastValue
from .schema import ChannelSpec, SchemaSpec

__all__ = [
    "build_channel",
    "build_channels",
]


def build_channel(spec: ChannelSpec) -> Channel:
    """把**一个**通道规格映射成一个通道实例（FR-012 · 契约 §4）。

    * 规格 ``has_reducer`` 为真 ⇒ ``BinaryOperatorAggregate``
      （归约器**同一引用** · FR-014）；
    * 否则 ⇒ ``LastValue``。

    ⚠️ 规格标注「有归约器」但归约器为**空** ⇒ 抛**内置** ``ValueError``
    （FR-025 ② · M-3 · E-5）—— MUST **NOT** 新增 L2 错误类型承载它。

    **纯函数**（FR-015）：不读环境变量 · 不出站 · 不写文件 · 构造**无副作用**。
    """
    if spec.has_reducer:
        if spec.reducer is None:
            raise ValueError(
                f"Channel {spec.key!r} is declared with a reducer but the "
                "reducer is empty"
            )
        return BinaryOperatorAggregate(
            key=spec.key,
            value_type=spec.value_type,
            reducer=spec.reducer,
        )
    return LastValue(key=spec.key, value_type=spec.value_type)


def build_channels(schema_spec: SchemaSpec) -> dict[str, Channel]:
    """把**一份**通道规格集映射成「key → 通道」的**保序**映射（FR-012 · 契约 §4）。

    * 按 ``schema_spec.keys`` **保序**遍历 ⇒ 每个 key **恰一个**通道
      （FR-012 ④ · M-4）；
    * 返回**可变** ``dict``（research **D-14**）—— 下游 **B5F2** / **B7F1**
      要在其上**增补内部通道**（如路由通道）⇒ 不可变映射会逼调用方先拷贝。

    **纯函数**（FR-015）：不读环境变量 · 不出站 · 不写文件。
    """
    return {
        key: build_channel(schema_spec.channels[key]) for key in schema_spec.keys
    }
