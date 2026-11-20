# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 —— **B18F1** 的 span 生产入口。

本模块提供：

* :class:`SpanProducer` —— run-scoped 当前 span 栈 / 父子关系 / 接收端转发；
* :func:`invoke_model` / :func:`invoke_tool` —— 模型 / 工具显式调用辅助。

**不是公开门面**（``freegraph.graph``）的组成部分；``import freegraph``
不会加载本模块（ARCH-2）。本模块零 L2 import、零第三方依赖、零环境变量。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from ._invoke import invoke_model, invoke_tool
from ._producer import SpanProducer

__all__ = ["SpanProducer", "invoke_model", "invoke_tool"]
