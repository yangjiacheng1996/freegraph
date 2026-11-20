# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 · **模型 / 工具调用辅助** —— 属 **B18F1**（内部模块）。

提供 :func:`invoke_model` / :func:`invoke_tool` 两个**显式**一次性调用辅助：
只对用户主动传入的鸭子类型对象产生子 span；不隐式拦截节点里的任意
``.invoke``。形状校验与生产开关无关；节点外 / 无 tracer 时等价于直接调用。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import inspect
from typing import Any

from ._producer import SpanProducer, current_tracer

__all__ = ["invoke_model", "invoke_tool"]


def _is_tool_shape(obj: Any) -> bool:
    """工具形状：``name``（``str``）+ ``description`` 存在 + callable ``invoke``。"""
    return (
        isinstance(getattr(obj, "name", None), str)
        and hasattr(obj, "description")
        and callable(getattr(obj, "invoke", None))
    )


def _is_model_shape(obj: Any) -> bool:
    """模型形状：callable ``invoke`` 且非工具形状。"""
    return callable(getattr(obj, "invoke", None)) and not _is_tool_shape(obj)


def _error_type(exc: BaseException) -> str:
    """低基数异常类名；空则 ``_OTHER``。"""
    name = type(exc).__name__
    return name if name else "_OTHER"


def _invoke_direct(obj: Any, argument: Any) -> Any:
    """无 span 的直接调用 + awaitable 拒绝（Q16）。"""
    result = obj.invoke(argument)
    if inspect.isawaitable(result):
        if inspect.iscoroutine(result):
            result.close()
        raise TypeError("v1 only supports synchronous invoke; awaitable result rejected")
    return result


def _invoke_with_span(
    tracer: SpanProducer,
    start: Any,
    obj: Any,
    argument: Any,
) -> Any:
    """在生产接缝内调用，并保证开始 / 结束快照成对。"""
    tracer.on_span_start(start)
    try:
        result = obj.invoke(argument)
        if inspect.isawaitable(result):
            if inspect.iscoroutine(result):
                result.close()
            raise TypeError(
                "v1 only supports synchronous invoke; awaitable result rejected"
            )
    except BaseException as exc:
        tracer.on_span_end(tracer.finish_span(start, _error_type(exc)))
        raise
    tracer.on_span_end(tracer.finish_span(start))
    return result


def invoke_model(obj: Any, input: Any, *, call_id: str | None = None) -> Any:
    """调用鸭子类型模型；节点执行期间产生模型 span。"""
    if not _is_model_shape(obj):
        raise TypeError(
            "invoke_model expects an object with callable invoke and non-tool shape"
        )
    tracer = current_tracer()
    if tracer is None or tracer.current_node_span() is None:
        return _invoke_direct(obj, input)
    start = tracer.make_model_span(obj)
    if start is None:
        return _invoke_direct(obj, input)
    return _invoke_with_span(tracer, start, obj, input)


def invoke_tool(obj: Any, args: Any, *, call_id: str | None = None) -> Any:
    """调用鸭子类型工具；节点执行期间产生工具 span。"""
    if not _is_tool_shape(obj):
        raise TypeError(
            "invoke_tool expects an object with name (str), description, and callable invoke"
        )
    tracer = current_tracer()
    if tracer is None or tracer.current_node_span() is None:
        return _invoke_direct(obj, args)
    start = tracer.make_tool_span(obj, call_id)
    if start is None:
        return _invoke_direct(obj, args)
    return _invoke_with_span(tracer, start, obj, args)
