# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**通道纯净性**（属性集 · 规模口径 · 浅引用 · 零副作用）—— B5F1 的 US4。

本文件承载的判据：

* **公开属性集合恰为 4 项** + **实例槽位集合 ⊆ 4 项** + **实例无 ``__dict__``**
  —— SC-009 · FR-013 ① · 澄清轮 Q15 · 裁定 17 ①；
* **规模口径**（引用类型**白名单** + ``gc.get_referents`` **计数探针**）
  —— SC-022 · FR-013 ②③；
* **浅引用**（``channel.value is 传入对象``）—— SC-025 · FR-024；
* **不校验写入值类型** · **无同步原语** · **写入入口只有 ``update()``**
  —— SC-026 · SC-024 · FR-023；
* **导入无副作用**（``sys.modules`` 增量 / 环境变量读取 / 出站连接）——
  SC-005 · FR-015 —— ⚠️ **必须在子进程**断言（复用既有 ``run_in_subprocess``
  夹具 · 既有 conftest **零改动**）。

**契约权威**：``specs/b5f1-channels/contracts/channel-contract.md`` §6。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import gc
import operator
from collections.abc import Callable
from typing import Any, TypedDict

import pytest

from freegraph.runtime import (
    BinaryOperatorAggregate,
    Channel,
    EphemeralValue,
    LastValue,
    SchemaSpec,
    build_channels,
    parse_state_schema,
)

#: 通道实例**允许**持有的**私有槽**集合（**名字逐字冻结** · FR-013 ①）。
ALLOWED_SLOTS = frozenset({"_key", "_value_type", "_value", "_reducer"})

#: 通道**公开属性**集合（**恰为**四项 · FR-013 ① · 澄清轮 Q15）。
PUBLIC_PROPERTIES = frozenset({"key", "value_type", "value", "reducer"})


def _channels() -> tuple[Channel, ...]:
    """三类通道各一（覆盖型 / 归约型 / 路由型）。"""
    return (
        LastValue("k", int),
        BinaryOperatorAggregate("k", list, operator.add),
        EphemeralValue("k", str),
    )


def _public_properties(channel: Channel) -> set[str]:
    """收集通道的**公开属性**（沿 **MRO** · 裁定 17 ① · research D-17 实测）。

    ⚠️ ``type(ch).__dict__`` **只**含该类自身定义的属性 ⇒ 属性定义在基类
    ``Channel`` 上时取到的是**空集** ⇒ MUST 沿 MRO 收集。
    """
    return {
        name
        for klass in type(channel).__mro__
        for name, value in klass.__dict__.items()
        if isinstance(value, property)
    }


def _instance_slots(channel: Channel) -> set[str]:
    """收集通道实例的**槽位**（沿 MRO 收集各类的 ``__slots__``）。"""
    slots: set[str] = set()
    for klass in type(channel).__mro__:
        declared = klass.__dict__.get("__slots__", ())
        if isinstance(declared, str):
            slots.add(declared)
        else:
            slots.update(declared)
    return slots


# ── 公开属性集合与槽位（SC-009 · FR-013 ①）───────────────────────────────


@pytest.mark.parametrize("channel", _channels(), ids=lambda c: type(c).__name__)
def test_public_property_set_is_exactly_four(channel: Channel) -> None:
    """SC-009 ①：公开属性集合**恰为**四项。"""
    assert _public_properties(channel) == set(PUBLIC_PROPERTIES)


@pytest.mark.parametrize("channel", _channels(), ids=lambda c: type(c).__name__)
def test_instance_slots_are_a_subset_of_the_four_slots(channel: Channel) -> None:
    """SC-009 ②：实例槽位集合 ⊆ {``_key``, ``_value_type``, ``_value``, ``_reducer``}。"""
    assert _instance_slots(channel) <= set(ALLOWED_SLOTS)


@pytest.mark.parametrize("channel", _channels(), ids=lambda c: type(c).__name__)
def test_channel_instances_have_no_dict(channel: Channel) -> None:
    """裁定 17 ①：子类**未**声明 ``__slots__ = ()`` ⇒ 实例**自带** ``__dict__``
    ⇒ MUST NOT 存在。"""
    assert not hasattr(channel, "__dict__")


@pytest.mark.parametrize("channel", _channels(), ids=lambda c: type(c).__name__)
def test_channel_rejects_arbitrary_attributes(channel: Channel) -> None:
    """FR-013 ①：通道**结构上**不可能持有 4 项之外的数据。"""
    with pytest.raises(AttributeError):
        channel.arbitrary = 42  # type: ignore[attr-defined]


# ── 规模口径（SC-022 · FR-013 ②③）────────────────────────────────────────


def _schema_with_keys(count: int) -> Any:
    """构造一份含 ``count`` 个 key 的 schema（每个 key 的类型为 ``int``）。"""
    return TypedDict(f"_S{count}", {f"k{index}": int for index in range(count)})


@pytest.mark.parametrize("count", [1, 1000], ids=["N=1", "N=1000"])
def test_channel_reference_count_does_not_grow_with_key_count(count: int) -> None:
    """SC-022 ②：``len(gc.get_referents(channel))`` 与 key 数**无关**。

    ⚠️ **辅助**判据（裁定 17 ③）—— 计数相等**不能**替代白名单。
    """
    spec = parse_state_schema(_schema_with_keys(count))
    channel = build_channels(spec)["k0"]
    reference_count = len(gc.get_referents(channel))
    other = build_channels(parse_state_schema(_schema_with_keys(1)))["k0"]
    assert reference_count == len(gc.get_referents(other))


@pytest.mark.parametrize("count", [1, 1000], ids=["N=1", "N=1000"])
def test_channel_holds_no_state_table_reference(count: int) -> None:
    """SC-022 ①（**主判据**）：引用类型**白名单** —— 通道的直接引用集合中
    MUST **不出现** ``dict`` / ``SchemaSpec`` / 其它 ``Channel`` 实例。"""
    spec = parse_state_schema(_schema_with_keys(count))
    channel = build_channels(spec)["k0"]
    violations = [
        type(referent).__name__
        for referent in gc.get_referents(channel)
        if isinstance(referent, (dict, Channel))
        or type(referent).__name__ == "SchemaSpec"
    ]
    assert violations == []


def test_schema_spec_is_not_reachable_from_the_channel() -> None:
    """SC-022 ①：通道**不持有**状态表（``SchemaSpec``）的引用。"""
    spec = parse_state_schema(_schema_with_keys(3))
    channel = build_channels(spec)["k0"]
    assert not any(
        isinstance(referent, SchemaSpec) for referent in gc.get_referents(channel)
    )


def test_channel_holds_no_other_channel_reference() -> None:
    """SC-022 ①：通道**不持有**其它 ``Channel`` 实例。"""
    channels = build_channels(parse_state_schema(_schema_with_keys(3)))
    for channel in channels.values():
        assert not any(
            isinstance(referent, Channel) for referent in gc.get_referents(channel)
        )


# ── 值的引用语义（SC-025 · FR-024）────────────────────────────────────────


class _Uncopyable:
    """持有**不可拷贝**成员的自定义类（SC-025 ③）。"""

    def __init__(self) -> None:
        self.payload = object()

    def __deepcopy__(self, memo: dict[int, Any]) -> "_Uncopyable":
        raise TypeError("this object refuses to be copied")


@pytest.mark.parametrize(
    ("channel", "payload"),
    [
        (LastValue("k", int), {"user": "data"}),
        (BinaryOperatorAggregate("k", object, lambda current, new: new), {"u": 1}),
        (EphemeralValue("k", str), {"user": "data"}),
    ],
    ids=["LastValue", "BinaryOperatorAggregate", "EphemeralValue"],
)
def test_channel_shallow_references_the_user_object(
    channel: Channel, payload: Any
) -> None:
    """SC-025 ①：写入后 ``channel.value is 传入对象``（**身份**判定）。"""
    channel.update([payload])
    assert channel.value is payload


def test_channel_does_not_deep_copy_the_user_object() -> None:
    """SC-025 ③：写入**不可拷贝**的对象 MUST **不抛错**（无深拷贝失败模式）。"""
    payload = _Uncopyable()
    channel = LastValue("k", object)
    channel.update([payload])
    assert channel.value is payload


def test_channel_does_not_validate_the_written_value_type() -> None:
    """SC-025 ④ / FR-024 ③：通道**不校验**写入值的类型。"""
    channel = LastValue("k", int)
    channel.update(["not-an-int"])
    assert channel.get() == "not-an-int"


def test_reduce_channel_holds_the_reducer_return_value_identity() -> None:
    """SC-025 ②：归约型通道持有的值 MUST 与**归约器的返回值**是同一对象。"""
    returned: list[Any] = []

    def reducer(current: Any, new: Any) -> Any:
        result = (current, new)
        returned.append(result)
        return result

    channel = BinaryOperatorAggregate("k", tuple, reducer)
    channel.update([("a",)])
    assert channel.value is returned[0]


# ── 写入入口与同步原语（SC-024 · FR-023）──────────────────────────────────


@pytest.mark.parametrize("channel", _channels(), ids=lambda c: type(c).__name__)
def test_write_entry_point_is_update_only(channel: Channel) -> None:
    """SC-024 ②：写入入口的条数 == **1**（且只能经由 ``update()``）。

    ⚠️ MUST NOT **求值**属性（``value`` 在无值时会抛错）⇒ 只看类字典里的
    **可调用项**（property 对象不算可调用项 —— 它是描述符）。
    """
    public: set[str] = set()
    for klass in type(channel).__mro__:
        for name, value in klass.__dict__.items():
            if name.startswith("_") or isinstance(value, property):
                continue
            if callable(value):
                public.add(name)
    assert "update" in public
    assert not (public - {"update", "get", "is_available", "clear"})


@pytest.mark.parametrize("channel", _channels(), ids=lambda c: type(c).__name__)
def test_channel_holds_no_synchronization_primitive(channel: Channel) -> None:
    """SC-024 ①：通道实例持有**锁 / 同步原语**的数量 == 0。"""
    forbidden = ("Lock", "RLock", "Condition", "Event", "Semaphore", "threading")
    for referent in gc.get_referents(channel):
        name = type(referent).__name__
        assert name not in forbidden
        assert "lock" not in name.lower()


# ── 导入副作用（SC-005 · FR-015 · I-19）───────────────────────────────────


def test_importing_freegraph_runtime_has_no_side_effects(
    run_in_subprocess: Callable[[str], dict[str, Any]]
) -> None:
    """SC-005：导入 ``freegraph.runtime`` ⇒ ``sys.modules`` 增量中**非标准库**
    条目数 == 0 · 环境变量读取次数 == 0 · 出站连接次数 == 0。

    ⚠️ MUST 在**子进程**执行（同进程已被 pytest 污染）。
    """
    result = run_in_subprocess(
        """
import json
import sys
before = set(sys.modules)
import freegraph.runtime
delta = sorted(
    name
    for name in set(sys.modules) - before
    if name.split(".")[0] not in set(sys.stdlib_module_names)
    and not name.startswith("freegraph")
)
print(json.dumps({"non_stdlib_delta": delta}))
"""
    )
    assert result["non_stdlib_delta"] == []
    assert result["env_reads"] == 0
    assert result["egress"] == 0

def test_channel_modules_reference_no_third_party_packages(
    run_in_subprocess: Callable[[str], dict[str, Any]]
) -> None:
    """SC-005：三类通道的实现对 ``langchain*`` / ``langsmith`` / ``langgraph*`` /
    ``pydantic`` / ``typing_extensions`` 的**引用数 == 0**。"""
    result = run_in_subprocess(
        """
import json
import sys
import freegraph.runtime
prefixes = ("langchain", "langgraph", "langsmith", "pydantic", "typing_extensions")
hits = sorted(
    name
    for name in sys.modules
    if any(name == prefix or name.startswith(prefix) for prefix in prefixes)
)
print(json.dumps({"third_party": hits}))
"""
    )
    assert result["third_party"] == []
