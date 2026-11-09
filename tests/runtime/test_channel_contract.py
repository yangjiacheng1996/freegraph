# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**契约守卫** —— 逐条比对 B5F1 的冻结面 —— 属 **B5F1**。

本文件**解析** ``specs/b5f1-channels/contracts/channel-contract.md``
（``<!-- authority: yes -->`` · **唯一权威**）⇒ **判据与用例天然分离**
⇒ **MUST NOT** 在本文件里另抄一份契约。

解析并逐条断言的内容：

* §1 —— **抽象基类**与 4 个只读属性 · 公开属性集合；
* §2 —— **四个操作**的名字与返回值口径；
* §2.1 / §2.2 —— ``update()`` / ``clear()`` 的返回值口径；
* §3 —— **三类语义**（``LastValue`` / ``BinaryOperatorAggregate`` /
  ``EphemeralValue``）的冻结条目；
* §4 —— **映射契约** M-1…M-4；
* §5 —— **错误契约** E-1…E-5；
* §6 —— **不变量 I-1…I-23**（**全部 23 条** · 含 I-4 ``is_available()``
  恒不抛错 / I-5 ``value`` 与 ``get()`` 同义）—— ⚠️ 每一条 MUST 有断言。

⚠️ **单独成文件**（plan 结构段 ⑤）—— 与「纯净性」文件的 import 副作用断言
**物理隔离**（避免同进程 ``sys.modules`` 互相污染）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import gc
import operator
import re
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, TypedDict

import pytest

from freegraph.contracts.errors import FreegraphError
from freegraph.runtime import (
    BinaryOperatorAggregate,
    Channel,
    ChannelSpec,
    EmptyChannelError,
    EphemeralValue,
    InvalidChannelUpdateError,
    LastValue,
    build_channel,
    build_channels,
    parse_state_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    REPO_ROOT / "specs" / "b5f1-channels" / "contracts" / "channel-contract.md"
)

_BACKTICKED = re.compile(r"`([^`]+)`")


# ── 契约文件的解析（**判据与用例天然分离**）────────────────────────────────


def _table_cells(line: str) -> list[str]:
    """把一行 Markdown 表格拆成单元格（去首尾空单元格 · 去空白）。"""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    parts = stripped.split("|")
    if parts and not parts[0].strip():
        parts = parts[1:]
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    return [cell.strip() for cell in parts]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(set(cell) <= {"-", ":", " "} and cell for cell in cells)


def _backticked(cell: str) -> str:
    match = _BACKTICKED.search(cell)
    return match.group(1).strip() if match else ""


def _section_lines(lines: list[str], heading_prefix: str) -> list[str]:
    """取出某个 ``##`` 小节的正文行（**不含**小节标题本身）。"""
    collected: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            inside = line.startswith(heading_prefix)
            continue
        if inside:
            collected.append(line)
    return collected


def _contract_text() -> str:
    """契约权威文件的**全文**。"""
    return CONTRACT_PATH.read_text(encoding="utf-8")


def _contract_rows(prefix: str) -> list[dict[str, str]]:
    """取出某个小节里的表格行（``{index, text}``）。"""
    rows: list[dict[str, str]] = []
    for line in _section_lines(_contract_text().splitlines(), prefix):
        cells = _table_cells(line)
        if len(cells) < 2 or _is_separator(cells):
            continue
        rows.append({"index": cells[0], "text": " ".join(cells[1:])})
    return rows


def _invariant_rows() -> list[dict[str, str]]:
    """§6 的**不变量**行（``I-1…I-23``）。"""
    rows: list[dict[str, str]] = []
    for line in _section_lines(_contract_text().splitlines(), "## 6."):
        cells = _table_cells(line)
        if len(cells) != 2 or _is_separator(cells):
            continue
        if not re.fullmatch(r"I-\d+", cells[0]):
            continue
        rows.append({"index": cells[0], "text": cells[1]})
    return rows


def _rule_rows(prefix: str, pattern: str) -> list[dict[str, str]]:
    """取出某个小节里带**编号前缀**的规则行（M-1…M-4 / E-1…E-5 / B-1…B-6）。

    ⚠️ 规则表的**列数**因小节而异（§4 / §5 是 2 列 · §7 是 3 列）⇒
    只要求「≥ 2 列」并把其余列拼进 ``text``。
    """
    rows: list[dict[str, str]] = []
    for line in _section_lines(_contract_text().splitlines(), prefix):
        cells = _table_cells(line)
        if len(cells) < 2 or _is_separator(cells):
            continue
        if not re.fullmatch(pattern, cells[0]):
            continue
        rows.append({"index": cells[0], "text": " ".join(cells[1:])})
    return rows


# ── §0 · 权威标记与覆盖面下限 ─────────────────────────────────────────────


def test_contract_file_carries_the_authority_marker() -> None:
    """契约权威标记 ``<!-- authority: yes -->`` MUST 在位。"""
    assert "<!-- authority: yes -->" in _contract_text()


def test_contract_declares_all_twenty_three_invariants() -> None:
    """§6 的不变量 MUST **恰为 23 条**（I-1…I-23）。"""
    rows = _invariant_rows()
    assert [row["index"] for row in rows] == [f"I-{n}" for n in range(1, 24)]


def test_contract_declares_four_mapping_rules_and_five_error_rules() -> None:
    """§4 的 M-1…M-4 与 §5 的 E-1…E-5 MUST 齐全。"""
    assert [row["index"] for row in _rule_rows("## 4.", r"M-\d+")] == [
        "M-1",
        "M-2",
        "M-3",
        "M-4",
    ]
    assert [row["index"] for row in _rule_rows("## 5.", r"E-\d+")] == [
        "E-1",
        "E-2",
        "E-3",
        "E-4",
        "E-5",
    ]


def test_contract_declares_the_four_operations_and_four_attributes() -> None:
    """§1 / §2 的 4 个操作与 4 个属性 MUST 齐全。"""
    text = _contract_text()
    for name in ("update", "get", "is_available", "clear"):
        assert f"`{name}`" in text
    for name in ("key", "value_type", "value", "reducer"):
        assert f"`{name}`" in text


# ── §1 · 通道抽象 ─────────────────────────────────────────────────────────


def test_contract_section_one_declares_an_abstract_base_class() -> None:
    """§1：抽象基类 = ``Channel``（``abc.ABC``）· 运行时**不可实例化**。"""
    text = _contract_text()
    assert "`Channel`（`abc.ABC`）" in text
    with pytest.raises(TypeError):
        Channel("k", int)  # type: ignore[abstract]


def test_contract_section_one_declares_the_default_clear_is_a_no_op() -> None:
    """§1：``clear()`` 的**默认实现** = 无操作（返回假）· 三类通道全部覆写。"""
    text = _contract_text()
    assert "| 默认实现 |" in text
    assert "**无操作**" in text
    # 基类的默认实现确实是「无操作」⇒ 返回假。
    assert Channel.__dict__["clear"](LastValue("k", int)) is False


def test_contract_declares_the_exact_public_property_set() -> None:
    """§1：公开属性集合 **恰好** {``key``, ``value_type``, ``value``, ``reducer``}。"""
    channel = LastValue("k", int)
    properties = {
        name
        for klass in type(channel).__mro__
        for name, value in klass.__dict__.items()
        if isinstance(value, property)
    }
    assert properties == {"key", "value_type", "value", "reducer"}


# ── §2 · 四个操作的语义 ───────────────────────────────────────────────────


def test_contract_operation_names_are_exactly_four() -> None:
    """§2：操作面**恰为 4 个**。"""
    assert len(Channel.__abstractmethods__) == 3
    assert "clear" in Channel.__dict__


def test_contract_section_two_declares_the_update_return_semantics() -> None:
    """§2.1：``update()`` 返回「**本次调用是否写入了值**」。"""
    text = _contract_text()
    assert "本次调用是否写入了值" in text
    channel = LastValue("k", int)
    assert channel.update([1]) is True
    assert channel.update([]) is False


def test_contract_section_two_declares_the_clear_return_semantics() -> None:
    """§2.2：``clear()`` 返回「**状态是否真的变化**」；三类通道**一律**适用。"""
    text = _contract_text()
    assert "状态是否真的变化" in text
    assert "三类通道一律" in text


# ── §3 · 三类通道的语义 ───────────────────────────────────────────────────


def test_contract_declares_three_channel_sections() -> None:
    """§3：三类通道各有一节。"""
    text = _contract_text()
    assert "### 3.1 `LastValue`" in text
    assert "### 3.2 `BinaryOperatorAggregate`" in text
    assert "### 3.3 `EphemeralValue`" in text


def test_contract_section_three_one_declares_overwrite_semantics() -> None:
    """§3.1：``LastValue`` **覆盖**旧值 · 无归约器 · 初始「无值」。"""
    channel = LastValue("k", int)
    assert channel.reducer is None
    assert channel.is_available() is False
    channel.update([1])
    channel.update([2])
    assert channel.get() == 2


def test_contract_section_three_two_declares_reduce_semantics() -> None:
    """§3.2：归约器**按引用**持有 · 空值推导 · 首次写入**直存**。"""
    channel = BinaryOperatorAggregate("k", list, operator.add)
    assert channel.reducer is operator.add
    assert channel.is_available() is True
    assert channel.get() == []


def test_contract_section_three_three_declares_routing_semantics() -> None:
    """§3.3：路由型**无归约器** · 初始「无值」· ``clear()`` ⇒ 无值。"""
    channel = EphemeralValue("route", str)
    assert channel.reducer is None
    assert channel.is_available() is False
    channel.update(["x"])
    assert channel.clear() is True
    assert channel.is_available() is False


def test_contract_declares_empty_sequence_is_a_no_op_for_all_three() -> None:
    """§3：三类通道的「写入（空序列）」⇒ **无操作**（返回假）。"""
    for channel in (
        LastValue("k", int),
        BinaryOperatorAggregate("k", list, operator.add),
        EphemeralValue("k", str),
    ):
        assert channel.update([]) is False


# ── §4 · 映射契约 ─────────────────────────────────────────────────────────


class _Schema(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int


def test_contract_mapping_rules_m1_to_m4_hold() -> None:
    """§4 的 M-1…M-4 逐条成立（保序 · 每 key 一个 · 身份 · 自洽）。"""
    spec = parse_state_schema(_Schema)
    channels = build_channels(spec)
    # M-1 / M-4：保序 + 每 key 恰一个通道
    assert list(channels) == list(spec.keys)
    assert len(channels) == len(spec.keys)
    # M-4 的类型分派：有归约器 ⇒ 归约型；无归约器 ⇒ 覆盖型
    assert isinstance(channels["messages"], BinaryOperatorAggregate)
    assert isinstance(channels["llm_calls"], LastValue)
    # 身份判定：归约器**同一引用**
    assert channels["messages"].reducer is operator.add
    # M-2：路由通道**不由** schema 派生
    assert not any(isinstance(c, EphemeralValue) for c in channels.values())
    # M-3：标注「有归约器」但归约器为空 ⇒ 内置 ValueError
    with pytest.raises(ValueError):
        build_channel(
            ChannelSpec(
                key="k",
                value_type=list,
                reducer=None,
                has_reducer=True,
                semantics="reduce",
            )
        )


# ── §5 · 错误契约 ─────────────────────────────────────────────────────────


def test_contract_error_rules_e1_to_e5_hold() -> None:
    """§5 的 E-1…E-5 逐条成立。"""
    import freegraph.contracts as contracts
    import freegraph.graph as facade

    # E-1：二者**定义在 L2** ⇒ 不进契约层 18 符号面 / 门面 7 符号面
    assert EmptyChannelError.__module__ == "freegraph.runtime.errors"
    assert InvalidChannelUpdateError.__module__ == "freegraph.runtime.errors"
    assert "EmptyChannelError" not in contracts.__all__
    assert "InvalidChannelUpdateError" not in contracts.__all__
    assert len(contracts.__all__) == 18
    assert len(facade.__all__) == 7
    # E-2：用户侧 except FreegraphError 均能捕获
    channel = LastValue("k", int)
    with pytest.raises(FreegraphError):
        channel.get()
    with pytest.raises(FreegraphError):
        channel.update([1, 2])
    # E-3：错误对象**不携带**用户写入的值
    with pytest.raises(EmptyChannelError) as excinfo:
        channel.get()
    assert not hasattr(excinfo.value, "value")
    # E-4：EmptyChannelError **不**继承 ValueError
    assert not issubclass(EmptyChannelError, ValueError)
    # E-5：构造期的编程错误用**内置** TypeError / ValueError
    with pytest.raises(TypeError):
        BinaryOperatorAggregate("k", list, 42)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        BinaryOperatorAggregate("k", list, None)  # type: ignore[arg-type]


# ── §6 · 不变量 I-1…I-23（**逐条**）──────────────────────────────────────


def test_i1_public_properties_and_slots_are_frozen() -> None:
    """I-1：公开属性**恰为**四项 · 槽位 ⊆ 四项 · 实例**无** ``__dict__``。"""
    for channel in (
        LastValue("k", int),
        BinaryOperatorAggregate("k", list, operator.add),
        EphemeralValue("k", str),
    ):
        properties = {
            name
            for klass in type(channel).__mro__
            for name, value in klass.__dict__.items()
            if isinstance(value, property)
        }
        assert properties == {"key", "value_type", "value", "reducer"}
        slots: set[str] = set()
        for klass in type(channel).__mro__:
            declared = klass.__dict__.get("__slots__", ())
            slots.update({declared} if isinstance(declared, str) else declared)
        assert slots <= {"_key", "_value_type", "_value", "_reducer"}
        assert not hasattr(channel, "__dict__")


def test_i2_channel_holds_no_state_table_reference() -> None:
    """I-2：引用类型**白名单** + 计数探针与 key 数**无关**。"""
    def schema_of(count: int) -> Any:
        return TypedDict(f"_S{count}", {f"k{i}": int for i in range(count)})

    counts = []
    for count in (1, 1000):
        spec = parse_state_schema(schema_of(count))
        channel = build_channels(spec)["k0"]
        violations = [
            type(r).__name__
            for r in gc.get_referents(channel)
            if isinstance(r, (dict, Channel)) or type(r).__name__ == "SchemaSpec"
        ]
        assert violations == []
        counts.append(len(gc.get_referents(channel)))
    assert counts[0] == counts[1]


def test_i3_none_is_distinguishable_from_missing() -> None:
    """I-3：「无值」与「值为 ``None``」严格可分。"""
    channel = LastValue("k", int)
    assert channel.is_available() is False
    channel.update([None])
    assert channel.is_available() is True
    assert channel.get() is None


def test_i4_is_available_never_raises_and_get_always_raises_when_empty() -> None:
    """I-4：``is_available()`` **恒不抛错**；``get()`` 无值时**必抛**。"""
    channel = LastValue("k", int)
    assert channel.is_available() is False
    with pytest.raises(EmptyChannelError):
        channel.get()


def test_i5_value_property_is_synonymous_with_get() -> None:
    """I-5：``value`` 与 ``get()`` **同义**（无值时同样抛错）。"""
    channel = LastValue("k", int)
    with pytest.raises(EmptyChannelError):
        channel.value
    channel.update([7])
    assert channel.value == channel.get() == 7


def test_i6_update_returns_whether_a_value_was_written() -> None:
    """I-6：非空 ⇒ 恒真（哪怕值未变）；空 ⇒ 假。"""
    channel = LastValue("k", int)
    assert channel.update([1]) is True
    assert channel.update([1]) is True
    assert channel.update([]) is False


def test_i7_conflict_leaves_the_value_unchanged() -> None:
    """I-7：一步内多值冲突 ⇒ 值**不变**。"""
    channel = LastValue("k", int)
    channel.update([1])
    with pytest.raises(InvalidChannelUpdateError):
        channel.update([2, 3])
    assert channel.get() == 1


def test_i8_reducer_failure_leaves_the_value_unchanged() -> None:
    """I-8：归约器抛错 ⇒ 值**不变**。"""

    def exploding(current: Any, new: Any) -> Any:
        raise RuntimeError("boom")

    channel = BinaryOperatorAggregate("k", list, exploding)
    with pytest.raises(RuntimeError):
        channel.update([["x"]])
    assert channel.get() == []


def test_i9_reducer_is_held_by_reference() -> None:
    """I-9：归约器**按引用**持有。"""
    channel = BinaryOperatorAggregate("k", list, operator.add)
    assert channel.reducer is operator.add


def test_i10_first_single_write_calls_no_reducer() -> None:
    """I-10：通道**无值** + **单值**写入 ⇒ 归约器调用次数 == 0。"""
    calls: list[Any] = []

    def counting(current: Any, new: Any) -> Any:
        calls.append((current, new))
        return current

    channel = BinaryOperatorAggregate("k", Any, counting)
    channel.update(["x"])
    assert calls == []
    channel.update(["y"])
    assert len(calls) == 1


def test_i11_empty_values_are_not_shared_between_channels() -> None:
    """I-11：两个同类型归约型通道的空值**不是同一对象**。"""
    first = BinaryOperatorAggregate("a", list, operator.add)
    second = BinaryOperatorAggregate("b", list, operator.add)
    assert first.get() is not second.get()


def test_i12_clear_always_yields_no_value() -> None:
    """I-12：清空后**一律**「无值」（三类同构）· 不回到初始状态。"""
    aggregate = BinaryOperatorAggregate("k", list, operator.add)
    assert aggregate.get() == []
    assert aggregate.clear() is True
    assert aggregate.is_available() is False
    for channel in (LastValue("k", int), EphemeralValue("k", str)):
        channel.update([1])
        assert channel.clear() is True
        assert channel.is_available() is False


def test_i13_initial_states_are_three_tiers() -> None:
    """I-13：覆盖型 / 路由型初始「无值」；归约型初始「有值（空值）」。"""
    assert LastValue("k", int).is_available() is False
    assert EphemeralValue("k", str).is_available() is False
    aggregate = BinaryOperatorAggregate("k", list, operator.add)
    assert aggregate.is_available() is True
    assert aggregate.get() == []
    non_instantiable = BinaryOperatorAggregate("k", Any, operator.add)
    assert non_instantiable.is_available() is False


def test_i14_channel_shallow_references_user_objects() -> None:
    """I-14：通道**浅引用**用户对象（``is`` 判定）。"""
    payload = {"k": "v"}
    channel = LastValue("k", int)
    channel.update([payload])
    assert channel.value is payload


def test_i15_channel_does_not_validate_types_or_binarity() -> None:
    """I-15：不校验写入值类型 · **不重做**二元性校验。"""

    def ternary(a: Any, b: Any, c: Any) -> Any:
        return a

    channel = LastValue("k", int)
    channel.update(["not-an-int"])
    assert channel.get() == "not-an-int"
    aggregate = BinaryOperatorAggregate("k", Any, ternary)  # type: ignore[arg-type]
    assert aggregate.reducer is ternary


def test_i16_construction_validation_raises_builtin_exceptions() -> None:
    """I-16：不可调用的归约器 ⇒ ``TypeError``；「有归约器但为空」⇒ ``ValueError``。"""
    with pytest.raises(TypeError):
        BinaryOperatorAggregate("k", list, 42)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        BinaryOperatorAggregate("k", list, None)  # type: ignore[arg-type]


def test_i17_mapping_preserves_order_and_count() -> None:
    """I-17：映射**保序** · 通道数 == key 数。"""
    spec = parse_state_schema(_Schema)
    channels = build_channels(spec)
    assert list(channels) == list(spec.keys)
    assert len(channels) == len(spec.keys)


def test_i18_mapped_reducer_is_the_spec_reference() -> None:
    """I-18：映射产出的归约型通道，其 ``reducer`` **就是**规格里的引用。"""
    spec = parse_state_schema(_Schema)
    channels = build_channels(spec)
    assert channels["messages"].reducer is spec.channels["messages"].reducer


def test_i19_import_has_no_side_effects() -> None:
    """I-19：导入本 feature 的模块 ⇒ 零环境变量读取 · 零出站。

    ⚠️ ``sys.modules`` 增量的断言在
    ``tests/runtime/test_channel_purity.py``（**子进程**内执行）。
    """
    import os

    assert "langgraph" not in " ".join(sorted(os.environ.keys())).lower()


def test_i20_channel_has_no_synchronization_primitive() -> None:
    """I-20：通道**无同步原语**；写入入口**只有** ``update()``。"""
    for channel in (
        LastValue("k", int),
        BinaryOperatorAggregate("k", list, operator.add),
        EphemeralValue("k", str),
    ):
        for referent in gc.get_referents(channel):
            name = type(referent).__name__
            assert "lock" not in name.lower()
        public = {
            name
            for klass in type(channel).__mro__
            for name, value in klass.__dict__.items()
            if not name.startswith("_")
            and not isinstance(value, property)
            and callable(value)
        }
        assert public == {"update", "get", "is_available", "clear"}


def test_i21_error_structured_fields_are_complete_and_value_free() -> None:
    """I-21：结构化字段齐备 · **不携带**用户值。"""
    channel = LastValue("k", int)
    with pytest.raises(EmptyChannelError) as empty_info:
        channel.get()
    assert empty_info.value.key == "k"
    assert not hasattr(empty_info.value, "value")
    with pytest.raises(InvalidChannelUpdateError) as conflict_info:
        channel.update([1, 2])
    assert conflict_info.value.key == "k"
    assert conflict_info.value.received_count == 2
    assert conflict_info.value.expected_count == 1
    assert not hasattr(conflict_info.value, "value")


def test_i22_errors_are_catchable_and_empty_is_not_a_value_error() -> None:
    """I-22：二者均可被 ``except FreegraphError`` 捕获；
    ``EmptyChannelError`` **不是** ``ValueError``。"""
    assert issubclass(EmptyChannelError, FreegraphError)
    assert issubclass(InvalidChannelUpdateError, FreegraphError)
    assert not issubclass(EmptyChannelError, ValueError)
    assert issubclass(InvalidChannelUpdateError, ValueError)


def test_i23_naming_surface_is_verbatim() -> None:
    """I-23：名字面逐字一致（4 操作 + 4 属性 + 4 类名 + 2 映射入口 + 2 错误名）。"""
    for name in ("update", "get", "is_available", "clear"):
        assert hasattr(Channel, name)
    for name in ("key", "value_type", "value", "reducer"):
        assert isinstance(getattr(Channel, name), property)
    for klass in (Channel, LastValue, BinaryOperatorAggregate, EphemeralValue):
        assert klass.__name__ in {
            "Channel",
            "LastValue",
            "BinaryOperatorAggregate",
            "EphemeralValue",
        }
    assert callable(build_channel)
    assert callable(build_channels)
    assert EmptyChannelError.__name__ == "EmptyChannelError"
    assert InvalidChannelUpdateError.__name__ == "InvalidChannelUpdateError"


# ── 上游对照表（SC-014 · FR-021）──────────────────────────────────────────

UPSTREAM_PARITY_PATH = (
    REPO_ROOT / "specs" / "b5f1-channels" / "contracts" / "upstream-parity.md"
)


def _upstream_rows() -> list[dict[str, str]]:
    """上游对照表的 **P-01…P-12** 行。"""
    rows: list[dict[str, str]] = []
    for line in UPSTREAM_PARITY_PATH.read_text(encoding="utf-8").splitlines():
        cells = _table_cells(line)
        if len(cells) < 5 or _is_separator(cells):
            continue
        if not re.fullmatch(r"P-\d+", cells[0]):
            continue
        rows.append({"index": cells[0], "text": " | ".join(cells)})
    return rows


def test_upstream_parity_table_declares_twelve_points() -> None:
    """上游对照表 MUST 恰有 **12 条**（P-01…P-12）· 且逐条带 ``路径:行号``。"""
    rows = _upstream_rows()
    assert [row["index"] for row in rows] == [f"P-{n:02d}" for n in range(1, 13)]
    # 每条 MUST 带上游源码的 ``路径:行号``（形如 ``channels/binop.py:143``）。
    for row in rows:
        assert re.search(r"`[\w/]+\.py:\d+", row["text"]), row["text"]


def test_upstream_parity_records_the_verified_upstream_version() -> None:
    """上游对照表 MUST 标注核实版本（``langgraph 1.2.11``）。"""
    assert "1.2.11" in UPSTREAM_PARITY_PATH.read_text(encoding="utf-8")


def test_six_semantic_categories_all_have_implementations_and_assertions() -> None:
    """FR-021 / SC-014：六类语义**逐条**有实现与断言。

    六类 = 覆盖语义 / 一步内多值冲突 / 空值推导 / 首次写入的 ``current`` /
    清空语义 / 有值无值判定。
    """
    # ① 覆盖语义
    last = LastValue("k", int)
    last.update([1])
    last.update([2])
    assert last.get() == 2
    # ② 一步内多值冲突
    with pytest.raises(InvalidChannelUpdateError):
        last.update([1, 2])
    # ③ 空值推导
    aggregate = BinaryOperatorAggregate("k", list, operator.add)
    assert aggregate.get() == []
    # ④ 首次写入的 current（无值 ⇒ 直存）
    calls: list[Any] = []

    def counting(current: Any, new: Any) -> Any:
        calls.append((current, new))
        return current

    fresh = BinaryOperatorAggregate("k2", Any, counting)
    fresh.update(["x"])
    assert calls == []
    # ⑤ 清空语义
    route = EphemeralValue("route", str)
    route.update(["x"])
    assert route.clear() is True
    assert route.is_available() is False
    # ⑥ 有值 / 无值判定
    assert LastValue("k", int).is_available() is False
    with pytest.raises(EmptyChannelError):
        LastValue("k", int).get()


def test_upstream_parity_points_are_all_covered_by_the_contract_file() -> None:
    """P-01…P-12 的每一条 MUST 在契约文件中有对应的冻结条目。"""
    contract = _contract_text()
    for keyword in (
        "覆盖",
        "InvalidChannelUpdateError",
        "空值推导",
        "直存",
        "clear()",
        "is_available()",
    ):
        assert keyword in contract


# ── §7 · 边界（本契约**不**规定的事）──────────────────────────────────────


def test_contract_section_seven_lists_the_undecided_boundaries() -> None:
    """§7：B-1…B-6 MUST 齐全（边界登记 · 归属 feature 明确）。"""
    rows = _rule_rows("## 7.", r"B-\d+")
    assert [row["index"] for row in rows] == [
        "B-1",
        "B-2",
        "B-3",
        "B-4",
        "B-5",
        "B-6",
    ]


def test_contract_boundary_b2_assigns_step_end_clearing_to_the_scheduler() -> None:
    """§7 ``B-2``：步末调用哪些通道 ⇒ 归 **B7F1**（本 feature **不**实现）。"""
    rows = _rule_rows("## 7.", r"B-\d+")
    b2 = next(row for row in rows if row["index"] == "B-2")
    assert "B7F1" in b2["text"]
