# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 · **补充 trace 记录** —— 属 **B19F1**（内部模块）。

本模块只提供与 ``Span`` **分离**的每节点任务记录 :class:`TraceRecord`，以及
JSON 安全降级纯函数 :func:`json_safe`。记录**不是** ``Span`` 的字段，不写进
``Span.attributes`` / ``Span.context``，也不属于 ``TraceSink`` 三方法协议。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["TraceRecord", "json_safe"]

TriggerId = tuple[Any, ...]


def _type_name(value: Any) -> str:
    """返回稳定的类型名占位符（不内省对象内容）。"""
    kind = type(value)
    return f"<{kind.__module__}.{kind.__qualname__}>"


def _json_key(key: Any) -> str:
    """把 dict key 确定性转换为字符串。"""
    if isinstance(key, str):
        return key
    if key is None or isinstance(key, (bool, int, float)):
        return str(key)
    return _type_name(key)


def json_safe(value: Any, _seen: set[int] | None = None) -> Any:
    """把任意值转换为可直接 ``json.dumps`` 的确定性表示。

    * 标量原样；``dict`` / ``list`` / ``tuple`` 递归（tuple → list）；
    * ``set`` / ``frozenset`` → 排序后的 list；
    * 循环引用 → ``"<cycle>"``；其它对象 / bytes / 异常 → 类型名占位符；
    * **不内省**对象属性 / ``repr`` / ``__dict__``；**不抛异常**。
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    seen = _seen if _seen is not None else set()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return _type_name(value)
    if isinstance(value, dict):
        marker = id(value)
        if marker in seen:
            return "<cycle>"
        seen.add(marker)
        try:
            return {_json_key(key): json_safe(item, seen) for key, item in value.items()}
        finally:
            seen.discard(marker)
    if isinstance(value, (list, tuple)):
        marker = id(value)
        if marker in seen:
            return "<cycle>"
        seen.add(marker)
        try:
            return [json_safe(item, seen) for item in value]
        finally:
            seen.discard(marker)
    if isinstance(value, (set, frozenset)):
        marker = id(value)
        if marker in seen:
            return "<cycle>"
        seen.add(marker)
        try:
            items = [json_safe(item, seen) for item in value]
        finally:
            seen.discard(marker)
        return sorted(items, key=lambda item: (type(item).__name__, repr(item)))
    return _type_name(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class TraceRecord:
    """每节点任务一条补充 trace 记录（与 ``Span`` 分离）。"""

    span_id: str
    task_id: str
    run_id: str
    thread_id: str | None
    checkpoint_id: str | None
    node: str
    superstep: int
    triggers: tuple[TriggerId, ...]
    concurrency_group: tuple[str, ...]
    barrier_groups: tuple[tuple[str, ...], ...]
    input_state: Any
    output_state: Any
    error: BaseException | None

    def to_jsonable(self) -> dict[str, Any]:
        """返回 B20 落盘用的 JSON 安全视图（``error`` → 类型名 + 消息）。"""
        return {
            "span_id": self.span_id,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "checkpoint_id": self.checkpoint_id,
            "node": self.node,
            "superstep": self.superstep,
            "triggers": [list(trigger) for trigger in self.triggers],
            "concurrency_group": list(self.concurrency_group),
            "barrier_groups": [list(group) for group in self.barrier_groups],
            "input_state": self.input_state,
            "output_state": self.output_state,
            "error": (
                None
                if self.error is None
                else {
                    "type": type(self.error).__name__,
                    "message": str(self.error),
                }
            ),
        }
