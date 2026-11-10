# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**C4 稀疏状态读**的**独立回归测试** —— 属 **B5F2**（tasks T011）。

**断言对象** = 读取层产出的**那个 dict**（它**就是**调度器将要交给节点的那个
dict）⇒ **不经由图执行**（本 feature 无调度循环 · 属 **B7F1**）。

⚠️ **判定力度**：断言 MUST 是**否定式**的 ——

* ``"llm_calls" not in node_input``（**验收判据 A1** · 引文 §6）—— 空 channel
  的 key **MUST NOT** 出现在入参中；
* ``node_input.get("llm_calls", 0) == 0``（**验收判据 A2**）—— ``.get`` 必须
  返回 **default** 而非 ``None``。

⇒ 若写成「节点入参包含所有 schema key」则**等于没有防线**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from freegraph.runtime import build_channels, parse_state_schema, read_channels


class MessagesSchema(TypedDict):
    """被测 schema（**有归约器** + **无归约器** 各一）。"""

    messages: Annotated[list, operator.add]
    llm_calls: int


def test_c4_sparse_state_read_excludes_empty_channels() -> None:
    """SC-001 · SC-002 · FR-012 · 验收判据 **A1 / A2**（**否定式**断言）。

    * ``"llm_calls" not in node_input``；
    * ``node_input.get("llm_calls", 0) == 0``；
    * ``type(node_input) is dict``。
    """
    channels = build_channels(parse_state_schema(MessagesSchema))
    channels["messages"].update([["hi"]])

    node_input = read_channels(channels)

    assert type(node_input) is dict
    assert "llm_calls" not in node_input
    assert node_input.get("llm_calls", 0) == 0
