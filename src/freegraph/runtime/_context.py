# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **运行期上下文（C21）** —— 属 **B8F3**（内部模块）。

本模块是 ``RunConfig.context`` 在运行期的**唯一载体**：

* :data:`_CONTEXT` —— ``contextvars.ContextVar``（缺省 ``None``）；
* :func:`bind_context` —— 单次运行入口绑定 / ``finally`` 复原（token reset）；
* :func:`get_context` —— L2 私有读取入口；
* :class:`_ContextState` —— ``context is not None`` 时的节点入参视图
  （``dict`` 子类 + **只读** ``.context``；映射内容仍是稀疏状态）；
* :func:`with_context` / :func:`with_context_arg` —— 标准节点入参 / ``Send.arg``
  的按需包装（``context is None`` 时返回**原对象**）。

**契约权威**：``specs/b8f3-node-alias-context/contracts/context-channel-contract.md``
（``<!-- authority: yes -->``）⇒ 本模块 MUST NOT 另立第二套载体。

**关键边界**：

* ``context`` **不是**状态 key ⇒ 不入 channels / 归约 / ``invoke`` 终态 /
  ``values`` 载荷 / checkpoint；
* ``context is None`` ⇒ 节点入参保持**精确** ``dict``（C4 / I-1 逐字不变）；
* ``.context`` 只读；未知属性按普通对象规则抛 ``AttributeError``；
* 本模块私有 ⇒ ``__all__`` 恒空 ⇒ 不进 ``freegraph.runtime.__all__``。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

__all__: list[str] = []

#: 当前运行的 context（缺省 ``None`` ⇒ 未提供）。
_CONTEXT: ContextVar[Any] = ContextVar("freegraph_run_context", default=None)


@contextmanager
def bind_context(context: Any) -> Iterator[None]:
    """把 ``context`` 绑定到当前运行；退出时用 token **复原**（含异常路径）。"""
    token = _CONTEXT.set(context)
    try:
        yield
    finally:
        _CONTEXT.reset(token)


def get_context() -> Any:
    """返回当前运行的 context（未绑定 / 未提供 ⇒ ``None``）。"""
    return _CONTEXT.get()


class _ContextState(dict):
    """带只读 ``.context`` 的节点入参视图（映射内容 == 稀疏状态）。"""

    def __init__(self, mapping: dict[str, Any], context: Any) -> None:
        super().__init__(mapping)
        self._fg_context = context

    @property
    def context(self) -> Any:
        """本次运行的 context（同一对象）；**只读**。"""
        return self._fg_context


def with_context(view: dict[str, Any]) -> dict[str, Any]:
    """按需把标准节点入参包装为 ``_ContextState``。

    ``context is None`` ⇒ 返回**精确的输入 dict**（``type(...) is dict``）；
    否则返回 ``_ContextState``（映射内容 / 顺序 / 值与输入逐字一致）。
    """
    context = get_context()
    if context is None:
        return view
    if isinstance(view, _ContextState):
        return view
    return _ContextState(view, context)


def with_context_arg(arg: Any) -> Any:
    """按需包装 ``Send.arg``：只有 ``dict`` 且 context 非 ``None`` 时包装。

    非 ``dict``（含任意用户对象）⇒ **原样返回**，不改变类型 / 身份（v1 边界）。
    """
    context = get_context()
    if context is None:
        return arg
    if not isinstance(arg, dict):
        return arg
    if isinstance(arg, _ContextState):
        return arg
    return _ContextState(arg, context)
