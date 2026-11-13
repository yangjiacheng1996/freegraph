# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 的**唯一公开 API 门面**。

本模块是 freegraph 对外的**唯一入口**（FR-001）——用户从这里取到
``StateGraph`` / ``START`` / ``END`` / ``Command`` / ``Send`` / ``interrupt`` /
``RunConfig`` 共 **7 个**符号（导出面清单的**手写**权威是
``specs/b2f2-public-api-facade/contracts/facade-api.md`` §0）。

**零实现体**（FR-006 · 门禁 G14）：本模块内**没有任何** ``class`` /
``def`` / ``async def`` 语句——只做**导出**与**常量**。
实现体住在门面包内的私有模块（``_stategraph`` / ``_primitives``）、
**L2 执行内核层**（``freegraph.runtime._interrupt``）与契约层
（``freegraph.contracts``）⇒ 门面是 ARCH-4「公开 API 面只经由 L1
导出」的执行手段，也是未来接线时**唯一需要改 import 行**的地方。

.. note::
   **MUST NOT** 使用 ``from __future__ import annotations``——该 future import
   会留下名为 ``annotations`` 的**公开绑定**，直接破坏「公开名恰 7 个」的
   判据（``data-model.md`` R-3 · research D-02）。

**层归属**：门面是**跨层单元**（层 =「—」）——它的导出面按定义横跨 L1–L3，
故它是 ARCH-1 的**唯一例外**（可 import L1–L3，仍**不得** import L4 持久化 /
L5 可观测 · 门禁 G17 / G18）。

**当前行为**：``StateGraph`` 的四个方法仍抛内置 ``NotImplementedError``
（消息点名归属 feature——行为归 B6F1 / B7F2）；``interrupt`` **已接线**
（**B10F1**）⇒ 其实现体在 **L2** 的 ``freegraph.runtime._interrupt`` ⇒ ⇒
门面**模块级** ``from .runtime._interrupt import interrupt``
（**ARCH-1 的唯一例外** ``facade-L1-L3`` ⇒ 门面 → L2 **合法** · 门禁
G17 / G18 恒绿）。

⚠️ **``src/freegraph/_primitives.py``（L2 单文件条目）MUST NOT import
``runtime/``**（**L2 目录条目**）⇒ 二者互相 import = **跨注册表条目的
同层 import** ⇒ **门禁 G25 判红**（实测两个方向都 FAIL）⇒ ⇒ 该文件
**只留 ``Send``**（**B11F1** 接线）。
"""

from ._primitives import Send
from ._stategraph import StateGraph
from .contracts import Command, RunConfig
from .runtime._interrupt import interrupt

START = "__start__"
END = "__end__"

__all__ = [
    "StateGraph",
    "START",
    "END",
    "Send",
    "interrupt",
    "Command",
    "RunConfig",
]
