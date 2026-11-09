# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**错误契约**（``EmptyChannelError`` / ``InvalidChannelUpdateError``）—— B5F1。

本文件承载的判据：

* **空通道读取**抛 ``EmptyChannelError`` —— SC-018 · FR-017 ①③⑦；
* **一步内多值冲突**抛 ``InvalidChannelUpdateError`` —— SC-006 · SC-016；
* **结构化字段**齐备（``key`` / ``received_count`` / ``expected_count``）——
  SC-018 · FR-017 ④；
* **错误对象不携带用户写入的值** —— SC-018 · FR-017 ⑥；
* **构造期校验**（内置 ``TypeError`` / ``ValueError``）—— SC-026 · FR-025；
* **归约器抛错不污染状态** —— SC-006 · FR-008。

⚠️ **单独成文件**（plan 结构段 ②）—— 避免「语义文件」与「错误文件」互相
污染断言来源。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from typing import Any

import pytest

from freegraph.contracts.errors import FreegraphError
from freegraph.runtime import (
    BinaryOperatorAggregate,
    EmptyChannelError,
    EphemeralValue,
    InvalidChannelUpdateError,
    LastValue,
)


# ── 空通道读取的错误契约（SC-018 · FR-017）───────────────────────────────


def test_empty_channel_error_carries_the_channel_key() -> None:
    """SC-018：``EmptyChannelError.key`` == **出错的通道 key**。"""
    channel = LastValue("llm_calls", int)
    with pytest.raises(EmptyChannelError) as excinfo:
        channel.get()
    assert excinfo.value.key == "llm_calls"


def test_empty_channel_error_is_catchable_as_freegraph_error() -> None:
    """SC-018 · FR-017 ③：``except FreegraphError`` **能**捕获。"""
    channel = LastValue("k", int)
    with pytest.raises(FreegraphError):
        channel.get()


def test_empty_channel_error_is_not_a_value_error() -> None:
    """FR-017 ⑦ / SC-018：``EmptyChannelError`` **不是** ``ValueError``
    的子类（「读到无值」是**正常信号**）。"""
    assert not issubclass(EmptyChannelError, ValueError)


def test_empty_channel_error_does_not_carry_the_user_value() -> None:
    """FR-017 ⑥ / SC-018：错误对象 **不携带**用户写入的**值本身**。"""
    channel = LastValue("k", int)
    channel.update(["sensitive-user-value"])
    channel.clear()
    with pytest.raises(EmptyChannelError) as excinfo:
        channel.get()
    rendered = repr(excinfo.value) + str(excinfo.value)
    assert "sensitive-user-value" not in rendered


# ── 归约失败与构造期校验（US2 · SC-006 · SC-016 · SC-026）────────────────


class _ExplodingReducer:
    """**抛错**的归约器（FR-008 · SC-006 的负向用例）。"""

    def __call__(self, current: Any, new: Any) -> Any:
        raise RuntimeError("reducer failed")


def test_reducer_failure_propagates_and_leaves_the_value_unchanged() -> None:
    """FR-008 / SC-006：归约器抛错 ⇒ 异常**向上传播**且通道**值不变**。"""
    channel = BinaryOperatorAggregate("messages", list, _ExplodingReducer())
    with pytest.raises(RuntimeError, match="reducer failed"):
        channel.update([["m1"]])
    assert channel.get() == []
    assert channel.is_available() is True


def test_non_callable_reducer_raises_builtin_type_error_at_construction() -> None:
    """FR-025 ① / SC-026 ①：归约器**不可调用** ⇒ 构造期抛内置 ``TypeError``
    （MUST **NOT** 拖到写入时）。"""
    with pytest.raises(TypeError):
        BinaryOperatorAggregate("k", list, "not-callable")  # type: ignore[arg-type]


def test_empty_reducer_raises_builtin_value_error_at_construction() -> None:
    """FR-025 ② / SC-026 ②：「标注有归约器但归约器为空」⇒ 内置 ``ValueError``。"""
    with pytest.raises(ValueError):
        BinaryOperatorAggregate("k", list, None)  # type: ignore[arg-type]


def test_channel_layer_does_not_recheck_reducer_binarity() -> None:
    """FR-025 ④ / SC-026 ③：通道层**不重做**二元性校验（非二元归约器**不**报错）。"""

    def ternary(a: Any, b: Any, c: Any) -> Any:
        return a

    # 构造**不**报错 ⇒ 通道层没有重做二元性判定（那是 B4F1 的职责）。
    # 值类型取 ``Any``（不可实例化）⇒ 首次写入**直存**、**不调**归约器。
    channel = BinaryOperatorAggregate("k", Any, ternary)  # type: ignore[arg-type]
    assert channel.reducer is ternary
    assert channel.is_available() is False
    channel.update([["m1"]])
    assert channel.get() == ["m1"]


def test_invalid_channel_update_error_structured_fields() -> None:
    """SC-018 / FR-017 ④：``key`` / ``received_count`` / ``expected_count``
    齐备且 ``expected_count`` **恒为 1**。"""
    channel = LastValue("k", int)
    with pytest.raises(InvalidChannelUpdateError) as excinfo:
        channel.update([1, 2])
    error = excinfo.value
    assert error.key == "k"
    assert error.received_count == 2
    assert error.expected_count == 1


def test_invalid_channel_update_error_is_catchable_as_freegraph_error() -> None:
    """SC-018 / FR-017 ③：``except FreegraphError`` **能**捕获。"""
    channel = LastValue("k", int)
    with pytest.raises(FreegraphError):
        channel.update([1, 2])


def test_invalid_channel_update_error_is_also_a_value_error() -> None:
    """FR-017 ②：``InvalidChannelUpdateError`` **双重继承**
    ``FreegraphError`` **且** ``ValueError``。"""
    assert issubclass(InvalidChannelUpdateError, ValueError)
    assert issubclass(InvalidChannelUpdateError, FreegraphError)


def test_conflict_leaves_the_channel_value_unchanged() -> None:
    """SC-006 / I-7：**先检测后写入** ⇒ 冲突时通道**值不变**。"""
    channel = LastValue("k", int)
    channel.update([1])
    with pytest.raises(InvalidChannelUpdateError):
        channel.update([2, 3])
    assert channel.get() == 1


# ── 路由通道冲突（US3 · SC-006 · SC-016 · SC-018）─────────────────────────


def test_ephemeral_value_conflict_raises_with_structured_fields() -> None:
    """SC-006 / SC-016 / SC-018：一步内多值 ⇒ 抛
    ``InvalidChannelUpdateError`` 且结构化字段齐备。"""
    channel = EphemeralValue("route", str)
    with pytest.raises(InvalidChannelUpdateError) as excinfo:
        channel.update(["a", "b"])
    error = excinfo.value
    assert error.key == "route"
    assert error.received_count == 2
    assert error.expected_count == 1


def test_ephemeral_value_conflict_leaves_the_value_unchanged() -> None:
    """SC-006 / I-7：**先检测后写入** ⇒ 冲突时通道**值不变**。"""
    channel = EphemeralValue("route", str)
    channel.update(["a"])
    with pytest.raises(InvalidChannelUpdateError):
        channel.update(["b", "c"])
    assert channel.get() == "a"
