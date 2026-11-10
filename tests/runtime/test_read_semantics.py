# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**稀疏读**的语义用例 —— 属 **B5F2**（tasks T013 / T015 / T017）。

覆盖的判定（``contracts/read-contract.md`` §2 与 §4）：

* **I-1** 结果 key 集合 == 「``is_available()`` 为真」的通道集合；
* **I-2** 结果 key **顺序** == 入参映射顺序（过滤后）；
* **I-3** ``type(result) is dict``（**逐字** · MUST NOT 降级为「是 dict 的实例」）；
* **I-4** 结果里的值与通道当前值**同一对象**（``is``）；
* **I-10** 「**值为 ``None``**」的通道**出现**在结果里；
* **§2.3** ``skip_empty=False`` 读到无值 ⇒ 抛 ``EmptyChannelError``；
* **§2.1** 省略 ``skip_empty`` 与显式 ``skip_empty=True`` 的结果**逐字相等**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

import pytest

from freegraph.runtime import (
    EmptyChannelError,
    LastValue,
    build_channels,
    parse_state_schema,
    read_channels,
)


class MixedSchema(TypedDict):
    """被测 schema（**有归约器** + **无归约器** + **从未写入**各一）。"""

    messages: Annotated[list, operator.add]
    llm_calls: int
    never_written: str


def _channels() -> dict:
    """构造一份手写通道状态（**已写入** + **从未写入**各一）。"""
    channels = build_channels(parse_state_schema(MixedSchema))
    channels["messages"].update([["hi"]])
    return channels


# ── T013 · 稀疏语义（I-1 / I-10 / §2.3 / §2.1）────────────────────────


def test_result_key_set_equals_the_available_channel_set() -> None:
    """**I-1**：结果 key 集合 == 「``is_available()`` 为真」的通道集合。"""
    channels = _channels()

    result = read_channels(channels)

    expected = {key for key, channel in channels.items() if channel.is_available()}
    assert set(result) == expected
    assert "never_written" not in result
    assert "llm_calls" not in result
    assert "messages" in result


def test_channel_holding_none_is_present_in_the_result() -> None:
    """**I-10**：「**值为 ``None``**」的通道**出现**在结果里（值为 ``None``）。

    ⚠️ 「值为 ``None``」≠「无值」⇒ MUST NOT 被稀疏判据排除。
    """
    channels = _channels()
    channels["llm_calls"].update([None])

    result = read_channels(channels)

    assert "llm_calls" in result
    assert result["llm_calls"] is None


def test_skip_empty_false_raises_empty_channel_error_for_the_empty_key() -> None:
    """**§2.3**：``skip_empty=False`` 读到无值 ⇒ 抛 ``EmptyChannelError``。

    错误对象的 ``key`` MUST 指向那个 key ⇒ MUST **NOT** 以 ``None`` 冒充「有值」。
    ⚠️ 抛的是**映射顺序里的第一个**无值通道（``llm_calls`` —— ``never_written``
    排在其后）⇒ 该断言同时守住 **I-2** 的「按入参映射顺序遍历」。
    """
    channels = _channels()

    with pytest.raises(EmptyChannelError) as excinfo:
        read_channels(channels, skip_empty=False)

    assert excinfo.value.key == "llm_calls"


def test_omitting_skip_empty_equals_explicit_true() -> None:
    """**§2.1**：省略 ``skip_empty`` 与显式 ``skip_empty=True`` 结果**逐字相等**。"""
    channels = _channels()

    assert read_channels(channels) == read_channels(channels, skip_empty=True)
    assert list(read_channels(channels)) == list(read_channels(channels, skip_empty=True))


def test_empty_string_channel_key_is_kept_as_a_plain_dict_key() -> None:
    """**Edge Case ①**：通道 key 为**空串** ⇒ MUST 照常作为 ``dict`` 的一个 key 出现。"""
    channels = _channels()
    channels[""] = LastValue(key="", value_type=str)
    channels[""].update(["空串键的值"])

    result = read_channels(channels)

    assert "" in result
    assert result[""] == "空串键的值"


def test_key_outside_the_schema_is_still_read() -> None:
    """**Edge Case ②**：映射里有**不在 schema 里**的 key ⇒ 读取层**照常读取**。

    ⚠️ 读取层 MUST **NOT** 做 schema 校验（那是 **B4F1** 的职责）⇒
    该 key 若「无值」则在 ``skip_empty=True`` 下被跳过。
    """
    channels = _channels()
    channels["outside_schema"] = LastValue(key="outside_schema", value_type=int)
    channels["outside_schema"].update([42])

    result = read_channels(channels)

    assert result["outside_schema"] == 42


def test_empty_mapping_returns_an_empty_dict() -> None:
    """**Edge Case ③**：``read_channels({})`` ⇒ MUST 返回**空 ``dict``**。

    ⇒ **不是** ``None``、**不**抛错。
    """
    result = read_channels({})

    assert type(result) is dict
    assert result == {}


def test_non_mapping_argument_raises_type_error() -> None:
    """契约 §1.1：入参**非映射** ⇒ MUST 抛 ``TypeError``（**显式失败**）。"""
    with pytest.raises(TypeError):
        read_channels([("messages", "not-a-channel")])  # type: ignore[arg-type]


# ── T015 · 结果形态（I-3 / I-4 / I-2）─────────────────────────────────


def test_result_is_exactly_a_plain_dict() -> None:
    """**I-3**：``type(result) is dict`` **逐字**（MUST NOT 是 ``dict`` 的子类）。"""
    result = read_channels(_channels())

    assert type(result) is dict


def test_result_values_are_the_very_same_objects_as_the_channel_values() -> None:
    """**I-4**：结果里的每个值与通道当前值**同一对象**（``is``）。

    ⇒ 值**按引用**（MUST **NOT** 深拷贝 —— 深拷贝会破坏对象身份且对不可拷贝
    对象会失败）。
    """
    channels = _channels()

    result = read_channels(channels)

    for key, channel in channels.items():
        if key in result:
            assert result[key] is channel.get()


def test_mutating_the_result_key_set_does_not_affect_channel_state() -> None:
    """契约 §2.1：改结果 ``dict`` 的**键集合** **不影响**通道状态。

    ⇒ 结果 MUST 是**新建**的 ``dict``（MUST NOT 把内部映射交出去）。
    """
    channels = _channels()

    result = read_channels(channels)
    result["injected"] = "凭空出现的 key"
    del result["messages"]

    assert "injected" not in channels
    assert "messages" in channels
    assert channels["messages"].get() == ["hi"]


def test_result_key_order_follows_the_input_mapping_order() -> None:
    """**I-2**：结果 ``dict`` 的 key **顺序** == 入参映射顺序（过滤后）。"""
    channels = _channels()

    result = read_channels(channels)

    assert list(result) == ["messages"]
    assert list(result) == [
        key for key in channels if key in result
    ]


def test_result_key_order_is_the_mapping_order_not_the_sorted_order() -> None:
    """**I-2** 的**反证**：结果顺序 MUST NOT 是**排序后**的顺序。

    ⇒ 故意让入参映射的 key 顺序与**字母序**不同 ⇒ 若实现偷偷排序则本用例红。
    """
    channels = {
        "zebra": LastValue(key="zebra", value_type=int),
        "alpha": LastValue(key="alpha", value_type=int),
        "middle": LastValue(key="middle", value_type=int),
    }
    for channel in channels.values():
        channel.update([1])

    result = read_channels(channels)

    assert list(result) == ["zebra", "alpha", "middle"]


# ── T017 · 浅引用的**已知面**（与上游同构 · research D-08 / D-10 / DR-4）──


def test_in_place_mutation_of_the_value_object_is_visible_on_the_channel() -> None:
    """**已知面**：就地修改结果里的**值对象** **会**影响通道的当前值。

    ⚠️ 这与**上游同构**（上游 ``checkpoint()`` 亦返回同一对象）⇒
    **断言写明该行为**，MUST **NOT** 去修它（读取层 MUST **NOT** 深拷贝）。
    """
    channels = _channels()

    result = read_channels(channels)
    result["messages"].append("就地追加")

    assert channels["messages"].get() == ["hi", "就地追加"]

