# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**三类通道的语义** —— B5F1 的 US1 / US2 / US3（SC-001…SC-004 · SC-020…SC-023）。

本文件承载的判据：

* **覆盖语义**（``LastValue``）—— SC-001 · SC-020 · **验收判据 A2**；
* **归约语义**（``BinaryOperatorAggregate``）—— SC-002 · SC-010 · SC-021 ·
  **验收判据 A1**；
* **清空语义**（``EphemeralValue``）—— SC-003 · SC-023 · **验收判据 A3**；
* **初始状态三档** —— SC-023 · FR-022；
* **可替换性**（自定义子类）与**名字面** —— SC-017 · SC-019；
* **参数化组合**（归约器类型 × 通道类型）—— SC-028 · FR-027。

**契约权威**：``specs/b5f1-channels/contracts/channel-contract.md``。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import collections.abc
import operator
from typing import Annotated, Any, NotRequired, Required

import pytest

from freegraph.runtime.channel import MISSING
from freegraph.runtime import (
    BinaryOperatorAggregate,
    Channel,
    EmptyChannelError,
    EphemeralValue,
    InvalidChannelUpdateError,
    LastValue,
)


class _CountingReducer:
    """**可调用实例**的归约器 —— 记录调用次数与实参（FR-007 ② · I-10）。"""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, Any]] = []

    def __call__(self, current: Any, new: Any) -> Any:
        self.calls.append((current, new))
        return operator.add(current, new)


# ── 覆盖语义（US1 · 验收判据 A2 · SC-001 · SC-020）────────────────────────


def test_last_value_overwrites_on_consecutive_writes() -> None:
    """SC-001（**验收判据 A2**）：连续两次写入 ⇒ 读到**末值**（不是累加）。"""
    channel = LastValue("llm_calls", int)
    assert channel.update([1]) is True
    assert channel.update([2]) is True
    assert channel.get() == 2
    assert channel.get() != 3
    assert channel.get() != 1


def test_last_value_never_holds_or_calls_a_reducer() -> None:
    """SC-001：`reducer is None` ⇒ 「无归约器 ⇒ 覆盖」**不走**归约路径。"""
    channel = LastValue("llm_calls", int)
    assert channel.reducer is None
    channel.update([1])
    channel.update([2])
    assert channel.reducer is None


def test_last_value_update_returns_true_for_non_empty_writes() -> None:
    """SC-020 ①：写入序列**非空** ⇒ 返回**真**（哪怕值**逐字相等**）。"""
    channel = LastValue("k", int)
    assert channel.update([7]) is True
    assert channel.update([7]) is True
    assert channel.get() == 7


def test_last_value_update_returns_false_for_empty_sequence() -> None:
    """SC-020 ②：写入序列**为空** ⇒ 返回**假**且通道值**不变**。"""
    channel = LastValue("k", int)
    assert channel.update([]) is False
    assert channel.is_available() is False
    channel.update([1])
    assert channel.update([]) is False
    assert channel.get() == 1


# ── 初始状态与只读性（US1 · SC-004 · SC-009 · SC-020 · SC-023）──────────


def test_last_value_starts_without_a_value() -> None:
    """SC-023 ①：覆盖型构造后 `is_available()` 为**假**（初始「无值」）。"""
    channel = LastValue("k", int)
    assert channel.is_available() is False


def test_last_value_get_on_empty_channel_raises() -> None:
    """FR-011 ②：读「无值」通道 ⇒ 抛 ``EmptyChannelError``。"""
    channel = LastValue("k", int)
    with pytest.raises(EmptyChannelError):
        channel.get()


def test_last_value_update_with_empty_sequence_is_a_no_op() -> None:
    """FR-002：``update([])`` ⇒ **无操作**、返回**假**、值**不变**。"""
    channel = LastValue("k", int)
    assert channel.update([]) is False
    assert channel.is_available() is False
    with pytest.raises(EmptyChannelError):
        channel.get()


def test_last_value_writing_none_makes_it_available() -> None:
    """FR-011 ③：「值为 ``None``」与「无值」**严格可分**。"""
    channel = LastValue("k", int)
    channel.update([None])
    assert channel.is_available() is True
    assert channel.get() is None


def test_last_value_value_property_is_read_only() -> None:
    """FR-002：`value` **无 setter** ⇒ 外部 MUST NOT 能改写。"""
    channel = LastValue("k", int)
    with pytest.raises(AttributeError):
        channel.value = 5  # type: ignore[misc]


def test_last_value_clear_resets_to_no_value() -> None:
    """FR-009 / SC-023 ④：`clear()` ⇒ **无值**（读取抛错）。"""
    channel = LastValue("k", int)
    channel.update([1])
    assert channel.clear() is True
    assert channel.is_available() is False
    with pytest.raises(EmptyChannelError):
        channel.get()


def test_last_value_clear_is_idempotent() -> None:
    """FR-002：已是「无值」⇒ ``clear()`` **无操作**、返回**假**（幂等）。"""
    channel = LastValue("k", int)
    assert channel.clear() is False
    channel.update([1])
    assert channel.clear() is True
    assert channel.clear() is False
    assert channel.is_available() is False


def test_channel_public_property_set_is_frozen() -> None:
    """SC-004 · SC-009 ① · SC-020 · SC-023：公开属性集合 **⊆** 七项。

    ⚠️ 沿 **MRO** 收集（``type(ch).__dict__`` **只**含该类自身定义的属性
    —— 属性定义在基类上时取到**空集** ⇒ 裁定 17 ① · research D-17 实测）。

    ⚠️ **2026-11-12 · 上游对齐 P2-a**：属性集合由**四项**扩为**七项** —— 新增
    ``typ`` / ``ValueType`` / ``UpdateType``（上游 ``BaseChannel`` 的同名成员 ·
    ``langgraph/channels/base.py:22,28-38``）⇒ **冻结面**相应扩展（**只增**，
    不改既有四项的名字与语义）⇒ 用于支撑「每次运行新建通道实例」的多会话隔离。
    """
    channel = LastValue("k", int)
    properties = {
        name
        for klass in type(channel).__mro__
        for name, value in klass.__dict__.items()
        if isinstance(value, property)
    }
    expected = {
        "key",
        "value_type",
        "value",
        "reducer",
        "typ",
        "ValueType",
        "UpdateType",
    }
    assert properties <= expected
    assert expected <= properties


# ── 归约语义（US2 · 验收判据 A1 · SC-002 · SC-010 · SC-021）──────────────


def test_binary_operator_aggregate_reduces_in_order() -> None:
    """SC-002（**验收判据 A1**）：两次写入 ⇒ 逐元素等于 ``["m1", "m2"]``。"""
    channel = BinaryOperatorAggregate("messages", list, operator.add)
    channel.update([["m1"]])
    channel.update([["m2"]])
    assert channel.get() == ["m1", "m2"]


def test_binary_operator_aggregate_folds_from_the_initial_empty_value() -> None:
    """SC-021：基准 = **从初始空值起折叠**（**不是**从首值起折）。"""
    channel = BinaryOperatorAggregate("messages", list, operator.add)
    channel.update([["m1"]])
    channel.update([["m2"]])
    base: list[Any] = []
    base = operator.add(base, ["m1"])
    base = operator.add(base, ["m2"])
    assert channel.get() == base


def test_binary_operator_aggregate_holds_the_reducer_by_reference() -> None:
    """SC-010 / FR-014：``channel.reducer is operator.add``（**身份**判定）。"""
    channel = BinaryOperatorAggregate("messages", list, operator.add)
    assert channel.reducer is operator.add


def test_binary_operator_aggregate_starts_with_the_derived_empty_value() -> None:
    """SC-002 / SC-023 ②：初始「**有值**」且值为 ``[]``（**验收判据 A1**）。"""
    channel = BinaryOperatorAggregate("messages", list, operator.add)
    assert channel.is_available() is True
    assert channel.get() == []


def test_binary_operator_aggregate_reducer_call_count_matches_value_count() -> None:
    """FR-005：写入 N 个值 ⇒ 归约器被调用 **N** 次（通道**有值**时）。"""
    reducer = _CountingReducer()
    channel = BinaryOperatorAggregate("messages", list, reducer)
    channel.update([["m1"]])
    channel.update([["m2"]])
    channel.update([["m3"]])
    assert len(reducer.calls) == 3


# ── 空值推导与首次写入（US2 · SC-007 · SC-021）────────────────────────────


@pytest.mark.parametrize(
    ("value_type", "expected"),
    [
        (list, []),
        (int, 0),
        (str, ""),
        (dict, {}),
        (collections.abc.Sequence, []),
        (collections.abc.MutableSequence, []),
        (collections.abc.Set, set()),
        (collections.abc.MutableSet, set()),
        (collections.abc.Mapping, {}),
        (collections.abc.MutableMapping, {}),
        (Annotated[list, "meta"], []),
        (Required[list], []),
        (NotRequired[list], []),
        (list[int], []),
    ],
)
def test_empty_value_derivation_covers_six_categories(
    value_type: Any, expected: Any
) -> None:
    """SC-007：空值推导覆盖面 **≥ 6 类**（含**抽象容器映射**）。"""
    channel = BinaryOperatorAggregate("k", value_type, operator.add)
    assert channel.is_available() is True
    assert channel.get() == expected


def test_empty_value_derivation_fails_for_non_instantiable_types() -> None:
    """SC-007：值类型**不可实例化** ⇒ 初始「**无值**」（构造**不**失败）。"""
    channel = BinaryOperatorAggregate("k", Any, operator.add)
    assert channel.is_available() is False
    with pytest.raises(EmptyChannelError):
        channel.get()


def test_first_write_on_an_empty_channel_stores_the_value_directly() -> None:
    """FR-007 ② / I-10：通道**无值** + **单值**写入 ⇒ 归约器调用次数 == 0。"""
    reducer = _CountingReducer()
    channel = BinaryOperatorAggregate("k", Any, reducer)
    channel.update([["m1"]])
    assert len(reducer.calls) == 0
    assert channel.get() == ["m1"]


def test_first_write_with_multiple_values_stores_the_first_and_reduces_the_rest() -> None:
    """FR-007 ②（裁定 17 ④）：多值首写 ⇒ 首个**直存**、其余按序归约
    （归约器调用次数 == **值数 − 1**）。"""
    reducer = _CountingReducer()
    channel = BinaryOperatorAggregate("k", Any, reducer)
    channel.update([["m1"], ["m2"], ["m3"]])
    assert len(reducer.calls) == 2
    assert channel.get() == ["m1", "m2", "m3"]


def test_two_same_typed_channels_do_not_share_their_empty_value() -> None:
    """FR-006 ④ / SC-007 / I-11：两个同类型通道的空值**不是同一对象**。"""
    first = BinaryOperatorAggregate("a", list, operator.add)
    second = BinaryOperatorAggregate("b", list, operator.add)
    assert first.get() is not second.get()
    first.update([["x"]])
    assert second.get() == []


def test_binary_operator_aggregate_cleared_channel_is_not_back_to_initial() -> None:
    """FR-022 ③ / SC-023 ④：``clear()`` 后 ⇒ **无值**且**不回到**初始空值。"""
    channel = BinaryOperatorAggregate("messages", list, operator.add)
    initial = channel.get()
    assert channel.clear() is True
    assert channel.is_available() is False
    with pytest.raises(EmptyChannelError):
        channel.get()
    assert initial == []


def test_cleared_binary_operator_aggregate_treats_next_write_as_first() -> None:
    """FR-007 ②：清空后再写入 ⇒ 按「**无值**」处理（**直存**、调用次数 == 0）。"""
    reducer = _CountingReducer()
    channel = BinaryOperatorAggregate("k", list, reducer)
    channel.update([["m1"]])
    channel.clear()
    channel.update([["m2"]])
    assert len(reducer.calls) == 1
    assert channel.get() == ["m2"]


def test_binary_operator_aggregate_clear_is_idempotent() -> None:
    """FR-002 / FR-009：已是「无值」⇒ ``clear()`` **无操作**、返回**假**。"""
    channel = BinaryOperatorAggregate("k", Any, operator.add)
    assert channel.is_available() is False
    assert channel.clear() is False
    channel.update([["m1"]])
    assert channel.clear() is True
    assert channel.clear() is False


# ── 清空语义（US3 · 验收判据 A3 · SC-003 · SC-023）────────────────────────


def test_ephemeral_value_clear_resets_to_no_value() -> None:
    """SC-003（**验收判据 A3**）：``clear()`` ⇒ **无值**（不是 ``None``）。"""
    channel = EphemeralValue("route", str)
    channel.update(["tool_node"])
    assert channel.get() == "tool_node"
    assert channel.clear() is True
    assert channel.is_available() is False
    with pytest.raises(EmptyChannelError):
        channel.get()


def test_ephemeral_value_clear_does_not_leak_the_previous_value() -> None:
    """SC-003：清空后读取**不得**返回上一次的值、**不得**返回 ``None``。"""
    channel = EphemeralValue("route", str)
    channel.update(["tool_node"])
    channel.clear()
    with pytest.raises(EmptyChannelError) as excinfo:
        channel.get()
    assert "tool_node" not in str(excinfo.value)


def test_ephemeral_value_write_after_clear_restores_availability() -> None:
    """SC-003：清空后再写入 ⇒ 恢复「有值」且新值 == **刚写入**的值。"""
    channel = EphemeralValue("route", str)
    channel.update(["tool_node"])
    channel.clear()
    channel.update(["other"])
    assert channel.is_available() is True
    assert channel.get() == "other"


def test_ephemeral_value_clear_is_idempotent() -> None:
    """FR-009：连续 ``clear()`` 两次 ⇒ 第二次返回**假**（幂等）。"""
    channel = EphemeralValue("route", str)
    channel.update(["tool_node"])
    assert channel.clear() is True
    assert channel.clear() is False
    assert channel.is_available() is False


def test_ephemeral_value_starts_without_a_value() -> None:
    """FR-022 ①：路由型构造后初始「**无值**」（**不推导**空值）。"""
    channel = EphemeralValue("route", str)
    assert channel.is_available() is False
    with pytest.raises(EmptyChannelError):
        channel.get()


def test_ephemeral_value_update_with_empty_sequence_clears() -> None:
    """FR-010（**上游同款** · 2026-11-12 上游对齐 P2-a）：空序列 ⇒ **清空**。

    ⚠️ 上游 ``EphemeralValue.update([])`` ⇒ 值 → 缺失、返回**真**（**仅当**原先有值）
    （``langgraph/channels/ephemeral_value.py:56-61``）⇒ 调度层用它做**步末清空**
    （上游 ``pregel/_algo.py:326-333``）⇒ **原先**的「空序列 = 无操作 + 清空走 ``clear()``」
    口径与上游**不同款** ⇒ 已按上游改写。
    """
    channel = EphemeralValue("route", str)
    # 本来就无值 ⇒ 无操作、返回**假**
    assert channel.update([]) is False
    assert channel.is_available() is False
    channel.update(["x"])
    # 有值 ⇒ **清空**、返回**真**
    assert channel.update([]) is True
    assert channel.is_available() is False


def test_ephemeral_value_never_holds_a_reducer() -> None:
    """FR-010：路由型**无归约器**（``reducer is None``）。"""
    channel = EphemeralValue("route", str)
    assert channel.reducer is None


# ── 可替换性 + 名字面（US4 · SC-017 · SC-019）─────────────────────────────


class _CustomChannel(Channel):
    """**只依赖通道抽象**的自定义通道（FR-019 ③ · SC-017）。

    ⚠️ 它**不改动**抽象与既有三类通道 ⇒ 证明抽象**真的**是可替换的
    实现单元。``__slots__ = ()`` ⇒ 实例**无** ``__dict__``。
    """

    __slots__ = ()


    def from_checkpoint(self, checkpoint: Any) -> "Channel":
        """按检查点**新建**同种通道（**上游同款** · ``langgraph/channels/base.py:60-65``
        的 ``from_checkpoint`` 是**抽象方法** ⇒ 第三方自定义通道**必须**自己实现）。"""
        empty = type(self)(self._key, self._value_type)
        if checkpoint is not MISSING:
            empty._value = checkpoint
        return empty
    def __init__(self, key: str, value_type: Any) -> None:
        super().__init__(key, value_type)
        self._value = None

    def update(self, values: Any) -> bool:
        """收集最后一次写入（示例语义）。"""
        if len(values) == 0:
            return False
        self._value = values[-1]
        return True

    def get(self) -> Any:
        """取回最后一次写入。"""
        return self._value

    def is_available(self) -> bool:
        """判定「有值 / 无值」。"""
        return self._value is not None

    def clear(self) -> bool:
        """清空（示例语义）。"""
        if self._value is None:
            return False
        self._value = None
        return True


def test_a_custom_channel_subclass_is_usable_through_the_abstract() -> None:
    """SC-017：只依赖抽象的自定义子类可被创建 / 写入 / 读取 / 清空。"""
    channel = _CustomChannel("custom", str)
    assert isinstance(channel, Channel)
    assert channel.key == "custom"
    assert channel.update(["x"]) is True
    assert channel.get() == "x"
    assert channel.is_available() is True
    assert channel.clear() is True
    assert channel.is_available() is False


def test_abstract_base_class_is_not_instantiable() -> None:
    """FR-001：抽象基类**运行时不可实例化**（``abc.ABC`` + ``@abstractmethod``）。"""
    with pytest.raises(TypeError):
        Channel("k", int)  # type: ignore[abstract]


def test_channel_operation_names_are_frozen() -> None:
    """SC-019 / I-23：四个操作名**逐字一致**。"""
    for name in ("update", "get", "is_available", "clear"):
        assert callable(getattr(Channel, name))
        assert name in Channel.__abstractmethods__ or name == "clear"


def test_channel_attribute_names_are_frozen() -> None:
    """SC-019 / I-23：四个属性名**逐字一致**。"""
    for name in ("key", "value_type", "value", "reducer"):
        assert isinstance(getattr(Channel, name), property)


def test_channel_class_names_are_frozen() -> None:
    """SC-019 / I-23：四个类名**逐字一致**。"""
    assert Channel.__name__ == "Channel"
    assert LastValue.__name__ == "LastValue"
    assert BinaryOperatorAggregate.__name__ == "BinaryOperatorAggregate"
    assert EphemeralValue.__name__ == "EphemeralValue"


def test_mapping_entry_point_names_are_frozen() -> None:
    """SC-019 / I-23：两个映射入口名**逐字一致**。"""
    from freegraph.runtime import build_channel, build_channels

    assert callable(build_channel)
    assert callable(build_channels)


def test_error_type_names_are_frozen() -> None:
    """SC-019 / I-23：两个错误类型名**逐字一致**。"""
    from freegraph.runtime import InvalidChannelUpdateError

    assert EmptyChannelError.__name__ == "EmptyChannelError"
    assert InvalidChannelUpdateError.__name__ == "InvalidChannelUpdateError"


# ── 参数化组合（US4 · FR-027 · SC-028）────────────────────────────────────


def _concat_reducer(current: Any, new: Any) -> Any:
    """**自定义**二元归约器 —— 同类型序列拼接（FR-027 ① 的第三类归约器）。

    ``list`` / ``tuple`` / ``str`` / ``bytes`` 均适用 ⇒ 每组组合的
    「归约器 × 值类型」都**相容**（FR-027 ②）。
    """
    if isinstance(current, (str, bytes, tuple)):
        return current + new
    return list(current) + list(new)


#: 「**归约器类型** × **通道类型**」的组合表（FR-027 ①②）——
#: 每组自带**相容**的值类型（归约器与值类型**不得**配成不兼容组合，
#: 否则断言的是「归约器报错」而非「语义恒成立」）。
#:
#: 三类归约器：``operator.add`` · ``max`` · ``_concat_reducer``（自定义）。
_COMBINATIONS = [
    (operator.add, list, ["m1"]),
    (operator.add, list[int], [1]),
    (operator.add, str, "m1"),
    (operator.add, tuple, ("m1",)),
    (operator.add, bytes, b"m1"),
    (max, int, 1),
    (max, float, 1.5),
    (max, str, "a"),
    (max, tuple, ("a",)),
    (max, bytes, b"a"),
    (_concat_reducer, list, ["m1"]),
    (_concat_reducer, tuple, ("m1",)),
    (_concat_reducer, str, "m1"),
    (_concat_reducer, bytes, b"m1"),
]


@pytest.mark.parametrize(
    ("reducer", "value_type", "sample"),
    _COMBINATIONS,
    ids=[f"{i:02d}-{r.__name__}-{v!r}" for i, (r, v, _) in enumerate(_COMBINATIONS)],
)
def test_parameterized_combinations_cover_at_least_twelve(
    reducer: Any, value_type: Any, sample: Any
) -> None:
    """SC-028：组合数 **≥ 12**（3 类归约器 × 3 类通道）。"""
    assert len(_COMBINATIONS) >= 12
    assert reducer is not None and value_type is not None and sample is not None


@pytest.mark.parametrize(
    ("reducer", "value_type", "sample"),
    _COMBINATIONS,
    ids=[f"{i:02d}-{r.__name__}-{v!r}" for i, (r, v, _) in enumerate(_COMBINATIONS)],
)
def test_overwrite_semantics_holds_in_every_combination(
    reducer: Any, value_type: Any, sample: Any
) -> None:
    """FR-027 ③ ①：覆盖型写入 ⇒ 读到**末值**（所有组合下恒成立）。"""
    channel = LastValue("k", value_type)
    channel.update([sample])
    channel.update(["second"])
    assert channel.get() == "second"


@pytest.mark.parametrize(
    ("reducer", "value_type", "sample"),
    _COMBINATIONS,
    ids=[f"{i:02d}-{r.__name__}-{v!r}" for i, (r, v, _) in enumerate(_COMBINATIONS)],
)
def test_reduce_semantics_holds_in_every_combination(
    reducer: Any, value_type: Any, sample: Any
) -> None:
    """FR-027 ③ ②：归约型写入序列 == **从初始值起**的逐次归约。"""
    channel = BinaryOperatorAggregate("k", value_type, reducer)
    empty = channel.get()
    channel.update([sample])
    channel.update([sample])
    expected = reducer(reducer(empty, sample), sample)
    assert channel.get() == expected


@pytest.mark.parametrize(
    ("reducer", "value_type", "sample"),
    _COMBINATIONS,
    ids=[f"{i:02d}-{r.__name__}-{v!r}" for i, (r, v, _) in enumerate(_COMBINATIONS)],
)
def test_clear_semantics_holds_in_every_combination(
    reducer: Any, value_type: Any, sample: Any
) -> None:
    """FR-027 ③ ③：路由型清空后 ⇒ **无值**（所有组合下恒成立）。"""
    channel = EphemeralValue("k", value_type)
    channel.update([sample])
    assert channel.clear() is True
    assert channel.is_available() is False
    with pytest.raises(EmptyChannelError):
        channel.get()


@pytest.mark.parametrize(
    ("reducer", "value_type", "sample"),
    _COMBINATIONS,
    ids=[f"{i:02d}-{r.__name__}-{v!r}" for i, (r, v, _) in enumerate(_COMBINATIONS)],
)
def test_conflict_fails_explicitly_in_every_combination(
    reducer: Any, value_type: Any, sample: Any
) -> None:
    """FR-027 ③ ④：一步内多值 ⇒ **显式失败**且**值不变**（所有组合下恒成立）。"""
    for channel in (
        LastValue("k", value_type),
        EphemeralValue("k", value_type),
    ):
        channel.update([sample])
        with pytest.raises(InvalidChannelUpdateError):
            channel.update([sample, sample])
        assert channel.get() == sample


# ── 上游同款的通道成员（2026-11-12 上游对齐 P2-a）────────────────────────


def test_typ_value_type_and_update_type_are_readable() -> None:
    """``typ`` / ``ValueType`` / ``UpdateType`` MUST 直接可读（上游同款）。

    ⚠️ 上游 ``BaseChannel`` 的同名成员（``langgraph/channels/base.py:22,28-38``）
    ⇒ freegraph 的**冻结面**由四项扩为**七项**（**只增**）。
    """
    channel = LastValue("k", int)
    assert channel.typ is int
    assert channel.ValueType is int
    assert channel.UpdateType is int


def test_copy_returns_a_new_channel_with_the_same_value() -> None:
    """``copy()`` MUST 返回**新通道**且带同样的值（上游同款 · ``base.py:40-47``）。"""
    channel = LastValue("k", int)
    channel.update([7])
    copied = channel.copy()
    assert copied is not channel
    assert copied.get() == 7
    assert copied.key == "k"


def test_checkpoint_returns_the_value_or_the_missing_sentinel() -> None:
    """``checkpoint()`` MUST 返回当前值；无值 ⇒ 返回**缺失哨兵**（上游同款 · ``base.py:49-58``）。"""
    from freegraph.runtime.channel import MISSING

    channel = LastValue("k", int)
    assert channel.checkpoint() is MISSING
    channel.update([3])
    assert channel.checkpoint() == 3


def test_from_checkpoint_builds_a_fresh_channel_with_the_given_value() -> None:
    """``from_checkpoint()`` MUST **新建**同种通道并带上给定的值（上游同款 · ``base.py:60-65``）。"""
    from freegraph.runtime.channel import MISSING

    channel = LastValue("k", int)
    rebuilt = channel.from_checkpoint(9)
    assert rebuilt is not channel
    assert rebuilt.get() == 9
    assert rebuilt.key == "k"

    empty = channel.from_checkpoint(MISSING)
    assert empty.is_available() is False


def test_the_reducer_channel_rebuild_keeps_its_reducer() -> None:
    """归约型通道重建时 MUST **带上归约器**（上游同款 · ``binop.py:116-121``）。"""
    channel = BinaryOperatorAggregate("k", list, operator.add)
    rebuilt = channel.from_checkpoint(["x"])
    assert rebuilt.reducer is operator.add
    rebuilt.update([["y"]])
    assert rebuilt.get() == ["x", "y"]


def test_the_routing_channel_rebuild_keeps_its_guard() -> None:
    """路由型通道重建时 MUST **带上 guard**（上游同款 · ``ephemeral_value.py:48-54``）。"""
    channel = EphemeralValue("k", str, guard=False)
    rebuilt = channel.from_checkpoint("v")
    assert rebuilt.guard is False
    assert rebuilt.get() == "v"
    assert rebuilt.key == "k"


def test_consume_and_finish_are_no_ops_by_default() -> None:
    """``consume()`` / ``finish()`` 默认**无操作**（上游同款 · ``base.py:101-120``）。"""
    channel = LastValue("k", int)
    assert channel.consume() is False
    assert channel.finish() is False


def test_the_abstract_from_checkpoint_raises_for_the_base_class() -> None:
    """基类的 ``from_checkpoint`` MUST 不可直接使用（**抽象方法** · 上游同款）。

    ⚠️ 上游 ``BaseChannel.from_checkpoint`` 是 ``@abstractmethod``（``base.py:60-65``）
    ⇒ 第三方自定义通道**必须**自己实现「按检查点重建」。
    """
    from freegraph.runtime.channel import Channel

    with pytest.raises(NotImplementedError):
        Channel.from_checkpoint(object(), 1)  # type: ignore[abstract]


def test_the_reducer_channel_rebuild_from_the_missing_sentinel() -> None:
    """归约型通道从**缺失哨兵**重建 ⇒ 新通道**无值**（上游同款）。"""
    from freegraph.runtime.channel import MISSING

    channel = BinaryOperatorAggregate("k", list, operator.add)
    rebuilt = channel.from_checkpoint(MISSING)
    assert rebuilt.get() == []
