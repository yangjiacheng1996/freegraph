# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""``Send`` / ``interrupt`` 的**外壳**——门面的实现体在此（门面本身零实现体）。

本模块承载两个**原语**的外壳，**未来由 B11F1**（``Send`` 的动态 fan-out）与
**B10F1**（``interrupt`` 的中断 / 恢复闭环）在**同一个门面导出名**下接线；
**门面导出面 MUST NOT 因接线而改变**（门禁 G15 / G16 会同时报出）。

**签名冻结**（``data-model.md`` §2.5 / §2.6）：

* ``Send`` = ``@dataclass(frozen=True, slots=True)``，字段 ``node: str`` /
  ``arg: Any``——**刻意不用** ``kw_only=True``（``harness/demo/graph_core.py``
  与上游都用**位置参数** ``Send("worker", {"n": 1})`` ⇒ ``kw_only=True`` 会
  直接 ``TypeError`` · research D-13）；**不可变记录**（改属性抛
  ``FrozenInstanceError`` · Q7）；**不可哈希**（显式 ``__hash__ = None`` ·
  FR-005 ① · 裁定 11——frozen dataclass 默认**仍会**生成 ``__hash__``，
  故 MUST 显式关掉）；
* ``interrupt(value: Any) -> Any`` —— **位置或关键字皆可**（上游
  ``langgraph/types.py:851`` 同形）；当前**无条件抛**
  ``NotImplementedError``（消息点名 B10F1）⇒ 零副作用。
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


def interrupt(value: Any) -> Any:
    """在节点内**中断**并等待恢复——**未接线**（由 **B10F1** 交付）。

    运行期语义：返回**恢复值**（``Any``）。当前实现**无条件**抛
    ``NotImplementedError``⇒ 零副作用。

    :param value: 中断时携带的载荷（用户自定义）。
    :returns: 运行期返回恢复值；本 feature **不可达**。
    :raises NotImplementedError: 恒抛——行为归 **B10F1**。
    """
    raise NotImplementedError("interrupt 尚未接线（由 B10F1 交付）")
