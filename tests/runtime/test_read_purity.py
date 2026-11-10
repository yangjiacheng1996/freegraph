# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**读取层**的纯净性用例 —— 属 **B5F2**（tasks T026 / T027）。

覆盖的判定：

* **零副作用**（**必须在子进程**执行 ⇒ 复用既有 ``tests/runtime/conftest.py``
  的 ``run_in_subprocess`` 夹具 · **既有 conftest 零改动**）：
  ``sys.modules`` 增量中非标准库条目数 == **0** · 环境变量读取次数 == **0** ·
  出站连接次数 == **0**（FR-020 / FR-022 / FR-023 · SC-010 / SC-016）；
* **副本的纯净**（``copy.copy`` 的结果）：副本**无** ``__dict__``（B5F1 的
  ``__slots__`` 纪律不被破坏）· 副本的**归约器与原通道同一引用**（I-6 / I-7）；
* **零污染**：读取**前后**通道的**绑定与可用性判定**（``is_available()`` 的
  **结果** + ``get()`` 的**取值**）**不变**（I-5 · 作用域见 FR-009 / 裁定 29）。

⚠️ **MUST NOT** 断言「值对象逐字相等」——「**就地修改型**归约器改写值对象」
属**已知面**（MUST **NOT** 计入该判据 · MUST **NOT** 修）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import copy
import operator
from typing import Annotated, TypedDict

from freegraph.runtime import (
    BinaryOperatorAggregate,
    build_channels,
    local_read,
    parse_state_schema,
)


class PuritySchema(TypedDict):
    """被测 schema（**有归约器** + **无归约器**各一）。"""

    messages: Annotated[list, operator.add]
    llm_calls: int


def _channels() -> dict:
    """构造一份手写通道状态。"""
    channels = build_channels(parse_state_schema(PuritySchema))
    channels["messages"].update([["old"]])
    return channels


# ── T026 · 副本的纯净（I-6 / I-7 / I-5）──────────────────────────────


def test_channel_copy_has_no_instance_dict() -> None:
    """**I-6**：副本**无** ``__dict__`` ⇒ B5F1 的 ``__slots__`` 纪律不被破坏。"""
    channel = BinaryOperatorAggregate(
        key="messages", value_type=list, reducer=operator.add
    )

    duplicate = copy.copy(channel)

    assert not hasattr(duplicate, "__dict__")
    assert not hasattr(channel, "__dict__")


def test_channel_copy_keeps_the_very_same_reducer_reference() -> None:
    """**I-7**：副本的归约器与原通道**同一引用**。"""
    channel = BinaryOperatorAggregate(
        key="messages", value_type=list, reducer=operator.add
    )

    duplicate = copy.copy(channel)

    assert duplicate.reducer is channel.reducer


def test_binding_and_availability_are_unchanged_by_a_fresh_read() -> None:
    """**I-5**：读取**前后**通道的**绑定与可用性判定****不变**。

    ⚠️ **MUST NOT** 断言「值对象逐字相等」——**就地修改型**归约器改写值对象
    属**已知面**（MUST **NOT** 计入本判据 · MUST **NOT** 修）。
    """
    channels = _channels()
    before = [
        (key, channel.is_available(), channel.get())
        for key, channel in channels.items()
        if channel.is_available()
    ]

    local_read(channels, {"messages": [["new"]]}, fresh=True)

    after = [
        (key, channel.is_available(), channel.get())
        for key, channel in channels.items()
        if channel.is_available()
    ]
    assert after == before


def test_fresh_view_equals_the_manually_computed_copy_based_view() -> None:
    """读取层的 fresh 视图 MUST 与「**手工按副本法算出**的视图」**逐字相等**。

    ⇒ 证明实现走的是**副本法**（``copy.copy`` ⇒ 副本上 ``update`` ⇒ 从副本读）
    ⇒ 而**不是**「就地改原通道再读回来」。
    """
    channels = _channels()
    writes = {"messages": [["new"]]}

    duplicate = copy.copy(channels["messages"])
    duplicate.update(writes["messages"])
    expected = {"messages": duplicate.get()}

    assert local_read(channels, writes, fresh=True) == expected


# ── T027 · 零副作用（**子进程** · SC-010 / SC-016）──────────────────────

_ZERO_SIDE_EFFECT_SOURCE = '''
import json

before = snapshot_modules()

import freegraph.runtime.read

payload = {
    "new_non_stdlib": non_stdlib_delta(before),
    "third_party": third_party_modules(),
    "read_exports": sorted(freegraph.runtime.read.__all__),
}
payload["__counters__"] = dict(COUNTERS)
print(json.dumps(payload))
'''


def test_reading_layer_has_no_side_effects(run_in_subprocess) -> None:
    """SC-010 / SC-016 · FR-020 / FR-022 / FR-023：读取层**零副作用**。

    * ``sys.modules`` 增量的**非标准库**条目数 **== 0**；
    * **环境变量读取次数 == 0**（三条读取路径全覆盖）；
    * **出站连接次数 == 0**（两个入口全覆盖）。

    ⚠️ **必须在子进程内执行** —— 测试进程自身已导入 pytest ⇒ 同进程
    ``sys.modules`` 不可作依据（沿用 B1F1 / B3F1 / B4F1 的既有口径）。
    """
    result = run_in_subprocess(_ZERO_SIDE_EFFECT_SOURCE)

    assert result["new_non_stdlib"] == []
    assert result["third_party"] == []
    assert result["env_reads"] == 0
    assert result["egress"] == 0
    assert result["read_exports"] == ["local_read", "read_channels"]
