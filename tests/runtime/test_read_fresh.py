# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**fresh 读**的用例 —— 属 **B5F2**（tasks T023）。

覆盖的判定（``contracts/read-contract.md`` §3 与 §4）：

* **§3.2** 合并语义 MUST 走通道**自身的**写入语义（**MUST NOT** 在读取层
  另写一份归约逻辑）；
* **§3.3** **零污染**（作用域 = **绑定与可用性判定** —— ``is_available()`` 的
  **结果** + ``get()`` 的**取值**）⇒ 读取前后**不变**；
* **§4 I-11** 两个稀疏入口（``read_channels`` 与 ``local_read(..., fresh=False)``）
  的结果 **MUST 逐字相等**（spec **FR-038** / **SC-033**）。

⚠️ **已知面（**MUST NOT** 计入零污染判据 · **MUST NOT** 修）**：**就地修改型**
归约器（如 ``a.extend(b)`` 一类）会**改写原通道的值对象**（副本与原通道
**浅共享值对象**）⇒ 与**上游同构**（research **D-10** / **DR-4**）⇒ 本文件
**断言写明**该行为。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

import pytest

from freegraph.runtime import (
    BinaryOperatorAggregate,
    EphemeralValue,
    InvalidChannelUpdateError,
    LastValue,
    build_channels,
    local_read,
    parse_state_schema,
    read_channels,
)


class FreshSchema(TypedDict):
    """被测 schema（**有归约器** + **无归约器**各一）。"""

    messages: Annotated[list, operator.add]
    llm_calls: int


def _channels() -> dict:
    """构造一份手写通道状态（``messages`` 已写入 · ``llm_calls`` 从未写入）。"""
    channels = build_channels(parse_state_schema(FreshSchema))
    channels["messages"].update([["old"]])
    return channels


def _snapshot(channels: dict) -> list[tuple[str, bool, object]]:
    """给每个通道拍一张「**绑定与可用性判定**」的快照。

    快照内容 = ``(key, is_available() 的结果, get() 的取值)`` ——
    这正是**零污染**判据的**作用域**（契约 §3.3 · FR-009 · 裁定 29）。
    """
    snapshot: list[tuple[str, bool, object]] = []
    for key, channel in channels.items():
        available = channel.is_available()
        snapshot.append((key, available, channel.get() if available else None))
    return snapshot


# ── §3.2 · 合并语义 ───────────────────────────────────────────────────


def test_fresh_view_contains_this_writes_values() -> None:
    """**§3.2**：``fresh=True`` 的视图**含**本次写入。"""
    channels = _channels()

    view = local_read(channels, {"messages": [["new"]]}, fresh=True)

    assert view["messages"] == ["old", "new"]


def test_reducing_channel_fresh_view_equals_the_reduced_result() -> None:
    """**§3.2**：归约型通道的 fresh 视图 == **归约后**的结果。"""
    channels = _channels()

    view = local_read(channels, {"messages": [["new"]]}, fresh=True)

    assert view["messages"] == ["old", "new"]


def test_non_fresh_view_does_not_contain_this_writes_values() -> None:
    """**§3.1**：``fresh=False`` 的视图**不含**本次写入。"""
    channels = _channels()

    view = local_read(channels, {"messages": [["new"]]}, fresh=False)

    assert view["messages"] == ["old"]


def test_fresh_view_of_a_channel_without_a_value_shows_the_written_value() -> None:
    """**§3.2**：覆盖型通道**无值** + 1 个写入 ⇒ 视图里该写入值**出现**。"""
    channels = _channels()

    view = local_read(channels, {"llm_calls": [7]}, fresh=True)

    assert view["llm_calls"] == 7


def test_unknown_write_key_raises_invalid_channel_update_error() -> None:
    """**§3.2**：待写入的**未知 key** ⇒ 抛**既有的** ``InvalidChannelUpdateError``。

    错误的 ``key`` MUST 指向那个未知 key ⇒ MUST **NOT** 新增错误类型
    ⇒ MUST **NOT** 静默丢弃（与上游的偏离 · 立项书 C6）。
    """
    channels = _channels()

    with pytest.raises(InvalidChannelUpdateError) as excinfo:
        local_read(channels, {"not_in_channels": [1]}, fresh=True)

    assert excinfo.value.key == "not_in_channels"


def test_unknown_write_key_with_a_non_sequence_value_still_fails_explicitly() -> None:
    """**§3.2**：未知 key 的待写入值**不可取长**时 ⇒ 仍**显式失败**。

    ⚠️ 错误对象 **MUST NOT** 携带用户写入的**值本身**（B5F1 FR-017 ⑥）⇒
    ``received_count`` 按 **1** 计（不可取长时）。
    """
    channels = _channels()

    with pytest.raises(InvalidChannelUpdateError) as excinfo:
        local_read(channels, {"not_in_channels": 42}, fresh=True)

    assert excinfo.value.key == "not_in_channels"
    assert excinfo.value.received_count == 1


def test_reducer_failure_propagates_and_leaves_the_channel_unchanged() -> None:
    """**§3.2**：归约器在合并中抛错 ⇒ 错误**向上传播**，通道正式值**不变**。"""

    def boom(current: list, new: list) -> list:
        if new == ["new"]:
            raise RuntimeError("归约器炸了")
        return current + new

    channels = {
        "messages": BinaryOperatorAggregate(
            key="messages", value_type=list, reducer=boom
        ),
    }
    channels["messages"].update([["old"]])

    with pytest.raises(RuntimeError, match="归约器炸了"):
        local_read(channels, {"messages": [["new"]]}, fresh=True)

    assert channels["messages"].get() == ["old"]


# ── §3.3 · 零污染（作用域 = 绑定与可用性判定）─────────────────────────


def test_binding_and_availability_are_unchanged_by_a_fresh_read() -> None:
    """**§3.3 / I-5**：读取**前后**通道的**绑定与可用性判定****不变**。

    作用域 = ``is_available()`` 的**结果** + ``get()`` 的**取值**。
    """
    channels = _channels()
    before = _snapshot(channels)

    local_read(channels, {"messages": [["new"]]}, fresh=True)

    assert _snapshot(channels) == before


def test_binding_and_availability_are_unchanged_by_a_non_fresh_read() -> None:
    """**§3.3 / I-5**：**非** fresh 读同样**零污染**。"""
    channels = _channels()
    before = _snapshot(channels)

    local_read(channels, {"messages": [["new"]]}, fresh=False)

    assert _snapshot(channels) == before


def test_in_place_mutating_reducer_rewrites_the_original_value_object() -> None:
    """**已知面**：**就地修改型**归约器 ⇒ 原通道的**值对象被改写**。

    ⚠️ **MUST NOT** 计入「零污染」判据（作用域只覆盖**绑定与可用性判定**）·
    **MUST NOT** 由读取层修复（**深拷贝**会破坏 FR-005 的对象身份语义、
    对不可拷贝对象**会失败**、且与**上游分叉**）⇒ 与**上游同构**
    （research **D-10** / **DR-4**）⇒ 本用例**断言写明**该行为。
    """

    def extend_in_place(current: list, new: list) -> list:
        current.extend(new)
        return current

    channels = {
        "messages": BinaryOperatorAggregate(
            key="messages", value_type=list, reducer=extend_in_place
        ),
    }
    channels["messages"].update([["old"]])

    local_read(channels, {"messages": [["new"]]}, fresh=True)

    assert channels["messages"].get() == ["old", "new"]
    assert channels["messages"].is_available() is True


# ── §4 I-11 · 两个稀疏入口 MUST 逐字相等（FR-038 / SC-033）────────────


def test_the_two_sparse_entries_are_byte_identical() -> None:
    """**I-11**：``read_channels(channels)`` 与 ``local_read(channels, {})``
    的结果 **MUST 逐字相等**（key 集合 + key **顺序** + 逐 key 值**同一对象**）。

    ⇒ 「**稀疏**读」只有**一处**实现 ⇒ 二者若出现差异 ⇒ 判为**语义分叉缺陷**。
    """
    channels = _channels()

    direct = read_channels(channels)
    via_local = local_read(channels, {}, fresh=False)

    assert via_local == direct
    assert list(via_local) == list(direct)
    for key in direct:
        assert via_local[key] is direct[key]


def test_empty_writes_mapping_returns_the_same_view_as_a_non_fresh_read() -> None:
    """**Edge Case ④**：``local_read`` 的**待写入映射为空** ⇒ MUST 返回与
    「**非** fresh 读」**逐字相等**的视图。"""
    channels = _channels()

    assert local_read(channels, {}, fresh=True) == local_read(
        channels, {}, fresh=False
    )


# ── Edge Case ⑤ / ⑥ ──────────────────────────────────────────────────


def test_same_channel_read_and_written_in_one_fresh_read() -> None:
    """**Edge Case ⑤**：**同一通道**在**同一次** fresh 读里**既被读取又被写入**
    ⇒ 视图按「**先合并本次写入、再取值**」计算 ⇒ 视图 == 「写入生效后的状态」
    · 而**通道正式值**仍为写入前的值。"""
    channels = _channels()

    view = local_read(channels, {"messages": [["new"]]}, fresh=True)

    assert view["messages"] == ["old", "new"]
    assert channels["messages"].get() == ["old"]


def test_third_party_channel_subclass_is_readable() -> None:
    """**Edge Case ⑥**：第三方自定义 ``Channel`` 子类 ⇒ 读取层 MUST 只依赖
    B5F1 冻结的四个操作 ⇒ 自定义通道**可被读取**。

    ⚠️ fresh 读的**复制**要求该子类**可复制**（``copy.copy``）⇒
    本用例同时证明该子类**可复制**。
    """

    class CountingChannel(LastValue):
        """第三方自定义子类（**自带一个槽** ⇒ 副本必须带上它）。"""

        __slots__ = ("_writes",)

        def __init__(self, key: str, value_type: object) -> None:
            super().__init__(key, value_type)
            self._writes = 0

        def update(self, values):  # noqa: ANN001, ANN201 —— 夹具形态
            self._writes += 1
            return super().update(values)

    channel = CountingChannel(key="custom", value_type=int)
    channel.update([1])
    channels = {"custom": channel}

    assert read_channels(channels) == {"custom": 1}
    assert local_read(channels, {"custom": [2]}, fresh=True) == {"custom": 2}
    assert channel.get() == 1


# ── 上游同款（2026-11-12 上游对齐 P3）──────────────────────────────────────


def test_the_fresh_view_drops_the_routing_channel_like_upstream() -> None:
    """fresh 视图 MUST 对**每个**通道建副本 ⇒ **路由型**通道的副本被 ``update([])`` 清空
    ⇒ 它在 fresh 视图里**缺席**（**上游同款**）。

    ⚠️ **2026-11-12 上游对齐 P3**：上游对**每一个**通道都 ``copy()`` 一份、再
    ``update(updated[k])``（无写入者 ⇒ ``update([])``）· 上游
    ``langgraph/pregel/_algo.py:209-215`` ⇒ 路由型通道（上游 ``ephemeral_value.py:56-61`` 的
    ``update([])`` 会清空）在 fresh 视图里**缺席**。

    ⇒ 实测两侧**逐字相同**：上游 fresh 视图 = ``{'a': 7, 'acc': ['x']}``（路由通道不在其中）。
    """
    channels = {
        "a": LastValue("a", int),
        "route": EphemeralValue("route", str),
        "acc": BinaryOperatorAggregate("acc", list, operator.add),
    }
    channels["a"].update([2])
    channels["route"].update(["prev"])
    channels["acc"].update([["x"]])

    view = local_read(channels, {"a": [7]}, fresh=True)

    assert view == {"a": 7, "acc": ["x"]}
    # 路由通道在 fresh 视图里**缺席**（上游同款）⇒ **B8F1** 的条件边路由读需知晓此点
    assert "route" not in view
    # 原始通道**不受影响**（读侧零污染）
    assert channels["route"].get() == "prev"
    assert channels["a"].get() == 2
