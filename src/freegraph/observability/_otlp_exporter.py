# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 · **可选 OTLP 导出器**（B21F1 · 公开符号）。

``OtlpExporter`` 实现 ``TraceSink`` 三方法，经既有
``StateGraph.compile(*, tracer=...)`` 注入。默认关闭；不读任何环境变量；
导出失败不阻断图执行；v1 只做同步导出。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Mapping
from typing import Any

from freegraph.contracts.trace import Span

__all__ = ["OtlpExporter"]

_LOG = logging.getLogger("freegraph.observability.otlp")
_INSTALL_HINT = 'pip install "freegraph[otlp]"'


def _validate_endpoint(endpoint: Any) -> str:
    if not isinstance(endpoint, str) or not endpoint:
        raise ValueError("endpoint must be a non-empty 'host:port' string")
    if "://" in endpoint:
        raise ValueError("endpoint must be 'host:port' without a URL scheme")
    if any(char.isspace() for char in endpoint):
        raise ValueError("endpoint must not contain whitespace")
    host: str
    port_text: str
    if endpoint.startswith("["):
        closing = endpoint.find("]")
        if closing <= 1:
            raise ValueError("endpoint has an invalid IPv6 host")
        host = endpoint[1:closing]
        rest = endpoint[closing + 1 :]
        if not rest.startswith(":"):
            raise ValueError("endpoint must be 'host:port'")
        port_text = rest[1:]
    else:
        if endpoint.count(":") != 1:
            raise ValueError("endpoint must be 'host:port'")
        host, port_text = endpoint.split(":", 1)
    if not host:
        raise ValueError("endpoint host must be non-empty")
    try:
        port = int(port_text)
    except ValueError as exc:
        raise ValueError("endpoint port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("endpoint port must be in 1..65535")
    return endpoint


def _validate_headers(headers: Any) -> tuple[tuple[str, str], ...]:
    if headers is None:
        return ()
    if not isinstance(headers, Mapping):
        raise ValueError("headers must be a mapping of str to str")
    items: list[tuple[str, str]] = []
    for key, value in headers.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("headers keys and values must be str")
        items.append((key, value))
    return tuple(items)


def _validate_timeout(timeout: Any) -> float:
    if timeout is None:
        return 10.0
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ValueError("timeout must be a positive number or None")
    if timeout <= 0:
        raise ValueError("timeout must be a positive number or None")
    return float(timeout)


def _import_otlp_module(name: str) -> Any:
    try:
        if name == "mapping":
            from . import _otlp_mapping as module
        else:
            from . import _otlp_transport as module
    except ImportError as exc:  # pragma: no cover - 缺 extra 的显式路径
        raise ImportError(
            f"OtlpExporter requires the optional OTLP dependencies; "
            f'install them with {_INSTALL_HINT}'
        ) from exc
    return module


class OtlpExporter:
    """把 L1 ``Span`` 同步导出到用户显式提供的 OTLP 端点 / 导出器。"""

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        exporter: object | None = None,
        insecure: bool = False,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        on_error: Any = None,
    ) -> None:
        if not isinstance(insecure, bool):
            raise ValueError("insecure must be a bool")
        if on_error is not None and not callable(on_error):
            raise ValueError("on_error must be callable or None")
        if endpoint is None and exporter is None:
            raise ValueError("exactly one of endpoint / exporter must be provided")
        if endpoint is not None and exporter is not None:
            raise ValueError("exactly one of endpoint / exporter must be provided")

        self._lock = threading.Lock()
        self._export_errors = 0
        self._last_error: BaseException | None = None
        self._on_error = on_error
        self._headers: tuple[tuple[str, str], ...] = ()
        self._timeout = 10.0
        self._insecure = False
        self._endpoint: str | None = None
        self._exporter: Any = None
        self._mapping: Any = None
        self._transport: Any = None
        self._failure_result: Any = None

        if exporter is not None:
            if not callable(getattr(exporter, "export", None)):
                raise ValueError("exporter must provide a callable export() method")
            if insecure is not False:
                raise ValueError("insecure is only valid with endpoint=")
            if headers is not None:
                raise ValueError("headers is only valid with endpoint=")
            if timeout is not None:
                raise ValueError("timeout is only valid with endpoint=")
            mapping = _import_otlp_module("mapping")
            try:
                from opentelemetry.sdk.trace.export import SpanExportResult
            except ImportError as exc:  # pragma: no cover - 缺 extra 的显式路径
                raise ImportError(
                    f"OtlpExporter requires the optional OTLP dependencies; "
                    f'install them with {_INSTALL_HINT}'
                ) from exc
            self._exporter = exporter
            self._mapping = mapping
            self._failure_result = SpanExportResult.FAILURE
            return

        self._endpoint = _validate_endpoint(endpoint)
        self._headers = _validate_headers(headers)
        self._timeout = _validate_timeout(timeout)
        self._insecure = insecure
        self._mapping = _import_otlp_module("mapping")
        self._transport = _import_otlp_module("transport")

    @property
    def export_errors(self) -> int:
        """累计未成功导出的完整 span 数（只读）。"""
        with self._lock:
            return self._export_errors

    @property
    def last_error(self) -> BaseException | None:
        """最近一次失败对象（成功导出不清空；只读）。"""
        with self._lock:
            return self._last_error

    def on_span_start(self, span: Span) -> None:
        """no-op —— 只导出有 ``end_time`` 的完整 span。"""
        return None

    def current_span(self) -> Span | None:
        """导出器是接收端，不伪造当前上下文。"""
        return None

    def on_span_end(self, span: Span) -> None:
        """同步导出完整 span；失败隔离为四路诊断，不阻断图执行。"""
        if span.end_time is None:
            return
        failure: BaseException | None = None
        with self._lock:
            try:
                result = self._mapping.map_span(span)
                if result.no_export:
                    return
                if result.skip_reason is not None:
                    failure = ValueError(result.skip_reason)
                elif self._transport is not None:
                    self._transport.export_spans(
                        [result.readable],
                        endpoint=self._endpoint,
                        insecure=self._insecure,
                        headers=self._headers,
                        timeout=self._timeout,
                    )
                else:
                    outcome = self._exporter.export([result.readable])
                    if outcome == self._failure_result:
                        failure = RuntimeError(
                            "SpanExporter.export returned FAILURE"
                        )
            except Exception as exc:  # noqa: BLE001 - 导出失败必须隔离
                failure = exc
            if failure is not None:
                self._export_errors += 1
                self._last_error = failure
        if failure is not None:
            _LOG.warning("OTLP export failed for span %s: %s", span.id, failure)
            callback = self._on_error
            if callback is not None:
                try:
                    callback(failure)
                except Exception as exc:  # noqa: BLE001 - 回调自身异常隔离
                    _LOG.warning("OtlpExporter on_error raised: %s", exc)
