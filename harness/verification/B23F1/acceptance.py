#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""B23F1 一键验收：A1–A4（离线 / 合法 PNG / 同名方法 / 零出站）。"""

from __future__ import annotations

import importlib.metadata
import socket
import struct
import sys
from typing import Any, TypedDict
import zlib

from freegraph.graph import END, START, StateGraph

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ENV = 2

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
WIDTH = 64
HEIGHT = 64
RAW_LENGTH = HEIGHT * (1 + WIDTH * 3)


class State(TypedDict, total=False):
    value: int


def _a(state: State) -> dict[str, int]:
    return {"value": state.get("value", 0) + 1}


def _b(state: State) -> dict[str, int]:
    return {"value": state.get("value", 0) + 10}


def _route(state: State) -> str:
    return "b"


def _build() -> Any:
    builder = StateGraph(State)
    builder.add_node("a", _a)
    builder.add_node("b", _b)
    builder.add_edge(START, "a")
    builder.add_conditional_edges("a", _route, ["b", END])
    builder.add_edge("b", END)
    return builder.compile()


class _SocketGuard:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *_args: object, **_kwargs: object) -> object:
        self.calls += 1
        raise AssertionError("框架尝试出站")


def _png_failures(data: Any) -> list[str]:
    failures: list[str] = []
    if type(data) is not bytes:
        return [f"return type is {type(data).__name__}, not bytes"]
    if not data:
        return ["empty bytes"]
    if not data.startswith(PNG_SIGNATURE):
        return ["PNG signature mismatch"]

    pos = 8
    chunks: list[tuple[bytes, bytes, int]] = []
    while pos < len(data):
        if pos + 12 > len(data):
            failures.append("truncated chunk header")
            break
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        if len(body) != length or pos + 12 + length > len(data):
            failures.append(f"truncated chunk {chunk_type!r}")
            break
        crc = struct.unpack(">I", data[pos + 8 + length : pos + 12 + length])[0]
        if (zlib.crc32(chunk_type + body) & 0xFFFFFFFF) != crc:
            failures.append(f"bad CRC for {chunk_type!r}")
        chunks.append((chunk_type, body, length))
        pos += 12 + length
    if pos != len(data):
        failures.append("trailing bytes after last chunk")
    if not chunks or chunks[0][0] != b"IHDR" or chunks[0][2] != 13:
        failures.append("first chunk is not IHDR(13)")
    else:
        width, height, bit_depth, color_type, compression, filter_method, interlace = (
            struct.unpack(">IIBBBBB", chunks[0][1])
        )
        if (width, height) != (WIDTH, HEIGHT):
            failures.append(f"IHDR size is {width}x{height}")
        if (bit_depth, color_type) != (8, 2):
            failures.append(f"IHDR bit depth / color type is {bit_depth}/{color_type}")
        if (compression, filter_method, interlace) != (0, 0, 0):
            failures.append("IHDR compression / filter / interlace is not 0/0/0")
    if not chunks or chunks[-1][0] != b"IEND" or chunks[-1][2] != 0:
        failures.append("last chunk is not IEND(0)")
    idat = b"".join(body for chunk_type, body, _ in chunks if chunk_type == b"IDAT")
    if not idat:
        failures.append("missing IDAT")
    else:
        try:
            raw = zlib.decompress(idat)
        except zlib.error as exc:
            failures.append(f"IDAT decompression failed: {exc}")
        else:
            if len(raw) != RAW_LENGTH:
                failures.append(f"IDAT raw length is {len(raw)}, expected {RAW_LENGTH}")
            colors: set[tuple[int, int, int]] = set()
            for y in range(HEIGHT):
                row = raw[y * (1 + WIDTH * 3) : (y + 1) * (1 + WIDTH * 3)]
                if row[0] != 0:
                    failures.append("non-zero scanline filter")
                    break
                for x in range(WIDTH):
                    colors.add(tuple(row[1 + x * 3 : 4 + x * 3]))
            if len(colors) < 3:
                failures.append(f"only {len(colors)} distinct colors")
    return failures


def main() -> int:
    try:
        compiled = _build()
        graph = compiled.get_graph(xray=True)
    except Exception as exc:  # noqa: BLE001
        print(f"B23F1 acceptance: FAIL ({type(exc).__name__}: {exc})")
        return EXIT_ENV

    guard = _SocketGuard()
    original_socket = socket.socket
    socket.socket = guard  # type: ignore[assignment]
    try:
        data = graph.draw_mermaid_png()
        repeat = graph.draw_mermaid_png()
        empty = type(graph)().draw_mermaid_png()
    except Exception as exc:  # noqa: BLE001
        print(f"B23F1 acceptance: FAIL (draw_mermaid_png: {type(exc).__name__}: {exc})")
        return EXIT_FAIL
    finally:
        socket.socket = original_socket  # type: ignore[assignment]

    failures: list[str] = []
    if not hasattr(graph, "draw_mermaid_png"):
        failures.append("A3 Graph 缺少 draw_mermaid_png")
    if type(graph).__module__ != "freegraph.contracts.graph" or type(graph).__name__ != "Graph":
        failures.append("A3 返回类型不是 freegraph.contracts.graph.Graph")
    failures.extend(f"A2 {item}" for item in _png_failures(data))
    if repeat != data:
        failures.append("A2 同一 Graph 两次调用字节不一致")
    if empty != data:
        failures.append("A2 空图与普通图字节不一致")
    if guard.calls != 0:
        failures.append(f"A4 框架出站 != 0（{guard.calls}）")

    try:
        requires = importlib.metadata.requires("freegraph") or []
    except importlib.metadata.PackageNotFoundError:
        requires = []
    forbidden = ("langchain", "langsmith", "langgraph")
    if any(any(name in requirement for name in forbidden) for requirement in requires):
        failures.append("A4 依赖闭包含 langchain/langsmith/langgraph")

    if failures:
        print("B23F1 acceptance: FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return EXIT_FAIL
    print("B23F1 acceptance: PASS")
    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
