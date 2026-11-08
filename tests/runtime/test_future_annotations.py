# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**未来注解形态**的隔离测试模块 —— B4F1（tasks T016 / T024）。

⚠️ **隔离理由**（tasks T016 · 2026-11-08 分析轮）：
``from __future__ import annotations`` 会让**整份文件**的注解都变成字符串
⇒ MUST 与其它用例**物理隔离**（否则本仓库既有的 ``test_schema_parse.py``
内**所有** schema 的注解都会变成字符串，且会与「注解不可解析」用例
**相互干扰** ⇒ 无法区分「真不可解析」与「作用域没解析到」）。

覆盖：

* **T016** —— 未来注解下**仍能解析出归约器**（裁定 5 · FR-009）；
* **T024** —— 未来注解下的 key ⇒ **一律** ``required is True``
  （FR-021 ③ —— CPython 的 TypedDict 机制识别不出字符串里的
  ``Required`` / ``NotRequired`` ⇒ freegraph **照抄**该结果）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Annotated, NotRequired, TypedDict

from freegraph.runtime import parse_state_schema


class MessagesState(TypedDict):
    """未来注解下的 schema（``Annotated[list, operator.add]``）。"""

    messages: Annotated[list, operator.add]
    llm_calls: int


class OptionalState(TypedDict):
    """未来注解下的 ``NotRequired`` —— CPython **识别不出** ⇒ 一律必选。"""

    a: int
    b: NotRequired[str]


def test_reducer_is_still_extracted_under_future_annotations() -> None:
    """T016 · SC-010：未来注解下**仍能解析出归约器**（且身份保持）。"""
    spec = parse_state_schema(MessagesState)
    channel = spec.channels["messages"]

    assert channel.reducer is operator.add
    assert channel.has_reducer is True
    assert channel.semantics == "reduce"


def test_value_type_is_resolved_to_a_type_not_a_string() -> None:
    """裁定 5：未来注解下 ``value_type`` MUST 是**类型对象**（不是字符串）。"""
    spec = parse_state_schema(MessagesState)

    assert spec.channels["messages"].value_type is list
    assert spec.channels["llm_calls"].value_type is int


def test_all_keys_are_required_under_future_annotations() -> None:
    """T024 · FR-021 ③：未来注解下 key ⇒ **一律** ``required is True``。

    ⚠️ 这是**上游行为**（CPython 的 TypedDict 机制识别不出字符串里的
    ``Required`` / ``NotRequired``）⇒ freegraph **照抄**，MUST NOT 自造
    判定逻辑。
    """
    spec = parse_state_schema(OptionalState)

    assert {key: spec.channels[key].required for key in spec.keys} == {
        "a": True,
        "b": True,
    }


def test_keys_and_channels_stay_consistent_under_future_annotations() -> None:
    """SC-008 · I-2：未来注解下保序与条数仍然成立。"""
    spec = parse_state_schema(MessagesState)

    assert spec.keys == ("messages", "llm_calls")
    assert len(spec.channels) == len(spec.keys) == 2
