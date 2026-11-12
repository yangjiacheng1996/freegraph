# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**C4 稀疏状态读**的**独立回归测试** —— 属 **B5F2**（tasks T011）·
**节点边界口径**由 **B7F1** 追加（tasks T039 / T040 · 承接 **H-1**）。

**断言对象** = 读取层产出的**那个 dict**（它**就是**调度器将要交给节点的那个
dict）⇒ **不经由图执行**（B5F2 侧 · 本 feature 无调度循环）。

⚠️ **判定力度**：断言 MUST 是**否定式**的 ——

* ``"llm_calls" not in node_input``（**验收判据 A1** · 引文 §6）—— 空 channel
  的 key **MUST NOT** 出现在入参中；
* ``node_input.get("llm_calls", 0) == 0``（**验收判据 A2**）—— ``.get`` 必须
  返回 **default** 而非 ``None``。

⇒ 若写成「节点入参包含所有 schema key」则**等于没有防线**。

**B7F1 的追加（承接 **H-1** · FR-016 / FR-017）**：C4 的**契约边界**是
「**节点入参**」⇒ 本文件 MUST 有**两条**口径**并存**（裁定 13）：

* **读取层口径**（下方 · B5F2 交付）—— 守「稀疏读原语本身没坏」；
* **节点边界口径**（下方 · B7F1 追加）—— 守「**调度器交给节点的字典**没坏」
  ⇒ 让一个**订阅了「有值通道 + 无值通道」**的节点经**调度器**执行一次 ⇒ 断言
  它**实际收到**的入参不含无值通道的 key。

⚠️ **2026-11-12 · 上游对齐（P1-0-2）**：触发源**恒为边**（上游 ``branch:to:<node>``
· ``langgraph/graph/state.py:1531-1532``）⇒ 节点边界口径的夹具**必须**带**入口边**
（``edges={"__start__": ("reader",)}``）⇒ ``subscribes`` **只**决定「读哪些通道」。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from freegraph.runtime import (
    GraphSpec,
    NodeSpec,
    SchedulerState,
    build_channels,
    parse_state_schema,
    read_channels,
    run_super_step,
)


class MessagesSchema(TypedDict):
    """被测 schema（**有归约器** + **无归约器**各一）。"""

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


def test_c4_node_boundary_the_real_node_input_excludes_empty_channels() -> None:
    """**B7F1 的节点边界口径**（FR-016 · 承接 **H-1** · SC-009）。

    ⚠️ 让一个**订阅了「有值通道 + 无值通道」**的节点经**调度器**执行一次 ⇒
    断言它**实际收到**的入参：

    * ``"llm_calls" not in node_input``（**否定式**）；
    * ``node_input.get("llm_calls", 0) == 0``（返回 **default** 而非 ``None``）；
    * ``type(node_input) is dict``。

    ⚠️ **观测方式** MUST 沿用 **B5F2 FR-030** 的既有口径 —— 在**节点函数内部**
    把收到的字典**复制一份**留存（且该副本 MUST 取自**节点执行前** ⇒ 节点就地
    改写入参时，观测到的仍是原始入参）。
    """
    channels = build_channels(parse_state_schema(MessagesSchema))
    channels["messages"].update([["hi"]])
    captured: list[dict[str, Any]] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(dict(state))
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": NodeSpec(subscribes=(), run=lambda state: {}),
            "reader": NodeSpec(subscribes=("messages", "llm_calls"), run=node),
        },
        edges={"__start__": ("reader",)},
    )

    run_super_step(spec, SchedulerState())

    assert len(captured) == 1
    node_input = captured[0]
    assert type(node_input) is dict
    assert "llm_calls" not in node_input
    assert node_input.get("llm_calls", 0) == 0
    assert "messages" in node_input
