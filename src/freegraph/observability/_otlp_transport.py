# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 · **OTLP gRPC 传输**（B21F1 · 内部模块）。

只使用**官方**编码器 ``encode_spans`` + 官方 ``TraceServiceStub``；不写
protobuf / OTLP wire format / 手写 gRPC payload。每次导出使用短生命周期
channel，``finally`` 关闭；**不读环境变量、不重试、不起后台线程**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import grpc
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import (
    TraceServiceStub,
)
from opentelemetry.sdk.trace import ReadableSpan

__all__ = ["export_spans"]


def export_spans(
    spans: Sequence[ReadableSpan],
    *,
    endpoint: str,
    insecure: bool,
    headers: Sequence[tuple[str, str]],
    timeout: float,
) -> Any:
    """把 ``ReadableSpan`` 编码为 OTLP 请求并经官方 gRPC stub 发送一次。

    异常由调用方隔离；本函数**不重试**，也不读取任何环境变量。
    """
    request = encode_spans(list(spans))
    if insecure:
        channel = grpc.insecure_channel(endpoint)
    else:
        channel = grpc.secure_channel(endpoint, grpc.ssl_channel_credentials())
    try:
        stub = TraceServiceStub(channel)
        return stub.Export(
            request,
            metadata=tuple(headers),
            timeout=timeout,
        )
    finally:
        channel.close()
