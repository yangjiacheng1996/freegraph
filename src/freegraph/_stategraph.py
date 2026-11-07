# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""``StateGraph`` 的**外壳**——门面的实现体在此（门面本身零实现体）。

本模块承载 ``StateGraph`` 外壳，**未来由 B6F1**（构建）在**同一个门面导出名**
下接线；**门面导出面 MUST NOT 因接线而改变**（门禁 G15 / G16 会同时报出）。

**当前状态（M0 · B2F2）**：构造**可成功**（零校验、零副作用），四个方法
（``add_node`` / ``add_edge`` / ``add_conditional_edges`` / ``compile``）
一律抛内置 ``NotImplementedError`` 并点名归属 feature——**静默成功**会让
用户的图「看起来建好了」却永不执行，比报错更坏（``data-model.md`` §4）。

**签名冻结**（``data-model.md`` §2.1）：

* ``__init__(self, schema: Any) -> None`` —— **恰一个**必填位置参数，
  参数名 ``schema``（宪法原则 III 第 2 项 · 裁定 4）；
* ``add_node(self, name: str, fn: NodeFunc, *, alias: str | None = None) -> Self``
  —— 位置参数 ``(str, Callable)`` + 关键字 ``alias``（宪法 III 第 3 项 · C25）；
* ``add_edge(self, src: str | list[str], dst: str) -> Self``
  —— 返回注解 ``Self``（链式语义 · 宪法 III 第 4 项 · 裁定 5）；
* ``add_conditional_edges(self, src: str, path_fn: ..., path_map: ...) -> Self``
  —— ``path_map`` **同时支持 list 与 dict**、**无缺省值**（宪法 III 第 5 项 · C7）；
* ``compile(self, *, checkpointer: Checkpointer | None = None, store: Store | None = None) -> CompiledGraph``
  —— **无参可调用** + 两个 **keyword-only** 可选关键字（裁定 6 · C10 / C19 / C20）。

**公开属性：无** —— ``schema`` **私有**存放（``self._schema`` · research D-11）
⇒ 快照里**无** ``[attribute]`` 条目。
"""

from collections.abc import Callable
from typing import Any, Self

from .contracts import Checkpointer, CompiledGraph, NodeFunc, Store


class StateGraph:
    """**图构建器**——用户从门面取到的建图入口（M0 阶段**未接线**）。

    构造**只接受一个**位置参数 ``schema``（状态 schema），**零值校验**、
    **零副作用**（不读环境变量、不做 I/O、不起线程）——契约层的数据类
    一律「零值校验」（生产者负责）。

    .. note::
       **当前四个方法一律抛** ``NotImplementedError``——构建行为归 **B6F1**、
       编译行为归 **B7F2**。**无「部分接线」状态**：允许「``add_node`` 能用、
       ``compile`` 不能用」的半接线会产生难以诊断的行为 ⇒ 明确禁止。
    """

    def __init__(self, schema: Any) -> None:
        """构造：只存下 ``schema``（私有），**不校验、不产生副作用**。"""
        self._schema = schema

    def add_node(
        self, name: str, fn: NodeFunc, *, alias: str | None = None
    ) -> Self:
        """登记一个节点——**未接线**（由 **B6F1** 交付）。

        ``alias`` 是**关键字专用**参数（节点别名 · C25 · B8F3）。
        """
        raise NotImplementedError("add_node 尚未接线（由 B6F1 交付）")

    def add_edge(self, src: str | list[str], dst: str) -> Self:
        """登记一条边——**未接线**（由 **B6F1** 交付）。"""
        raise NotImplementedError("add_edge 尚未接线（由 B6F1 交付）")

    def add_conditional_edges(
        self,
        src: str,
        path_fn: Callable[..., str | list[str]],
        path_map: list[str] | dict[str, str],
    ) -> Self:
        """登记条件边——**未接线**（由 **B6F1** 交付）。

        ``path_map`` **同时支持 list 与 dict** 两种形态（宪法 III 第 5 项 · C7）。
        """
        raise NotImplementedError("add_conditional_edges 尚未接线（由 B6F1 交付）")

    def compile(
        self,
        *,
        checkpointer: Checkpointer | None = None,
        store: Store | None = None,
    ) -> CompiledGraph:
        """编译成可执行产物——**未接线**（由 **B7F2** 交付）。

        两个关键字**均为 keyword-only**（裁定 6），且**都可省略**
        ⇒ ``compile()`` **无参可调用**。
        """
        raise NotImplementedError("compile 尚未接线（由 B7F2 交付）")
