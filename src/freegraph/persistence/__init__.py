# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L4 持久化层 · **公开包** —— 属 **B14F1**。

公开面只有三个符号：

* :class:`MemorySaver` —— 进程内 checkpointer（开发 / 调试定位）；
* ``InMemorySaver`` —— ``MemorySaver`` 的同一对象别名；
* :class:`CheckpointTuple` —— ``get_tuple`` / ``list`` 的读侧载体。

**依赖纪律**（L4）：只依赖 L1 ``freegraph.contracts`` + 标准库；MUST NOT import
L2 / L3 / L5；零第三方依赖、零环境变量、零出站。门面 ``freegraph.graph``
**MUST NOT** 转出本包符号（G18）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from ._types import CheckpointTuple
from .memory import InMemorySaver, MemorySaver

__all__ = ["MemorySaver", "InMemorySaver", "CheckpointTuple"]
