# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 运行期测试的小工具：接收端 + 双绑定上下文。"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


class RecordingReceiver:
    def __init__(self) -> None:
        self.started: list[Any] = []
        self.ended: list[Any] = []

    def on_span_start(self, span: Any) -> None:
        self.started.append(span)

    def on_span_end(self, span: Any) -> None:
        self.ended.append(span)


@contextmanager
def bind_producer(producer: Any) -> Iterator[Any]:
    from freegraph.observability._producer import bind_tracer as bind_l5
    from freegraph.runtime._span_hook import bind_span_tracer

    with bind_span_tracer(producer), bind_l5(producer):
        yield producer


def node_spans(receiver: RecordingReceiver) -> list[Any]:
    return [span for span in receiver.started if not span.attributes]
