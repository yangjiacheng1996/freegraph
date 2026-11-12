# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B4F1 的**主断言** —— 状态 schema 解析 + 归约器提取。

覆盖 spec 的 FR-001 ~ FR-012 · FR-017 · FR-021 与 SC-001 ~ SC-003 ·
SC-006 · SC-008 ~ SC-010 · SC-014 · SC-016 · SC-017。

**隔离要求**（tasks T016 / T024）：

* ``from __future__ import annotations`` 的形态 MUST 落在**独立模块**
  ``tests/runtime/test_future_annotations.py`` ⇒ 本文件**不**开启未来注解
  （否则本文件内**所有** schema 的注解都变成字符串，且会与「注解不可解析」
  用例相互干扰 ⇒ 无法区分「真不可解析」与「作用域没解析到」）；
* ``typing_extensions.TypedDict`` 的正面路径 MUST 落在**独立模块**
  ``tests/runtime/test_typed_dict_variants.py``（pytest 收集期即 import
  ⇒ 进程内 ``sys.modules`` 必含之）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

import operator
from typing import Annotated, Any, NotRequired, Required, TypedDict

import pytest

from freegraph.contracts import FreegraphError
from freegraph.runtime import (
    ChannelSpec,
    InvalidSchemaError,
    SchemaSpec,
    parse_state_schema,
)

# ── US1 · 追加语义被正确识别（SC-001 · SC-009 · SC-010）─────────────────


def test_annotated_reducer_is_identified_by_identity() -> None:
    """SC-001 ①~④：身份判定 + 有归约器 + 语义标记 + 基类型。"""
    assert ChannelSpec.__dataclass_fields__.keys() == {
        "key",
        "value_type",
        "reducer",
        "has_reducer",
        "semantics",
        "required",
    }


def test_annotated_list_add_is_recognised_as_binary_reducer() -> None:
    class MessagesState(TypedDict):
        messages: Annotated[list, operator.add]

    spec = parse_state_schema(MessagesState)
    channel = spec.channels["messages"]

    assert channel.reducer is operator.add
    assert channel.has_reducer is True
    assert channel.semantics == "reduce"
    # ⚠️ **上游同款**（2026-11-12 P3）：``value_type`` 保留 ``Annotated`` 原样
    assert channel.value_type.__origin__ is list


def test_value_type_keeps_the_annotated_wrapper() -> None:
    """FR-002 · I-6：`value_type` = **原始注解**（**保留** ``Annotated`` · **上游同款**）。

    ⚠️ **2026-11-12 上游对齐 P3**：上游把**原始注解**交给通道
    （``LastValue(annotation)`` / ``BinaryOperatorAggregate(annotation)`` ·
    上游 ``langgraph/graph/state.py:1862-1872``）⇒ 通道的 ``typ`` **带** ``Annotated``
    ⇒ freegraph 的 ``value_type`` **同款**。
    ⇒ **空值推导**那一侧仍由 B5F1 的宽口径剥离负责（上游 ``binop.py:22-30``）⇒ 两端口径一致。
    """

    class Generic(TypedDict):
        messages: Annotated[list[int], operator.add]

    spec = parse_state_schema(Generic)
    value_type = spec.channels["messages"].value_type
    assert getattr(value_type, "__metadata__", None) is not None
    assert value_type.__origin__ == list[int]


def test_reducer_is_held_by_reference_and_never_invoked() -> None:
    """SC-009：按引用持有（**身份**）· 解析期调用次数 == 0。"""
    calls: list[int] = []

    def counting_reducer(current: Any, new: Any) -> Any:  # noqa: ANN401
        calls.append(1)
        return current

    class Schema(TypedDict):
        messages: Annotated[list, counting_reducer]

    spec = parse_state_schema(Schema)

    assert spec.channels["messages"].reducer is counting_reducer
    assert calls == []


def test_same_callable_shared_by_two_keys_keeps_one_reference() -> None:
    """同一个 callable 被两个 key 共用 ⇒ 两条规格持**同一引用**（不复制）。"""

    class Schema(TypedDict):
        first: Annotated[list, operator.add]
        second: Annotated[list, operator.add]

    spec = parse_state_schema(Schema)

    assert spec.channels["first"].reducer is operator.add
    assert spec.channels["second"].reducer is operator.add
    assert spec.channels["first"].reducer is spec.channels["second"].reducer


def test_stateful_reducer_is_not_reset_by_parsing() -> None:
    """有状态的归约器（闭包 / 可变默认参数）⇒ 按引用持有、**不重置**状态。"""
    state: list[int] = [1]

    def stateful_reducer(current: Any, new: Any) -> Any:  # noqa: ANN401
        state.append(new)
        return state

    class Schema(TypedDict):
        messages: Annotated[list, stateful_reducer]

    spec = parse_state_schema(Schema)
    spec.channels["messages"].reducer  # noqa: B018 —— 只取引用，不调用

    assert state == [1]
    assert spec.channels["messages"].reducer is stateful_reducer


def test_required_wrapped_reducer_is_not_missed() -> None:
    """SC-010 · 裁定 4：`Required[...]` 包裹的归约器**不漏**。"""

    class Schema(TypedDict):
        messages: Required[Annotated[list, operator.add]]

    spec = parse_state_schema(Schema)

    assert spec.channels["messages"].reducer is operator.add
    assert spec.channels["messages"].has_reducer is True
    assert spec.channels["messages"].semantics == "reduce"


def test_notrequired_wrapped_reducer_is_not_missed() -> None:
    """SC-010 · 裁定 4：`NotRequired[...]` 包裹的归约器**不漏**。"""

    class Schema(TypedDict):
        messages: NotRequired[Annotated[list, operator.add]]

    spec = parse_state_schema(Schema)

    assert spec.channels["messages"].reducer is operator.add
    assert spec.channels["messages"].has_reducer is True
    assert spec.channels["messages"].semantics == "reduce"


# ── US2 · 计数型 key 走默认覆盖（SC-002 · SC-008 · SC-016）───────────────


def test_key_without_annotated_is_overwrite_semantics() -> None:
    """SC-002 · FR-006：无 `Annotated` ⇒ 归约器为空 + 语义 `overwrite`。"""

    class Schema(TypedDict):
        llm_calls: int

    spec = parse_state_schema(Schema)
    channel = spec.channels["llm_calls"]

    assert channel.reducer is None
    assert channel.has_reducer is False
    assert channel.semantics == "overwrite"


def test_reduce_and_overwrite_keys_do_not_cross_contaminate() -> None:
    class Schema(TypedDict):
        messages: Annotated[list, operator.add]
        llm_calls: int

    spec = parse_state_schema(Schema)

    assert spec.channels["messages"].semantics == "reduce"
    assert spec.channels["llm_calls"].semantics == "overwrite"
    assert spec.channels["messages"].has_reducer is True
    assert spec.channels["llm_calls"].has_reducer is False


def test_channel_count_equals_key_count_including_inherited_keys() -> None:
    """SC-008 · I-1：规格条数 == schema 的 key 数（含继承链）。"""

    class Base(TypedDict):
        b1: int
        b2: str

    class Child(Base):
        c1: float

    spec = parse_state_schema(Child)

    assert len(spec.channels) == len(spec.keys) == 3
    assert set(spec.channels) == {"b1", "b2", "c1"}


def test_channels_keep_declaration_order_with_inherited_keys_first() -> None:
    """FR-002 · research D-10：父类 key 在前 · 同名覆盖保持原位。"""

    class Base(TypedDict):
        b1: int
        b2: str

    class Child(Base):
        b2: int
        c1: float

    spec = parse_state_schema(Child)

    assert spec.keys == ("b1", "b2", "c1")
    assert tuple(spec.channels) == ("b1", "b2", "c1")
    assert spec.channels["b2"].value_type is int


def test_slots_pseudo_key_is_skipped() -> None:
    """SC-008 · 裁定 12：名为 `__slots__` 的伪 key **不计入**条数。"""

    class Schema(TypedDict):
        __slots__: str
        real: int

    spec = parse_state_schema(Schema)

    assert spec.keys == ("real",)
    assert len(spec.channels) == 1


def test_empty_typed_dict_yields_zero_channels() -> None:
    """空 TypedDict（零个 key）⇒ 零条规格（**合法** · 不报错）。"""

    class Empty(TypedDict):
        pass

    spec = parse_state_schema(Empty)

    assert spec.keys == ()
    assert len(spec.channels) == 0
    assert spec.to_dict() == {"keys": [], "channels": []}


def test_required_flags_follow_typed_dict_sets() -> None:
    """SC-016 · FR-021 ③：必填性标记**照抄** `__required_keys__`。"""

    class TotalFalse(TypedDict, total=False):
        a: int
        b: str

    class Mixed(TypedDict):
        c: int
        d: NotRequired[str]
        e: Required[float]

    total_false_spec = parse_state_schema(TotalFalse)
    assert {k: total_false_spec.channels[k].required for k in total_false_spec.keys} == {
        "a": False,
        "b": False,
    }

    mixed_spec = parse_state_schema(Mixed)
    assert {k: mixed_spec.channels[k].required for k in mixed_spec.keys} == {
        "c": True,
        "d": False,
        "e": True,
    }


def test_missing_required_key_is_not_rejected() -> None:
    """FR-021 ②：本 feature **不执行任何必填性校验**（校验归 B7F3）。"""

    class Schema(TypedDict):
        required_key: int
        optional_key: NotRequired[str]

    spec = parse_state_schema(Schema)

    assert spec.channels["required_key"].required is True
    assert spec.channels["optional_key"].required is False
    assert len(spec.channels) == 2


# ── US3 · 别的 `Annotated` 用法不被误判（SC-003）─────────────────────────


def test_non_callable_trailing_metadata_is_not_a_reducer() -> None:
    """SC-003 ①：末位**非** callable ⇒ 无归约器 · 解析**成功**。"""

    class Schema(TypedDict):
        note: Annotated[int, "说明文字"]

    spec = parse_state_schema(Schema)
    channel = spec.channels["note"]

    assert channel.has_reducer is False
    assert channel.semantics == "overwrite"
    assert channel.reducer is None


def test_only_the_last_metadata_entry_is_inspected() -> None:
    """SC-003 ② · FR-005：多条目元数据 ⇒ **只认末位**。"""

    class Schema(TypedDict):
        history: Annotated[list, "描述", operator.add]

    spec = parse_state_schema(Schema)

    assert spec.channels["history"].reducer is operator.add
    assert spec.channels["history"].semantics == "reduce"


def test_class_with_two_positional_init_args_is_accepted_as_reducer() -> None:
    """澄清 Q6 · 裁定 9：类**不**特殊排除 ⇒ 机械判定（`__init__` 恰 2 参 ⇒ 接受）。"""

    class ClassTwoArgInit:
        def __init__(self, a: Any, b: Any) -> None:  # noqa: ANN001
            self.a = a
            self.b = b

    class Schema(TypedDict):
        value: Annotated[list, ClassTwoArgInit]

    spec = parse_state_schema(Schema)

    assert spec.channels["value"].reducer is ClassTwoArgInit
    assert spec.channels["value"].semantics == "reduce"


def test_class_with_non_binary_init_is_rejected() -> None:
    """澄清 Q6 · 裁定 9：`__init__` 非 2 位置参的类 ⇒ **拒绝**（抛错）。"""

    class ClassNoInit:
        pass

    class Schema(TypedDict):
        value: Annotated[list, ClassNoInit]

    with pytest.raises(InvalidSchemaError) as excinfo:
        parse_state_schema(Schema)

    assert excinfo.value.key == "value"
    assert excinfo.value.reason == "reducer_not_binary"


def test_callable_instance_with_two_positional_args_is_accepted() -> None:
    """澄清 Q6：可调用实例按**机械判定**处理。"""

    class CallableInstance:
        def __call__(self, a: Any, b: Any) -> Any:  # noqa: ANN401
            return a

    instance = CallableInstance()

    class Schema(TypedDict):
        value: Annotated[list, instance]

    spec = parse_state_schema(Schema)

    assert spec.channels["value"].reducer is instance
    assert spec.channels["value"].semantics == "reduce"


def test_callable_instance_with_keyword_only_call_is_rejected() -> None:
    """澄清 Q6：`__call__(self, *, a, b)` ⇒ 0 个位置参数 ⇒ **拒绝**。"""

    class CallableKwOnlyInstance:
        def __call__(self, *, a: Any, b: Any) -> Any:  # noqa: ANN401
            return a

    instance = CallableKwOnlyInstance()

    class Schema(TypedDict):
        value: Annotated[list, instance]

    with pytest.raises(InvalidSchemaError) as excinfo:
        parse_state_schema(Schema)

    assert excinfo.value.key == "value"
    assert excinfo.value.reason == "reducer_not_binary"


# ── US4 · 写错的 schema 在解析期就报错（SC-006 · SC-014 · SC-017）────────


@pytest.mark.parametrize(
    ("form_name", "candidate"),
    [
        ("three_positional", lambda a, b, c: None),
        ("one_positional", lambda a: None),
        ("builtin_type", str),
        ("varargs_only_one_positional", lambda a, *args: None),
    ],
)
def test_non_binary_candidates_are_rejected(form_name: str, candidate: Any) -> None:
    """SC-014 · FR-017：五类非二元候选 ⇒ **抛错**（MUST NOT 静默降级）。"""
    assert form_name  # 参数名即判据的类别标识（便于失败时定位）

    class Schema(TypedDict):
        bad: Annotated[int, candidate]

    with pytest.raises(InvalidSchemaError) as excinfo:
        parse_state_schema(Schema)

    assert excinfo.value.key == "bad"
    assert excinfo.value.reason == "reducer_not_binary"


def test_class_with_non_binary_init_is_one_of_the_negative_cases() -> None:
    """SC-014 · FR-017：类（`__init__` **非 2 个位置参数**者）⇒ 抛错。"""

    class ClassOneArgInit:
        def __init__(self, a: Any) -> None:  # noqa: ANN001
            self.a = a

    class Schema(TypedDict):
        bad: Annotated[int, ClassOneArgInit]

    with pytest.raises(InvalidSchemaError) as excinfo:
        parse_state_schema(Schema)

    assert excinfo.value.key == "bad"
    assert excinfo.value.reason == "reducer_not_binary"


def test_inputs_without_annotations_are_rejected() -> None:
    """SC-006 · FR-007 ①：**无** ``__annotations__`` ⇒ ``not_a_state_schema`` + ``key is None``。

    ⚠️ **2026-11-12 上游对齐 P3**：上游的判据**只有一条** ——「**有** ``__annotations__``」
    （上游 ``langgraph/graph/state.py:1818``）⇒ **pydantic 模型 / dataclass / 普通类**
    **一律接受** ⇒ freegraph 采**同一条**判据（**放宽**）。
    ⇒ 剩下**无** ``__annotations__`` 的对象被拒（上游对这类建**单根** ``__root__`` 通道 ⇒
    该形态的运行期语义归 **B7F1 / B8F1**）。
    """

    candidates = [
        {},
        {"a": 1},
        dict[str, int],
    ]

    for candidate in candidates:
        with pytest.raises(InvalidSchemaError) as excinfo:
            parse_state_schema(candidate)

        assert excinfo.value.reason == "not_a_state_schema"
        assert excinfo.value.key is None


def test_real_pydantic_model_is_accepted_when_available() -> None:
    """SC-006：`pydantic` 形态的**真身**（若环境已装）⇒ **被接受**（**上游同款**）。

    ⚠️ **2026-11-12 上游对齐 P3**：上游的判据**只有**「有 ``__annotations__``」
    （上游 ``langgraph/graph/state.py:1818``）⇒ pydantic 模型**直接可解析**。

    ⚠️ ``importorskip`` MUST 置于**测试函数内**（模块级 skip 会连带跳过
    本文件内**其余全部**用例）。
    """
    pydantic = pytest.importorskip("pydantic")

    class Model(pydantic.BaseModel):
        value: int

    spec = parse_state_schema(Model)
    assert "value" in spec.channels
    assert spec.channels["value"].value_type is int


def test_unresolvable_annotation_names_the_offending_key() -> None:
    """SC-006 · FR-007 ③：注解不可解析 ⇒ `annotation_unresolvable` + 指名 key。

    ⚠️ MUST 用**显式字符串注解**构造（非未来注解下 ``Annotated[...]`` 是
    立即求值的表达式 ⇒ 会在类定义时就抛 ``NameError`` · research D-04）。
    """
    assert "Missing" not in globals()

    class Schema(TypedDict):
        bad: "Annotated[list[Missing], operator.add]"

    with pytest.raises(InvalidSchemaError) as excinfo:
        parse_state_schema(Schema)

    assert excinfo.value.key == "bad"
    assert excinfo.value.reason == "annotation_unresolvable"


def test_unresolvable_annotation_on_parent_class_names_the_offending_key() -> None:
    """research D-04：坏注解放在**父类**上 ⇒ 仍 MUST 指名 `bad`。"""

    class Parent(TypedDict):
        bad: "Annotated[list[Missing], operator.add]"

    class Child(Parent):
        fine: int

    with pytest.raises(InvalidSchemaError) as excinfo:
        parse_state_schema(Child)

    assert excinfo.value.key == "bad"
    assert excinfo.value.reason == "annotation_unresolvable"


def test_only_the_first_problem_is_reported() -> None:
    """SC-006 · FR-007 ④ · 澄清 Q3：快速失败 —— **只报第一个**问题。"""

    class Schema(TypedDict):
        bad_one: Annotated[int, lambda a, b, c: None]
        bad_two: Annotated[int, lambda a: None]

    with pytest.raises(InvalidSchemaError) as excinfo:
        parse_state_schema(Schema)

    assert excinfo.value.key == "bad_one"
    assert excinfo.value.reason == "reducer_not_binary"


def test_error_carries_structured_fields_and_closed_reason_domain() -> None:
    """SC-017：字段齐备率 == 100% · 原因码 ∈ **封闭集合**。"""
    from freegraph.runtime.errors import SCHEMA_ERROR_REASONS

    class Bad(TypedDict):
        bad: Annotated[int, lambda a, b, c: None]

    class NotDict:
        pass

    # ⚠️ **2026-11-12 上游对齐 P3**：空类（无注解）**被接受**（Python 3.10+ 自动给
    # 空 ``__annotations__``）⇒ 产出**零条**通道（**合法** · B4F1 的既有口径）；
    # ⇒ 被拒的是**根本不是类**的对象（``{}`` / ``dict[str, int]`` / 实例）。

    class Unresolvable(TypedDict):
        bad: "Annotated[list[Missing], operator.add]"

    cases = [
        (Bad, "bad", "reducer_not_binary"),
        ({}, None, "not_a_state_schema"),
        (Unresolvable, "bad", "annotation_unresolvable"),
    ]

    for schema, expected_key, expected_reason in cases:
        with pytest.raises(InvalidSchemaError) as excinfo:
            parse_state_schema(schema)

        error = excinfo.value
        assert error.key == expected_key
        assert error.reason == expected_reason
        assert error.reason in SCHEMA_ERROR_REASONS
        assert hasattr(error, "key")
        assert hasattr(error, "reason")


def test_error_is_catchable_through_base_classes() -> None:
    """SC-006 · FR-007 ⑤：`except FreegraphError` 与 `except ValueError` **均**可捕获。"""

    class Bad(TypedDict):
        bad: Annotated[int, lambda a, b, c: None]

    with pytest.raises(FreegraphError):
        parse_state_schema(Bad)

    with pytest.raises(ValueError):
        parse_state_schema(Bad)


def test_error_message_names_the_offending_key() -> None:
    """SC-006：消息 MUST 指名出错 key（消息只是摘要 · 结构化字段承载细节）。"""

    class Bad(TypedDict):
        bad: Annotated[int, lambda a, b, c: None]

    with pytest.raises(InvalidSchemaError) as excinfo:
        parse_state_schema(Bad)

    assert "bad" in str(excinfo.value)


def test_bare_builtin_exceptions_are_never_raised() -> None:
    """FR-007：MUST NOT 抛裸 `TypeError` / `NameError` / `AttributeError`。"""

    class Bad(TypedDict):
        bad: Annotated[int, lambda a, b, c: None]

    class Unresolvable(TypedDict):
        bad: "Annotated[list[Missing], operator.add]"

    for schema in (Bad, Unresolvable, {"a": 1}):
        with pytest.raises(InvalidSchemaError):
            parse_state_schema(schema)


# ── 产物形态（FR-010 · FR-020 · I-2 · I-3）───────────────────────────────


def test_has_reducer_and_semantics_are_consistent() -> None:
    """I-3：`has_reducer == (semantics == "reduce")`。"""

    class Schema(TypedDict):
        messages: Annotated[list, operator.add]
        llm_calls: int

    spec = parse_state_schema(Schema)

    for key in spec.keys:
        channel = spec.channels[key]
        assert channel.has_reducer == (channel.semantics == "reduce")
        assert (channel.reducer is None) == (channel.has_reducer is False)


def test_schema_spec_keys_and_channels_are_consistent() -> None:
    """I-2：`keys` 与 `channels` 的键集合恒等 · 迭代序一致。"""

    class Schema(TypedDict):
        messages: Annotated[list, operator.add]
        llm_calls: int

    spec = parse_state_schema(Schema)

    assert isinstance(spec, SchemaSpec)
    assert set(spec.keys) == set(spec.channels)
    assert tuple(spec.channels) == spec.keys
