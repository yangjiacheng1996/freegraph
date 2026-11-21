# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 · **共享行构造** —— 属 **B20F2**（内部模块）。

把 ``Span`` / ``TraceRecord`` 转换为 B20F1 已锁定的 JSONL 行视图：

* :func:`span_to_dict` —— ``kind="span"`` + ``Span`` 11 字段；
* :func:`record_to_dict` —— ``kind="trace_record"`` + ``TraceRecord.to_jsonable()`` 13 字段。

本模块只做纯函数映射，不读文件 / 不联网 / 不读环境变量；JSONL 与 SQLite
两个后端共用同一行视图，保证查询结果逐条等价。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from typing import Any

from freegraph.contracts.trace import Span

from ._record import TraceRecord

__all__: list[str] = ["record_to_dict", "span_to_dict"]


def span_to_dict(span: Span) -> dict[str, Any]:
    """把结束快照映射为 ``kind="span"`` + 11 字段的 dict（``kind`` 第一）。"""
    return {
        "kind": "span",
        "id": span.id,
        "name": span.name,
        "attributes": dict(span.attributes),
        "parent": span.parent,
        "start_time": span.start_time,
        "end_time": span.end_time,
        "context": dict(span.context),
        "thread_id": span.thread_id,
        "run_id": span.run_id,
        "node": span.node,
        "checkpoint_id": span.checkpoint_id,
    }


def record_to_dict(record: TraceRecord) -> dict[str, Any]:
    """把 ``TraceRecord.to_jsonable()`` 原样包装为带 ``kind`` 的 dict。"""
    return {"kind": "trace_record", **record.to_jsonable()}
