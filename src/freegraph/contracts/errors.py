# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 内核异常族 —— 本文件是该异常族的**唯一定义处**。

设计要点：

* 上层只捕获基类 :class:`FreegraphError` 即可兜住**全部**内核错误，
  无需逐个枚举子类（后续版本新增子类时，上层代码不必修改）。
* 基类名一旦冻结即**不得更改**；后续可**新增**子类，但基类名不变。
* 各子类暴露**结构化属性**（而非只给一段消息文本），
  上层取细节时**无须解析错误消息**。

本文件是内核异常族的唯一定义处；上层只捕获基类即可兜住全部内核错误；
后续可新增子类但基类名不得改。
"""

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - 仅注解期 ⇒ 运行期零内部 import
    from freegraph.contracts.types import Interrupt


class FreegraphError(Exception):
    """freegraph 内核异常的**统一基类**。

    上层只需 ``except FreegraphError`` 即可兜住**全部**内核错误，
    无须逐个枚举子类——后续版本新增子类时，上层代码不必修改。

    刻意**不自定义** ``__init__``：它只做「类型锚点 + 统一捕获点」两件事，
    消息原样交给内置异常基类处理。

    基类名 ``FreegraphError`` 即**冻结面**，不得再改；
    后续可**新增**子类，但基类名不变。
    """


class InvalidUpdateError(FreegraphError):
    """节点返回了状态 schema 中**不存在**的 key。

    结构化属性：

    * ``invalid_keys`` —— 不认识的 key 列表（``tuple[str, ...]``，顺序保持）。

    错误消息**只是给人看的摘要**——上层取细节时 MUST NOT 需要解析消息，
    直接读 ``invalid_keys`` 即可。

    缺省摘要为**英文**（面向下游消费者与上游报错的逐条对照），
    且 MUST **点名**那些未知 key。
    """

    def __init__(
        self,
        invalid_keys: Iterable[str],
        *,
        message: str | None = None,
    ) -> None:
        self.invalid_keys: tuple[str, ...] = tuple(invalid_keys)
        super().__init__(
            message
            if message is not None
            else (
                "Invalid state update: unknown key(s) "
                f"{', '.join(repr(key) for key in self.invalid_keys)}"
            )
        )


class GraphRecursionError(FreegraphError):
    """图的**递归超限**。

    结构化属性：

    * ``recursion_limit`` —— 递归上限；
    * ``current_step`` —— 已达步数。

    错误消息**只是给人看的摘要**——上层取细节时 MUST NOT 需要解析消息。

    缺省摘要为**英文**，且 MUST 点名递归上限与已达步数。
    """

    def __init__(
        self,
        recursion_limit: int,
        current_step: int,
        *,
        message: str | None = None,
    ) -> None:
        self.recursion_limit = recursion_limit
        self.current_step = current_step
        super().__init__(
            message
            if message is not None
            else (
                "Graph recursion limit exceeded: "
                f"recursion_limit={self.recursion_limit}, "
                f"current_step={self.current_step}"
            )
        )


class GraphInterrupt(FreegraphError):
    """节点**主动中断**（**上游同款** · 2026-11-12 上游对齐 P3）。

    结构化属性：

    * ``payload`` —— 中断**序列**（``tuple[Interrupt, ...]``）· 一次异常可携带
      **多个**中断（上游同款 · 上游 ``langgraph/errors.py:102-107``
      的 ``GraphInterrupt(interrupts: Sequence[Interrupt] = ())``）
      ⇒ **C17** 的「元素须带 ``.value`` 与 ``.id``」由 ``Interrupt`` 承载
      （L1 的 ``Interrupt`` · 上游 ``langgraph/types.py:575-620`` 同款）。

    ⚠️ **异常实参**（``args[0]``）= 同一个中断序列（上游同款 · 上游把序列放进
    ``args[0]``）⇒ 两侧的取法都work。
    """

    def __init__(
        self,
        interrupts: "Sequence[Interrupt]" = (),
        *,
        message: str | None = None,
    ) -> None:
        self.payload: "tuple[Interrupt, ...]" = tuple(interrupts)
        # ⚠️ **上游同款**（上游 ``langgraph/errors.py:102-107``）：异常的**实参** = 中断序列
        # ⇒ ``exc.args[0]`` 就是**序列**（上游的取法）⇒ 附带 message 时作为**第二个**实参。
        if message is None:
            super().__init__(self.payload)
        else:
            super().__init__(self.payload, message)
