# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 · **tracer 运行作用域** —— 属 **B19F1**（内部模块）。

本模块是公开注入形态 ``compile(*, tracer=...)`` 的运行期接线入口：

* ``tracer is not None`` ⇒ 构造**一个** :class:`SpanProducer`，同一实例同时绑定
  L2 ``_span_hook.bind_span_tracer`` 与 L5 ``_producer.bind_tracer``；
* ``tracer is None`` ⇒ 把两层 hook 都置 ``None``（**仅用于 B19F1 作用域内的嵌套屏蔽**）；
* 作用域结束即解绑；``_B19F1_SCOPE_ACTIVE`` 用 token 恢复。

**ARCH-3 例外 R-2**：本模块**仅**绑定 ``runtime._span_hook.bind_span_tracer``；
**不读** ``runtime._stream_context``（``run_id`` / ``thread_id`` 由 L2 节点 start
``Span`` 继承）。MUST NOT 扩展为任意 L5 → L2 私有依赖。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from ..runtime._span_hook import bind_span_tracer
from ._producer import SpanProducer, bind_tracer

__all__: list[str] = []

_B19F1_SCOPE_ACTIVE: ContextVar[bool] = ContextVar(
    "freegraph_b19f1_scope_active", default=False
)


def b19f1_scope_active() -> bool:
    """当前是否处于 B19F1 注入作用域（内部判定）。"""
    return _B19F1_SCOPE_ACTIVE.get()


@contextmanager
def trace_run_scope(tracer: Any | None) -> Iterator[SpanProducer | None]:
    """run-scoped 双绑定；``tracer is None`` 时屏蔽两层 hook。"""
    producer = SpanProducer(receiver=tracer) if tracer is not None else None
    token = _B19F1_SCOPE_ACTIVE.set(True)
    try:
        with bind_tracer(producer), bind_span_tracer(producer):
            yield producer
    finally:
        _B19F1_SCOPE_ACTIVE.reset(token)
