# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""``StateGraph`` 的**外壳**——门面的实现体在此（门面本身零实现体）。

本模块承载 ``StateGraph`` 外壳，**未来由 B6F1**（构建）在**同一个门面导出名**
下接线；**门面导出面 MUST NOT 因接线而改变**（门禁 G15 / G16 会同时报出）。

**当前状态（M0 · B2F2）**：构造**可成功**（零校验、零副作用），四个方法
（``add_node`` / ``add_edge`` / ``add_conditional_edges`` / ``compile``）
一律抛内置 ``NotImplementedError`` 并点名归属 feature——**静默成功**会让
用户的图「看起来建好了」却永不执行，比报错更坏（``data-model.md`` §4）。

**签名冻结**（``data-model.md`` §2.1 · **上游同款** · 2026-11-12 上游对齐 P3 改写）：

* ``__init__(self, state_schema: Any, context_schema: Any = None, *, input_schema: Any = None, output_schema: Any = None) -> None``
  —— **恰一个**必填位置参数（宪法原则 III 第 2 项）· 参数名**逐字对齐上游**
  （上游 ``langgraph/graph/state.py:216-224``）· 其余**可选** ⇒ 「只传 schema 一个位置参数」
  的调用形态**不受影响**（**放宽**）；
* ``add_node(self, node: str | Callable, action: Callable | None = None, *, alias: str | None = None, defer: bool = False, metadata: Mapping[str, Any] | None = None) -> Self``
  —— 位置参数 ``(node, action)``（**上游同款** · 上游 ``:667-682`` · 《立项书》§4.3 第 3 项
  **逐字**写的就是 ``(node: str, action: Callable)``）· 支持**单 callable 形态**
  （``add_node(fn)`` ⇒ 节点名取 ``fn.__name__`` · 上游 ``:778-787``）· 关键字 ``alias``
  （宪法 III 第 3 项 · C25 · freegraph **自有**增量）；
* ``add_edge(self, start_key: str | list[str], end_key: str) -> Self``
  —— 参数名**逐字对齐上游**（上游 ``:928`` · 《立项书》§4.3 第 4 项同款）· 返回注解 ``Self``
  （链式语义 · 宪法 III 第 4 项）；
* ``add_conditional_edges(self, source: str, path: Callable, path_map: list[str] | dict[str, str] | None = None) -> Self``
  —— ``path_map`` **同时支持 list 与 dict**（宪法 III 第 5 项 · C7）· **可省略**（**上游同款** ·
  上游 ``:982-989``）· 参数名**逐字对齐上游**；
* ``compile(self, checkpointer: Checkpointer | None = None, *, cache: Any = None, store: Store | None = None, interrupt_before: Any = None, interrupt_after: Any = None, debug: bool = False, name: str | None = None, transformers: Any = None) -> CompiledGraph``
  —— **无参可调用**（裁定 6 · C10 / C19 / C20）· ``checkpointer`` **位置或关键字**（**上游同款** ·
  上游 ``:1177-1188``）· 其余关键字**逐字对齐上游**（依赖上游专属类型者以 ``Any`` 占位）；
* **上游同款的六个方法**（**全部为桩** · 归 B6F1 / B7F2 接线）：
  ``add_sequence``（上游 ``:1032-1077``）· ``set_entry_point``（``:1079``）·
  ``set_conditional_entry_point``（``:1092``）· ``set_finish_point``（``:1116``）·
  ``validate``（``:1129-1175``）· ``set_node_defaults``（``:272-335``）。

**公开属性：无** —— ``schema`` **私有**存放（``self._schema`` · research D-11）
⇒ 快照里**无** ``[attribute]`` 条目。
"""

from collections.abc import Callable, Mapping, Sequence
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

    def __init__(
        self,
        state_schema: Any,
        context_schema: Any = None,
        *,
        input_schema: Any = None,
        output_schema: Any = None,
    ) -> None:
        """构造：只存下 ``state_schema``（私有），**不校验、不产生副作用**。

        ⚠️ **上游同款**（2026-11-12 上游对齐 P3 · 上游 ``langgraph/graph/state.py:216-224``）：
        参数名**逐字对齐上游**（``state_schema`` / ``context_schema`` / ``input_schema`` /
        ``output_schema``）⇒ **必填**位置参数**仍恰一个** ⇒ 「只传 schema 一个位置参数」的
        调用形态**不受影响**；其余三个**可选**且**关键字专用**（**放宽**）。
        """
        self._schema = state_schema

    def add_node(
        self,
        node: str | Callable[..., Any],
        action: Callable[..., Any] | None = None,
        *,
        alias: str | None = None,
        defer: bool = False,
        metadata: Mapping[str, Any] | None = None,
    ) -> Self:
        """登记一个节点——**未接线**（由 **B6F1** 交付）。

        ⚠️ **上游同款**（2026-11-12 上游对齐 P3 · 上游 ``:667-682``）：
        * 位置参数**逐字对齐上游** ``(node, action)``（《立项书》§4.3 第 3 项**逐字**同款）
          ⇒ **节点名**是第一个位置参数、**节点动作**是第二个；
        * 支持**单 callable 形态**：``add_node(fn)`` ⇒ 节点名取 ``fn.__name__``（上游 ``:778-787``）；
        * ``alias`` 是 freegraph **自有**增量（节点别名 · C25 · B8F3）；
        * ``defer`` / ``metadata`` 是**上游同款**的纯数据关键字。
        """
        raise NotImplementedError("add_node 尚未接线（由 B6F1 交付）")

    def add_edge(self, start_key: str | list[str], end_key: str) -> Self:
        """登记一条边——**未接线**（由 **B6F1** 交付）。

        ⚠️ **上游同款**（上游 ``langgraph/graph/state.py:928``）：参数名**逐字对齐上游**
        ``(start_key, end_key)``（《立项书》§4.3 第 4 项同款）。
        """
        raise NotImplementedError("add_edge 尚未接线（由 B6F1 交付）")

    def add_conditional_edges(
        self,
        source: str,
        path: Callable[..., str | list[str]],
        path_map: list[str] | dict[str, str] | None = None,
    ) -> Self:
        """登记条件边——**未接线**（由 **B6F1** 交付）。

        ``path_map`` **同时支持 list 与 dict** 两种形态（宪法 III 第 5 项 · C7）·
        ⚠️ **上游同款**（上游 ``:982-989``）：参数名**逐字对齐上游** ``(source, path)``，
        且 ``path_map`` **可省略**（**放宽**）。
        """
        raise NotImplementedError("add_conditional_edges 尚未接线（由 B6F1 交付）")

    def add_sequence(self, nodes: Sequence[Any]) -> Self:
        """登记一条**节点序列**——**未接线**（**上游同款** · 上游 ``:1032-1077``）。"""
        raise NotImplementedError("add_sequence 尚未接线（由 B6F1 交付）")

    def set_entry_point(self, key: str) -> Self:
        """设定**入口节点**——**未接线**（**上游同款** · 上游 ``:1079``）。"""
        raise NotImplementedError("set_entry_point 尚未接线（由 B6F1 交付）")

    def set_conditional_entry_point(
        self,
        path: Callable[..., str | list[str]],
        path_map: list[str] | dict[str, str] | None = None,
    ) -> Self:
        """设定**条件入口**——**未接线**（**上游同款** · 上游 ``:1092``）。"""
        raise NotImplementedError("set_conditional_entry_point 尚未接线（由 B6F1 交付）")

    def set_finish_point(self, key: str) -> Self:
        """设定**终点节点**——**未接线**（**上游同款** · 上游 ``:1116``）。"""
        raise NotImplementedError("set_finish_point 尚未接线（由 B6F1 交付）")

    def validate(self, interrupt: Sequence[str] | None = None) -> Self:
        """校验图结构——**未接线**（**上游同款** · 上游 ``:1129-1175``）。"""
        raise NotImplementedError("validate 尚未接线（由 B6F1 交付）")

    def set_node_defaults(self, **kwargs: Any) -> Self:
        """设定节点的**默认策略**——**未接线**（**上游同款** · 上游 ``:272-335``）。

        ⚠️ 上游的四个关键字（``retry_policy`` / ``cache_policy`` / ``error_handler`` / ``timeout``）
        都绑上游专属类型 ⇒ freegraph 以 ``**kwargs`` **原样透传**（形状**放宽**）⇒ 接线归 **B6F1**。
        """
        raise NotImplementedError("set_node_defaults 尚未接线（由 B6F1 交付）")

    def compile(
        self,
        checkpointer: Checkpointer | None = None,
        *,
        cache: Any = None,
        store: Store | None = None,
        interrupt_before: Any = None,
        interrupt_after: Any = None,
        debug: bool = False,
        name: str | None = None,
        transformers: Any = None,
    ) -> CompiledGraph:
        """编译成可执行产物——**未接线**（由 **B7F2** 交付）。

        ⚠️ **上游同款**（2026-11-12 上游对齐 P3 · 上游 ``langgraph/graph/state.py:1177-1188``）：
        * ``checkpointer`` 由 **keyword-only** 改为**位置或关键字**（**放宽**）；
        * 新增 ``cache`` / ``interrupt_before`` / ``interrupt_after`` / ``debug`` / ``name`` /
          ``transformers`` 六个关键字（依赖上游专属类型者以 ``Any`` 占位）；
        * ``compile()`` 仍**无参可调用**（裁定 6 · C10 / C19 / C20）。
        """
        raise NotImplementedError("compile 尚未接线（由 B7F2 交付）")
