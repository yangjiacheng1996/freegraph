# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 的**唯一数据与类型契约层**。

公开符号面**恰为 18 个**（见 ``contracts/public-api.md`` §0）——
不多、不少；本层不导出 ``Send`` 与 ``interrupt``
（二者归 **v2**：B11F1 / B10F1，本 feature **不导出**）。

本包**零** freegraph 内部 import、**零**第三方 import（仅标准库），
导入它不会连带加载任何内部层模块。
"""

from .errors import FreegraphError, GraphInterrupt, GraphRecursionError, InvalidUpdateError
from .graph import Edge, Graph, Node
from .protocols import Checkpointer, CompiledGraph, NodeFunc, Store, TraceSink
from .trace import Span, TraceQuery
from .types import Command, RunConfig, StateDict, StateSnapshot

__all__ = [
    "StateDict",
    "Command",
    "StateSnapshot",
    "RunConfig",
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
