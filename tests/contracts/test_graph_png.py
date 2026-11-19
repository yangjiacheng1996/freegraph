# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B23F1 · ``Graph.draw_mermaid_png()`` 的 PNG 契约（C15）。"""

from __future__ import annotations

import struct
import zlib

import pytest

from freegraph.contracts import Edge, Graph, Node

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
WIDTH = 64
HEIGHT = 64
RAW_LENGTH = HEIGHT * (1 + WIDTH * 3)
BACKGROUND = (245, 245, 245)
BOX_FILL = (217, 232, 255)
INK = (51, 102, 153)


def _parse_chunks(data: bytes) -> list[tuple[bytes, bytes, int]]:
    """按 PNG 规范逐块解析并校验长度 / CRC；返回 ``(type, data, length)``。"""
    assert isinstance(data, bytes)
    assert data.startswith(PNG_SIGNATURE)
    pos = 8
    chunks: list[tuple[bytes, bytes, int]] = []
    while pos < len(data):
        assert pos + 12 <= len(data)
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        crc = struct.unpack(">I", data[pos + 8 + length : pos + 12 + length])[0]
        assert len(body) == length
        assert (zlib.crc32(chunk_type + body) & 0xFFFFFFFF) == crc
        chunks.append((chunk_type, body, length))
        pos += 12 + length
    assert pos == len(data)
    return chunks


def _decompress_idat(data: bytes) -> bytes:
    chunks = _parse_chunks(data)
    idat = b"".join(body for chunk_type, body, _ in chunks if chunk_type == b"IDAT")
    assert idat
    return zlib.decompress(idat)


def _decode_colors(data: bytes) -> set[tuple[int, int, int]]:
    raw = _decompress_idat(data)
    assert len(raw) == RAW_LENGTH
    colors: set[tuple[int, int, int]] = set()
    for y in range(HEIGHT):
        row = raw[y * (1 + WIDTH * 3) : (y + 1) * (1 + WIDTH * 3)]
        assert row[0] == 0
        for x in range(WIDTH):
            colors.add(tuple(row[1 + x * 3 : 4 + x * 3]))
    return colors


def _conditional_graph() -> Graph:
    return Graph(
        nodes=(Node(id="a"), Node(id="b"), Node(id="c")),
        edges=(
            Edge(source="a", target="b", conditional=True, condition="route"),
            Edge(source="a", target="c", conditional=True, condition=None),
        ),
    )


def test_returns_bytes_for_graph() -> None:
    data = _conditional_graph().draw_mermaid_png()
    assert type(data) is bytes
    assert data


def test_empty_graph_returns_bytes() -> None:
    data = Graph().draw_mermaid_png()
    assert type(data) is bytes
    assert data


def test_degenerate_graph_returns_bytes() -> None:
    graph = Graph(
        nodes=(Node(id="__start__"), Node(id="__end__")),
        edges=(Edge(source="__start__", target="__end__"),),
    )
    assert graph.draw_mermaid_png()


def test_return_type_is_exactly_bytes() -> None:
    assert type(Graph().draw_mermaid_png()) is bytes


def test_length_is_positive() -> None:
    assert len(Graph().draw_mermaid_png()) > 0


def test_extra_arguments_raise_typeerror() -> None:
    with pytest.raises(TypeError):
        Graph().draw_mermaid_png("unexpected")  # type: ignore[call-arg]


def test_signature_and_first_chunk_is_ihdr() -> None:
    chunks = _parse_chunks(Graph().draw_mermaid_png())
    assert chunks[0][0] == b"IHDR"
    assert chunks[0][2] == 13


def test_ihdr_is_64x64_rgb8() -> None:
    _, body, _ = _parse_chunks(Graph().draw_mermaid_png())[0]
    width, height, bit_depth, color_type, compression, filter_method, interlace = (
        struct.unpack(">IIBBBBB", body)
    )
    assert (width, height) == (WIDTH, HEIGHT)
    assert (bit_depth, color_type) == (8, 2)
    assert (compression, filter_method, interlace) == (0, 0, 0)


def test_all_chunk_crcs_are_valid() -> None:
    data = Graph().draw_mermaid_png()
    for chunk_type, body, length in _parse_chunks(data):
        assert chunk_type
        assert len(chunk_type) == 4
        assert length == len(body)


def test_idat_decompresses_to_expected_scanlines() -> None:
    raw = _decompress_idat(Graph().draw_mermaid_png())
    assert len(raw) == RAW_LENGTH
    for y in range(HEIGHT):
        assert raw[y * (1 + WIDTH * 3)] == 0


def test_iend_is_last_and_no_trailing_bytes() -> None:
    chunks = _parse_chunks(Graph().draw_mermaid_png())
    assert chunks[-1][0] == b"IEND"
    assert chunks[-1][2] == 0


def test_chunk_sequence_is_exactly_ihdr_idat_iend() -> None:
    assert [chunk_type for chunk_type, _, _ in _parse_chunks(Graph().draw_mermaid_png())] == [
        b"IHDR",
        b"IDAT",
        b"IEND",
    ]


def test_palette_has_at_least_three_colors() -> None:
    colors = _decode_colors(Graph().draw_mermaid_png())
    assert len(colors) >= 3
    assert {BACKGROUND, BOX_FILL, INK} <= colors


def test_image_is_not_monochrome() -> None:
    assert len(_decode_colors(Graph().draw_mermaid_png())) > 1


def test_two_calls_are_byte_identical() -> None:
    graph = Graph()
    assert graph.draw_mermaid_png() == graph.draw_mermaid_png()


def test_different_graphs_are_byte_identical() -> None:
    assert Graph().draw_mermaid_png() == _conditional_graph().draw_mermaid_png()


def test_special_character_node_names_return_png() -> None:
    graph = Graph(
        nodes=(
            Node(id='a"b'),
            Node(id="x\ny"),
            Node(id="中文"),
            Node(id="🙂"),
        )
    )
    assert graph.draw_mermaid_png()


def test_graph_with_conditional_and_declared_edges_returns_png() -> None:
    assert _conditional_graph().draw_mermaid_png()


def test_graph_with_join_edge_returns_png() -> None:
    graph = Graph(
        nodes=(Node(id="a"), Node(id="b"), Node(id="c")),
        edges=(Edge(source="a", target="c"), Edge(source="b", target="c")),
    )
    assert graph.draw_mermaid_png()


def test_png_calls_draw_mermaid_once_and_ignores_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = Graph(nodes=(Node(id="a"),))
    baseline = graph.draw_mermaid_png()
    calls = {"n": 0}

    def fake_draw_mermaid(self: Graph) -> str:
        calls["n"] += 1
        return 'graph TD;\n\tzzz["this text must not be rendered"];'

    monkeypatch.setattr(Graph, "draw_mermaid", fake_draw_mermaid)
    assert graph.draw_mermaid_png() == baseline
    assert calls["n"] == 1


def test_draw_mermaid_output_is_unchanged_by_png() -> None:
    graph = _conditional_graph()
    before = graph.draw_mermaid()
    graph.draw_mermaid_png()
    assert graph.draw_mermaid() == before


def test_ipython_image_accepts_when_available() -> None:
    pytest.importorskip("IPython")
    from IPython.display import Image

    image = Image(Graph().draw_mermaid_png())
    assert image is not None
