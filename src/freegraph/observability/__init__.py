# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 —— span 生产 + **TraceSink 接入** + **本地 trace 查询**。

本模块提供：

* :class:`SpanProducer` —— run-scoped 当前 span 栈 / 父子关系 / 接收端转发；
* :func:`invoke_model` / :func:`invoke_tool` —— 模型 / 工具显式调用辅助；
* :func:`current_span` —— 当前上下文中**最内层**的活动 span（B19F1 · C24）；
* :class:`TraceRecord` —— 每节点任务一条补充 trace 记录（B19F1）；
* :class:`FileTraceStore` —— 本地 JSONL 写入 + 查询后端（B20F1 / B20F2）；
* :class:`SqliteTraceStore` —— 本地 SQLite 写入 + 查询后端（B20F2）。

**不是公开门面**（``freegraph.graph``）的组成部分；``import freegraph``
不会加载本模块（ARCH-2）。本模块零 L2 import、零第三方依赖、零环境变量。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from freegraph.contracts.trace import Span

from ._file_store import FileTraceStore
from ._invoke import invoke_model, invoke_tool
from ._producer import SpanProducer, current_tracer
from ._record import TraceRecord
from ._sqlite_store import SqliteTraceStore

__all__ = [
    "FileTraceStore",
    "SpanProducer",
    "SqliteTraceStore",
    "TraceRecord",
    "current_span",
    "invoke_model",
    "invoke_tool",
]


def current_span() -> Span | None:
    """返回当前上下文中**最内层**的活动 span；无 ⇒ ``None``。"""
    producer = current_tracer()
    if producer is None:
        return None
    return producer.current_span()
