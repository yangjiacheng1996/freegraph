# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""``Send`` 的**外壳** —— 门面的实现体在此（门面本身零实现体）。

本模块承载 ``Send`` **原语**的外壳，**由 B11F1**（``Send`` 的动态 fan-out）
在**同一个门面导出名**下接线；**门面导出面 MUST NOT 因接线而改变**
（门禁 G15 / G16 会同时报出）。

⚠️ **``interrupt`` 已于 B10F1 迁出**（**PR-4**）⇒ ⇒ 本模块**只留
``Send``** ⇒ ⇒ **MUST NOT** import ``freegraph.runtime``（**L2 目录条目**）
⇒ ⇒ 层注册表把本文件登记为 **L2 单文件条目**、把 ``runtime/`` 登记为
**另一个 L2 目录条目** ⇒ 二者互相 import = **跨注册表条目的同层
import** ⇒ **门禁 G25 判红**（实测两个方向都 FAIL · 惰性 import 同样
判红 —— 门禁扫 AST）⇒ ⇒ ``interrupt`` 的**运行期机制**住在
``src/freegraph/runtime/_interrupt.py``（**L2 目录条目内**），门面
``src/freegraph/graph.py`` 用**模块级** ``ImportFrom`` **直接转出**
（**ARCH-1 的唯一例外** ``facade-L1-L3``）。

**签名冻结**（``data-model.md`` §2.5 / §2.6）：

* ``Send`` = ``@dataclass(frozen=True, slots=True)``，字段 ``node: str`` /
  ``arg: Any``——**刻意不用** ``kw_only=True``（``harness/demo/graph_core.py``
  与上游都用**位置参数** ``Send("worker", {"n": 1})`` ⇒ ``kw_only=True`` 会
  直接 ``TypeError`` · research D-13）；**不可变记录**（改属性抛
  ``FrozenInstanceError`` · Q7）；**不可哈希**（显式 ``__hash__ = None`` ·
  FR-005 ① · 裁定 11——frozen dataclass 默认**仍会**生成 ``__hash__``，
  故 MUST 显式关掉）。
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Send:
    """**动态 fan-out 的载荷**——把某个 ``arg`` 投递给目标节点 ``node``。

    **不可变记录**：创建后**无任何**状态变化（改属性抛
    ``FrozenInstanceError``）——避免调度器读到旧值的时序坑。

    **不可哈希**：``__hash__`` **显式**置 ``None``。frozen dataclass 默认
    **仍会**生成 ``__hash__``，故 MUST 显式关掉（FR-005 ① · 裁定 11）——
    与 ``Node`` / ``Edge`` / ``Graph`` / ``Span`` 同构。

    .. note::
       **与上游的差异**：上游 LangGraph 的 ``Send`` **可变** ⇒ 该差异已登记
       在 ``README.md`` 的兼容矩阵（research D-17）。
    """

    node: str
    arg: Any

    __hash__ = None
