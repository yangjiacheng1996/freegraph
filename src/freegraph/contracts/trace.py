# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""契约层的**可观测数据面**——:class:`Span` 与 :class:`TraceQuery`。

* :class:`Span` —— 可观测事件载体（**11 字段**，含必带四项
  ``thread_id`` / ``run_id`` / ``node`` / ``checkpoint_id``）；
* :class:`TraceQuery` —— 本地 trace 查询请求（**C27 的请求结构**，5 字段全可空）。

两者均为**纯数据类**：字段值 100% 可 JSON 序列化（C27 的前提）。

> **依赖方向**：本模块**不 import** ``protocols``——``protocols`` 依赖本模块
> （``TraceSink`` 的方法签名引用 ``Span``），反向 import 会造成循环导入。

本模块**零** freegraph 内部 import、**零**第三方 import（仅标准库）。
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "Span",
    "TraceQuery",
]


@dataclass(frozen=True, slots=True, kw_only=True)
class Span:
    """**可观测事件载体** —— 一个 span 的完整定格（**11 字段**）。

    ================= ========================= ============= ==========================================
    字段              类型                       缺省          语义
    ================= ========================= ============= ==========================================
    ``id``            ``str``                    —（必填）      span 唯一标识（``parent`` 引用它）
    ``name``          ``str``                    —（必填）      span 名（节点 / 工具 / 模型三级）
    ``attributes``    ``Mapping[str, Any]``     空映射         属性（对齐 OTel GenAI 的 ``gen_ai.*``）
    ``parent``        ``str | None``             ``None``      **父 span 的 id**（不是对象引用）
    ``start_time``    ``str``                    —（必填）      起始时刻（UTC ISO-8601 字符串）
    ``end_time``      ``str | None``             ``None``      结束时刻；**未结束时为空**
    ``context``       ``Mapping[str, Any]``     空映射         附加上下文
    ``thread_id``     ``str | None``             ``None``      **会话标识**（C22；由 ``RunConfig`` 承载）
    ``run_id``        ``str``                    —（必填）      **单次运行标识**（C22 / C23）
    ``node``          ``str``                    —（必填）      **节点名**（C23 必带）
    ``checkpoint_id`` ``str | None``             ``None``      **检查点标识**（C23 必带）
    ================= ========================= ============= ==========================================

    **必带四项**（C23 · D11）：``thread_id`` / ``run_id`` / ``node`` /
    ``checkpoint_id`` 四项**均可读**；**缺 ``run_id`` 的 span 视为实现缺陷**
    （宪法原则 VII）。

    **JSON 可序列化**（C27 前提）：``parent`` 是**标识字符串**、时间是
    **ISO 字符串**、``attributes`` / ``context`` 是纯映射 ⇒ 整个 span 可被
    标准库序列化器直接序列化。

    **生命周期**：开始回调收「``end_time`` 为空」的实例，结束回调收
    **同 ``id``、``end_time`` 已填的新实例**，两次按 ``id`` 配对；
    **开始时的实例 MUST NOT 在事后被改写**（其 ``end_time`` 始终为空）。

    **不可变**（D-07 / D-14）：``frozen=True``；``attributes`` / ``context``
    在 ``__post_init__`` 中**浅拷贝**（``dict(...)``，**不用**
    ``MappingProxyType``——后者不可 JSON 序列化，会让 C27 的前提落不了地）。

    **构造期零值校验**：不校验 ``run_id`` 非空、不校验时间格式、不校验
    ``parent`` 指向存在的 span——格式与类型由**生产者**保证。

    **对应契约**：C23 / C24；数据格式 **DF4**。
    """

    id: str
    name: str
    attributes: Mapping[str, Any] = field(default_factory=dict)
    parent: str | None = None
    start_time: str
    end_time: str | None = None
    context: Mapping[str, Any] = field(default_factory=dict)
    thread_id: str | None = None
    run_id: str
    node: str
    checkpoint_id: str | None = None

    def __post_init__(self) -> None:
        """构造期把 ``attributes`` / ``context`` 拷为自身持有的**新映射**。

        ``frozen=True`` 下普通赋值会抛 ``FrozenInstanceError``，
        故 MUST 用 ``object.__setattr__``。拷贝为**浅拷贝**——嵌套容器
        仍与调用方共享同一对象（本层不做深拷贝）。

        本方法**不校验值**——``run_id`` 是否非空、时间格式是否合规均由
        **生产者**保证。
        """
        object.__setattr__(self, "attributes", dict(self.attributes))
        object.__setattr__(self, "context", dict(self.context))


@dataclass(frozen=True, slots=True, kw_only=True)
class TraceQuery:
    """**trace 查询请求** —— C27 的请求结构（**5 字段**，全部可空）。

    ============= ============== ======= ==========================================
    字段           类型            缺省   语义
    ============= ============== ======= ==========================================
    ``run_id``     ``str | None``  ``None`` 运行标识过滤
    ``thread_id``  ``str | None``  ``None`` 会话标识过滤
    ``node``       ``str | None``  ``None`` 节点名过滤
    ``start_time`` ``str | None``  ``None`` 时间范围起点（UTC ISO-8601）
    ``end_time``   ``str | None``  ``None`` 时间范围终点（UTC ISO-8601）
    ============= ============== ======= ==========================================

    五字段**全部可空、可任意组合**；**全空 = 取全部**（C27 的「空过滤器」）。

    **字段名与 span 侧同名**——一个概念一个名字。

    **构造期零值校验**：不校验时间范围先后（``start > end`` 归查询实现处理）。

    **可哈希**（**有意如此**）：五字段全为标量、无映射字段 ⇒ dataclass 默认可
    哈希。与 :class:`Span` 等四类的「不可哈希」口径**不同**——「不可哈希」的
    根因是**含映射字段**，不是一条无理由的禁令。**记录在案，非缺陷**。

    **对应契约**：C27（**数据面**已冻结；协议面挂起 B20F1）。
    """

    run_id: str | None = None
    thread_id: str | None = None
    node: str | None = None
    start_time: str | None = None
    end_time: str | None = None
