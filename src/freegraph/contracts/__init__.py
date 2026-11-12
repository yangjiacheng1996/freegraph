# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 的**唯一数据与类型契约层**。

公开符号面**恰为 20 个**（见 ``contracts/public-api.md`` §0）——
⚠️ **2026-11-12 上游对齐 P3**：新增 ``Interrupt`` 与 ``PregelTask``（**上游同款** ·
上游 ``langgraph/types.py:575-620`` / ``:637-646``）⇒ **C17** 的 ``.value`` / ``.id``
终于有了**类型载体** ⇒ 快照的 ``tasks`` / ``interrupts`` 元素类型也随之上游化。
不多、不少；本层不导出 ``Send`` 与 ``interrupt``
（二者归 **v2**：B11F1 / B10F1，本 feature **不导出**）。

本包**零** freegraph 内部 import、**零**第三方 import（仅标准库），
导入它不会连带加载任何内部层模块。
"""

from .errors import FreegraphError, GraphInterrupt, GraphRecursionError, InvalidUpdateError
from .graph import Edge, Graph, Node
from .protocols import Checkpointer, CompiledGraph, NodeFunc, Store, TraceSink
from .trace import Span, TraceQuery
from .types import (
    Command,
    Interrupt,
    PregelTask,
    RunConfig,
    StateDict,
    StateSnapshot,
)

__all__ = [
    "StateDict",
    "Command",
    "StateSnapshot",
    "RunConfig",
    "Interrupt",
    "PregelTask",
    "FreegraphError",
    "InvalidUpdateError",
    "GraphRecursionError",
    "GraphInterrupt",
    "NodeFunc",
    "Checkpointer",
    "TraceSink",
    "Store",
    "CompiledGraph",
    "Graph",
    "Node",
    "Edge",
    "Span",
    "TraceQuery",
]
