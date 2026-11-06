# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 的**唯一数据与类型契约层**。

公开符号面**恰为 8 个**（见 ``contracts/public-api.md`` §0）——
不多、不少；本层不导出 ``Send`` 与 ``interrupt``（二者归 B2F1）。

本包**零** freegraph 内部 import、**零**第三方 import（仅标准库），
导入它不会连带加载任何内部层模块。
"""

from .errors import FreegraphError, GraphInterrupt, GraphRecursionError, InvalidUpdateError
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
]
