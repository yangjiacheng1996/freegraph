# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 · **span 生产者** —— 属 **B18F1**（内部模块）。

``SpanProducer`` 持有 run-scoped 当前 span 栈，负责：

* 节点 / 模型 / 工具三级 span 的入栈 / 出栈；
* 父链（``parent`` = 入栈前的栈顶 id）；
* 接收端（``on_span_start`` / ``on_span_end``）转发与异常隔离；
* 模型 / 工具 span 的 v1 极简属性（Q9）与从节点 span 继承关联键。

本模块 **零 L2 import**：``run_id`` / ``thread_id`` / ``node`` /
``checkpoint_id`` 全部从当前节点 span 继承。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Literal

from freegraph.contracts.trace import Span

from ._time import end_iso_after, utc_now_iso_ns

__all__ = ["SpanProducer", "bind_tracer", "current_tracer"]

logger = logging.getLogger(__name__)

_SpanKind = Literal["node", "model", "tool"]

_TRACER: ContextVar[SpanProducer | None] = ContextVar(
    "freegraph_observability_tracer", default=None
)


@dataclass(frozen=True, slots=True)
class _SpanFrame:
    """当前 span 栈的一帧（``span`` + 生产侧 ``kind``）。"""

    span: Span
    kind: _SpanKind


@contextmanager
def bind_tracer(tracer: SpanProducer | None) -> Iterator[None]:
    """在当前上下文中绑定 / 解绑 L5 生产者。"""
    token = _TRACER.set(tracer)
    try:
        yield
    finally:
        _TRACER.reset(token)


def current_tracer() -> SpanProducer | None:
    """返回当前绑定的 L5 生产者（未绑定 ⇒ ``None``）。"""
    return _TRACER.get()


def _infer_kind(span: Span) -> _SpanKind:
    """按 ``attributes`` 推断 span 层级（生产侧封闭约定）。"""
    if not span.attributes:
        return "node"
    operation = span.attributes.get("gen_ai.operation.name")
    if operation == "execute_tool":
        return "tool"
    if operation is not None:
        return "model"
    return "node"


def _model_name(obj: Any) -> str | None:
    """按 ``model_name`` → ``model`` 读取非空字符串模型名；否则省略。"""
    for attribute in ("model_name", "model"):
        value = getattr(obj, attribute, None)
        if isinstance(value, str) and value:
            return value
    return None


class SpanProducer:
    """run-scoped span 生产者（L5）。"""

    def __init__(self, receiver: Any | None = None) -> None:
        self._receiver = receiver
        self._stack: ContextVar[tuple[_SpanFrame, ...]] = ContextVar(
            f"freegraph_span_stack_{id(self)}", default=()
        )

    def on_span_start(self, span: Span) -> None:
        """入栈并转发开始快照；接收端异常被隔离。"""
        frame = _SpanFrame(span=span, kind=_infer_kind(span))
        self._stack.set(self._stack.get() + (frame,))
        self._forward("on_span_start", span)

    def on_span_end(self, span: Span) -> None:
        """按 ``id`` 出栈并转发结束快照；接收端异常被隔离。"""
        stack = self._stack.get()
        index = -1
        for position in range(len(stack) - 1, -1, -1):
            if stack[position].span.id == span.id:
                index = position
                break
        if index >= 0:
            self._stack.set(stack[:index] + stack[index + 1 :])
        self._forward("on_span_end", span)

    def current_span_id(self) -> str | None:
        """栈顶 span 的 ``id``；空栈 ⇒ ``None``。"""
        stack = self._stack.get()
        return stack[-1].span.id if stack else None

    def current_node_span(self) -> Span | None:
        """最近的节点级 span（供 helpers 继承关联键）。"""
        for frame in reversed(self._stack.get()):
            if frame.kind == "node":
                return frame.span
        return None

    def make_model_span(self, obj: Any) -> Span | None:
        """构造模型开始 span；无活动节点 span ⇒ ``None``。"""
        node_span = self.current_node_span()
        if node_span is None:
            return None
        attributes: dict[str, Any] = {"gen_ai.operation.name": "chat"}
        model = _model_name(obj)
        if model is not None:
            attributes["gen_ai.request.model"] = model
        name = f"chat {model}" if model is not None else "chat"
        return self._new_span(node_span, name, attributes)

    def make_tool_span(self, obj: Any, call_id: str | None = None) -> Span | None:
        """构造工具开始 span；无活动节点 span ⇒ ``None``。"""
        node_span = self.current_node_span()
        if node_span is None:
            return None
        raw_name = getattr(obj, "name", "")
        tool_name = raw_name if isinstance(raw_name, str) else str(raw_name)
        attributes: dict[str, Any] = {
            "gen_ai.operation.name": "execute_tool",
            "gen_ai.tool.name": tool_name,
        }
        if isinstance(call_id, str) and call_id:
            attributes["gen_ai.tool.call.id"] = call_id
        return self._new_span(node_span, f"execute_tool {tool_name}", attributes)

    def finish_span(self, start: Span | None, error_type: str | None = None) -> Span | None:
        """构造同 ``id`` 的结束 span（严格正耗时；失败时写 ``error.type``）。"""
        if start is None:
            return None
        end_time, _ = end_iso_after(start.start_time)
        attributes = dict(start.attributes)
        if error_type is not None:
            attributes["error.type"] = error_type
        return Span(
            id=start.id,
            name=start.name,
            attributes=attributes,
            parent=start.parent,
            start_time=start.start_time,
            end_time=end_time,
            context=start.context,
            thread_id=start.thread_id,
            run_id=start.run_id,
            node=start.node,
            checkpoint_id=start.checkpoint_id,
        )

    def _new_span(
        self,
        node_span: Span,
        name: str,
        attributes: dict[str, Any],
    ) -> Span:
        start_time, _ = utc_now_iso_ns()
        return Span(
            id=uuid.uuid4().hex,
            name=name,
            attributes=attributes,
            parent=self.current_span_id(),
            start_time=start_time,
            end_time=None,
            context={},
            thread_id=node_span.thread_id,
            run_id=node_span.run_id,
            node=node_span.node,
            checkpoint_id=node_span.checkpoint_id,
        )

    def _forward(self, method: str, span: Span) -> None:
        """把快照转发给接收端；接收端异常 MUST 被隔离。"""
        receiver = self._receiver
        if receiver is None:
            return
        callback = getattr(receiver, method, None)
        if callback is None:
            return
        try:
            callback(span)
        except Exception:
            logger.warning(
                "span receiver %s failed; observable write dropped",
                method,
                exc_info=True,
            )
