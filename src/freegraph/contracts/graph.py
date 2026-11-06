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
from typing import Any

__all__ = [
    "Graph",
    "Node",
    "Edge",
]


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

    **对应契约**：C13（图结构）/ C25（节点命名）。
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

    **不变式**（本层**不校验**）：``conditional`` 为真时 ``condition`` MUST 非空
    ——值级守卫会与后续 30 个 feature 的实际用法反复冲突，由**生产者**
    （图定义层）保证。

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
