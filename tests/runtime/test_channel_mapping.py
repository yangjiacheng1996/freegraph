# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**映射入口**（``build_channel`` / ``build_channels``）—— B5F1 的 US4。

本文件承载的判据：

* **映射规则**（有归约器 ⇒ 归约型 · 无归约器 ⇒ 覆盖型）—— SC-008 · FR-012 ①②；
* **保序** + 每 key **恰一个**通道 —— SC-008 · FR-012 ④；
* **归约器的身份保持**（``channel.reducer is operator.add``）—— SC-008 · SC-010；
* **路由通道不由 schema 派生**（须支持直接实例化）—— SC-008 · FR-012 ③；
* **映射自洽**（标注「有归约器」但归约器为空 ⇒ 内置 ``ValueError``）——
  SC-026 · FR-025 ②。

**契约权威**：``specs/b5f1-channels/contracts/channel-contract.md`` §4。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

import pytest

from freegraph.runtime import (
    BinaryOperatorAggregate,
    ChannelSpec,
    EphemeralValue,
    LastValue,
    build_channel,
    build_channels,
    parse_state_schema,
)


class _Schema(TypedDict):
    """含一个**有归约器**的 key 与一个**无归约器**的 key。"""

    messages: Annotated[list, operator.add]
    llm_calls: int


# ── 映射规则（SC-008 · FR-012）────────────────────────────────────────────


def test_build_channels_maps_reducer_keys_to_aggregate_channels() -> None:
    """SC-008：有归约器 ⇒ ``BinaryOperatorAggregate``。"""
    spec = parse_state_schema(_Schema)
    channels = build_channels(spec)
    assert isinstance(channels["messages"], BinaryOperatorAggregate)


def test_build_channels_maps_plain_keys_to_last_value_channels() -> None:
    """SC-008：无归约器 ⇒ ``LastValue``。"""
    spec = parse_state_schema(_Schema)
    channels = build_channels(spec)
    assert isinstance(channels["llm_calls"], LastValue)


def test_build_channels_preserves_schema_key_order() -> None:
    """SC-008 / FR-012 ④：映射**保序**（键序 == ``SchemaSpec.keys`` 序）。"""
    spec = parse_state_schema(_Schema)
    channels = build_channels(spec)
    assert list(channels) == list(spec.keys)


def test_build_channels_produces_exactly_one_channel_per_key() -> None:
    """SC-008 / FR-012 ④：通道数 == schema 的 key 数。"""
    spec = parse_state_schema(_Schema)
    channels = build_channels(spec)
    assert len(channels) == len(spec.keys)


def test_build_channels_keeps_the_reducer_reference() -> None:
    """SC-008 / SC-010 / I-18：归约型通道的 ``reducer`` **就是**规格里的引用。"""
    spec = parse_state_schema(_Schema)
    channels = build_channels(spec)
    assert channels["messages"].reducer is operator.add
    assert channels["messages"].reducer is spec.channels["messages"].reducer


def test_build_channel_maps_a_single_spec() -> None:
    """SC-008 / FR-012 ①：``build_channel(spec)`` ⇒ 一个通道实例。"""
    spec = parse_state_schema(_Schema)
    channel = build_channel(spec.channels["llm_calls"])
    assert isinstance(channel, LastValue)
    assert channel.key == "llm_calls"


def test_build_channel_keeps_the_reducer_reference() -> None:
    """SC-008 / FR-014：``build_channel`` 产出的归约器是**同一引用**。"""
    spec = parse_state_schema(_Schema)
    channel = build_channel(spec.channels["messages"])
    assert isinstance(channel, BinaryOperatorAggregate)
    assert channel.reducer is operator.add


def test_build_channel_preserves_the_spec_value_type() -> None:
    """FR-012 ① / FR-002：通道的 ``value_type`` == 规格的 ``value_type``。"""
    spec = parse_state_schema(_Schema)
    channel = build_channel(spec.channels["llm_calls"])
    assert channel.value_type is spec.channels["llm_calls"].value_type


# ── 路由通道与映射自洽（SC-008 · SC-026）──────────────────────────────────


def test_ephemeral_value_is_not_derived_from_a_schema() -> None:
    """SC-008 / FR-012 ③ / M-2：路由通道**不由** schema 派生 ⇒ 须支持
    **直接实例化**。"""
    spec = parse_state_schema(_Schema)
    channels = build_channels(spec)
    assert not any(isinstance(channel, EphemeralValue) for channel in channels.values())
    route = EphemeralValue("route", str)
    assert route.key == "route"


def test_build_channel_rejects_a_spec_with_an_empty_reducer() -> None:
    """SC-026 / FR-025 ② / M-3：标注「有归约器」但归约器为**空**
    ⇒ 内置 ``ValueError``（MUST **NOT** 新增错误类型）。"""
    spec = ChannelSpec(
        key="messages",
        value_type=list,
        reducer=None,
        has_reducer=True,
        semantics="reduce",
    )
    with pytest.raises(ValueError):
        build_channel(spec)


def test_build_channels_returns_a_mutable_dict() -> None:
    """契约 §4：``build_channels`` 返回**可变** ``dict``
    （下游 B5F2 / B7F1 要在其上**增补内部通道** · research D-14）。"""
    spec = parse_state_schema(_Schema)
    channels = build_channels(spec)
    assert isinstance(channels, dict)
    channels["__internal__"] = EphemeralValue("__internal__", str)
    assert "__internal__" in channels
