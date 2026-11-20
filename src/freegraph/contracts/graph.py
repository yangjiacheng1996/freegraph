# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""契约层的**图结构自有类型**——:class:`Graph` / :class:`Node` / :class:`Edge`。

与上游 ``langchain_core.runnables.graph`` **同名但自有实现**——**不复用、不复制**
上游代码（宪法原则 IX：避免「声明兼容」被读成「暗示 affiliation」；
复用上游类型即把 ``langchain-core`` → ``langsmith`` 拖回依赖树，直接破原则 I）。

> **路径说明**：本模块是 ``freegraph.contracts.graph``（**契约层**的图结构数据类）；
> B2F2 将交付 ``freegraph.graph``（**公开门面**：``StateGraph`` / ``START`` / ``END``）。
> 二者路径不同、语义不同，**互不冲突**。

本模块**零** freegraph 内部 import、**零**第三方 import（仅标准库）。
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
import string
import struct
from typing import Any
import zlib

__all__ = [
    "Graph",
    "Node",
    "Edge",
]


_SAFE_ID_CHARS = frozenset(string.ascii_letters + string.digits + "_-")


def _safe_id(label: str) -> str:
    """把节点名映射为**确定性、Mermaid 合法**的节点 id。

    与上游 ``_to_safe_id``（``graph_mermaid.py:255-266``）逐字同款：
    保留 ASCII 字母 / 数字 / ``_`` / ``-``，其余字符写成 ``\\`` + 小写十六进制码点。
    """
    return "".join(
        char if char in _SAFE_ID_CHARS else "\\" + format(ord(char), "x")
        for char in label
    )


def _escape_label(text: str) -> str:
    """转义 mermaid 标签（节点标签与边标签同款）。

    处理顺序敏感：先处理 ``#``，避免后续生成的实体被二次转义。
    """
    text = str(text)
    text = text.replace("#", "#35;")
    text = text.replace('"', "#quot;")
    text = text.replace("<", "#lt;").replace(">", "#gt;")
    text = text.replace("&", "#amp;").replace("|", "#124;").replace("\\", "#92;")
    # 换行转义必须最后做，避免刚插入的 ``<br/>`` 被 ``<`` / ``>`` 二次转义。
    text = text.replace("\r\n", "<br/>").replace("\n", "<br/>").replace("\r", "<br/>")
    return text


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_WIDTH = 64
_PNG_HEIGHT = 64
_PNG_BIT_DEPTH = 8
_PNG_COLOR_TYPE = 2
_PNG_COMPRESSION = 0
_PNG_FILTER_METHOD = 0
_PNG_INTERLACE = 0
_PNG_BACKGROUND = (245, 245, 245)
_PNG_BOX_FILL = (217, 232, 255)
_PNG_INK = (51, 102, 153)
_PNG_BOXES = ((8, 24, 19, 39), (26, 24, 37, 39), (44, 24, 55, 39))
_PNG_CONNECTORS = ((20, 25, 32), (38, 43, 32))


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """编码一个 PNG 块（长度 + 类型 + 数据 + CRC-32）。"""
    body = chunk_type + data
    return (
        struct.pack(">I", len(data))
        + body
        + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    )


def _placeholder_rgb_rows() -> bytes:
    """生成 64×64 固定示意图标的原始扫描行（每行 filter 0 + RGB）。"""
    background = bytes(_PNG_BACKGROUND)
    box_fill = bytes(_PNG_BOX_FILL)
    ink = bytes(_PNG_INK)
    rows = [bytearray(background * _PNG_WIDTH) for _ in range(_PNG_HEIGHT)]
    for x0, y0, x1, y1 in _PNG_BOXES:
        for y in range(y0, y1 + 1):
            row = rows[y]
            for x in range(x0, x1 + 1):
                color = ink if x in (x0, x1) or y in (y0, y1) else box_fill
                offset = x * 3
                row[offset : offset + 3] = color
    for x0, x1, y in _PNG_CONNECTORS:
        row = rows[y]
        for x in range(x0, x1 + 1):
            offset = x * 3
            row[offset : offset + 3] = ink
    raw = bytearray()
    for row in rows:
        raw.append(0)
        raw.extend(row)
    return bytes(raw)


def _encode_placeholder_png(rows: bytes) -> bytes:
    """把原始扫描行编码为最小合法 PNG（IHDR / IDAT / IEND）。"""
    ihdr = struct.pack(
        ">IIBBBBB",
        _PNG_WIDTH,
        _PNG_HEIGHT,
        _PNG_BIT_DEPTH,
        _PNG_COLOR_TYPE,
        _PNG_COMPRESSION,
        _PNG_FILTER_METHOD,
        _PNG_INTERLACE,
    )
    return (
        _PNG_SIGNATURE
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(rows, 9))
        + _png_chunk(b"IEND", b"")
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class Node:
    """**图节点元素** —— 图中的一个节点（**3 字段**）。

    =========== ========================= ============= =================================
    字段         类型                       缺省           语义
    =========== ========================= ============= =================================
    ``id``       ``str``                    —（必填）       **节点名**，唯一
    ``name``     ``str | None``             ``None`` → **归一为 ``id``**  **别名**
    ``metadata`` ``Mapping[str, Any]``     空映射          附加信息
    =========== ========================= ============= =================================

    **``name`` 的输入类型是 ``str | None``，但构造后恒为 ``str``**（缺省归一为
    ``id``）——读侧 MUST 视其为 ``str``，**无需** ``or`` 回落。

    **浅不可变**：对象本身不可改（``frozen=True``），``metadata`` 装的是
    ``__post_init__`` 里拷出的新映射，其**内容**仍可变。

    **不可哈希**：``metadata`` 是映射 ⇒ ``hash()`` 抛 ``TypeError``。

    **构造期零值校验**：不校验 ``id`` 非空 / 唯一（由**生产者**保证）。

    **对应契约**：C13（图结构）。``Node.name`` 是**图展示名**，不是已作废的
    C25 节点注册别名；缺省归一为 ``id``。
    """

    id: str
    name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """构造期把 ``name`` **归一为 ``id``**、把 ``metadata`` **浅拷贝**。

        ``frozen=True`` 下普通赋值会抛 ``FrozenInstanceError``，
        故 MUST 用 ``object.__setattr__``。拷贝为**浅拷贝**（``dict(...)``）。

        本方法**不校验值**——``id`` 是否非空 / 唯一由**生产者**保证。
        """
        if self.name is None:
            object.__setattr__(self, "name", self.id)
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True, kw_only=True)
class Edge:
    """**边元素** —— 图中的一条边（**4 字段**）。

    =============== ================== ========== ==================================
    字段             类型                缺省         语义
    =============== ================== ========== ==================================
    ``source``       ``str``             —（必填）    起点**节点名**
    ``target``       ``str``             —（必填）    终点**节点名**
    ``conditional``  ``bool``            ``False``   是否**条件边**
    ``condition``    ``str | None``      ``None``    条件名（非条件边时为空）
    =============== ================== ========== ==================================

    **不变式**（本层**不校验**）：``add_conditional_edges`` 分支边
    ``conditional=True`` 时 ``condition`` MUST 非空；**节点声明的无标签边**
    （``Command[Literal]`` / ``destinations`` 序列）``condition is None`` **合法**
    （与上游 ``Edge.data=None`` 同款 · T-6）。值级守卫由**生产者**（图定义层）保证。

    **不可哈希**：四字段**全是标量**，dataclass **会自动生成** ``__hash__``
    ⇒ 类体 MUST **显式**写 ``__hash__ = None``，才兑现「四类统一不可哈希」。

    **对应契约**：C13 / C14（C14 的 mermaid 渲染消费本类型）。
    """

    source: str
    target: str
    conditional: bool = False
    condition: str | None = None

    #: 显式置 ``None`` ⇒ 本类**不可哈希**（dataclass 的 ``_hash_action`` 对
    #: 「类体中显式定义 ``__hash__``」的组合**不做覆盖**）。
    __hash__ = None  # type: ignore[assignment]


@dataclass(frozen=True, slots=True, kw_only=True)
class Graph:
    """**图结构** —— 节点集合与边集合的不可变定格（**2 字段**）。

    ========= ================== ======= ==============================
    字段      类型                缺省   语义
    ========= ================== ======= ==============================
    ``nodes`` ``tuple[Node, ...]`` ``()`` 节点集合（**不可变元组**）
    ``edges`` ``tuple[Edge, ...]`` ``()`` 边集合（**不可变元组**）
    ========= ================== ======= ==============================

    **容器用元组**而非上游的 ``dict[str, Node]`` / ``list[Edge]``——与不可变记录
    自洽，且避免「顺序不保证」的额外语义。

    **不变式**（本层**不校验**）：``nodes`` 的元素 ``id`` **唯一**——去重属
    图定义层。

    **不可哈希**：元素不可哈希 ⇒ 自身不可哈希。

    **对应契约**：C13。
    """

    nodes: tuple[Node, ...] = ()
    edges: tuple[Edge, ...] = ()

    #: 显式置 ``None`` ⇒ 本类**不可哈希**（冻结面：「``Node`` / ``Edge`` /
    #: ``Graph`` / ``Span`` **统一不可哈希**」——dataclass 默认会为本类生成
    #: ``__hash__``，那会让「空图可哈希、非空图不可哈希」的不一致漏出去）。
    __hash__ = None  # type: ignore[assignment]

    def draw_mermaid(self) -> str:
        """导出**纯本地**的 mermaid 文本（C14 · B22F1）。

        输出以 ``graph TD;`` 开头；节点 id 经 :func:`_safe_id` 安全化，
        节点 / 边标签经 :func:`_escape_label` 转义；普通边实线、条件边虚线。
        空图返回 ``graph TD;\\n``；同图同文本（确定性）。
        """
        lines = ["graph TD;"]
        for node in self.nodes:
            name = node.name if node.name is not None else node.id
            lines.append(f'\t{_safe_id(node.id)}["{_escape_label(name)}"];')
        for edge in self.edges:
            source = _safe_id(edge.source)
            target = _safe_id(edge.target)
            if edge.conditional:
                if edge.condition is None:
                    lines.append(f"\t{source} -.-> {target};")
                else:
                    label = _escape_label(edge.condition)
                    lines.append(
                        f"\t{source} -. &nbsp;{label}&nbsp; .-> {target};"
                    )
            else:
                lines.append(f"\t{source} --> {target};")
        return "\n".join(lines) + "\n"

    def draw_mermaid_png(self) -> bytes:
        """导出**纯本地**的 PNG 字节（C15 · B23F1）。

        v1 只返回固定示意图标的占位 PNG；先调用 :meth:`draw_mermaid` 作为唯一图源，
        但 v1 不把文本像素化。对任何 ``Graph`` 成功；零网络 / 零环境变量 /
        零文件副作用；同一 / 不同 ``Graph`` 均返回相同字节。
        """
        _ = self.draw_mermaid()
        return _encode_placeholder_png(_placeholder_rgb_rows())
